"""Read MakeHuman CC0 data (base mesh, targets, game_engine rig, weights) and
build a morphed body. Pure numpy - our own implementation of the macro-target
blend described in targets/macrodetails/macro.json. No MPFB code is used.

Units: the base mesh is in decimetres, Y up. `to_blender` converts to metres, Z up.
"""
from __future__ import annotations
import gzip, json, os
from functools import lru_cache
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DATA = os.path.join(ROOT, "third_party", "makehuman_cc0")
TG = os.path.join(DATA, "targets")


@lru_cache(maxsize=1)
def base():
    """Returns (V (N,3) dm Y-up, faces list[tuple], face_group list[str], vgroups dict name -> int array)."""
    V, F, FG = [], [], []
    grp = None
    with open(os.path.join(DATA, "base.obj")) as f:
        for l in f:
            if l.startswith("v "):
                V.append([float(x) for x in l.split()[1:4]])
            elif l.startswith("g "):
                grp = l.split()[1]
            elif l.startswith("f "):
                F.append(tuple(int(p.split("/")[0]) - 1 for p in l.split()[1:]))
                FG.append(grp)
    vg_raw = json.load(open(os.path.join(DATA, "mesh_metadata", "basemesh_vertex_groups.json")))
    vg = {}
    for k, ranges in vg_raw.items():
        idx = []
        for a, b in ranges:
            idx.extend(range(a, b + 1))
        vg[k] = np.array(idx, dtype=np.int64)
    return np.array(V, dtype=np.float64), F, FG, vg


@lru_cache(maxsize=4096)
def target(rel: str):
    """(indices, deltas) of a .target.gz file, path relative to targets/."""
    p = os.path.join(TG, rel if rel.endswith(".target.gz") else rel + ".target.gz")
    if not os.path.exists(p):
        return None
    idx, d = [], []
    with gzip.open(p, "rt") as f:
        for l in f:
            s = l.split()
            if len(s) == 4 and not l.startswith("#"):
                idx.append(int(s[0])); d.append([float(s[1]), float(s[2]), float(s[3])])
    return np.array(idx, dtype=np.int64), np.array(d, dtype=np.float64).reshape(-1, 3)


def _interp(value, stops):
    """stops: [(value, name)] ascending -> {name: weight} piecewise linear."""
    if value <= stops[0][0]:
        return {stops[0][1]: 1.0}
    for (a, na), (b, nb) in zip(stops, stops[1:]):
        if value <= b:
            t = (value - a) / (b - a)
            out = {}
            if 1 - t > 1e-6: out[na] = 1 - t
            if t > 1e-6: out[nb] = out.get(nb, 0) + t
            return out
    return {stops[-1][1]: 1.0}


def age_value(years: float) -> float:
    """MakeHuman age slider from years: 1y=0, 11y=0.1875, 25y=0.5, 90y=1."""
    if years <= 11:
        return max(0.0, (years - 1) / 10 * 0.1875)
    if years <= 25:
        return 0.1875 + (years - 11) / 14 * 0.3125
    return min(1.0, 0.5 + (years - 25) / 65 * 0.5)


def macro_targets(p: dict) -> dict:
    """p: gender 0..1 (1 male), age_years, muscle 0..1, weight 0..1, height 0..1,
    proportions 0..1, race {african, asian, caucasian} -> {target relpath: weight}"""
    G = {"female": 1 - p["gender"], "male": p["gender"]}
    A = _interp(age_value(p["age_years"]), [(0, "baby"), (0.1875, "child"), (0.5, "young"), (1.0, "old")])
    M = _interp(p.get("muscle", 0.5), [(0, "minmuscle"), (0.5, "averagemuscle"), (1, "maxmuscle")])
    W = _interp(p.get("weight", 0.5), [(0, "minweight"), (0.5, "averageweight"), (1, "maxweight")])
    out = {}
    def add(k, w):
        if w > 1e-6:
            out[k] = out.get(k, 0) + w
    race = p.get("race", {"caucasian": 1.0})
    for r, rw in race.items():
        for g, gw in G.items():
            for a, aw in A.items():
                add(f"macrodetails/{r}-{g}-{a}", rw * gw * aw)
    h = p.get("height", 0.5)
    pr = p.get("proportions", 0.5)
    for g, gw in G.items():
        for a, aw in A.items():
            for m, mw in M.items():
                for w_, ww in W.items():
                    base_w = gw * aw * mw * ww
                    add(f"macrodetails/universal-{g}-{a}-{m}-{w_}", base_w)
                    if h > 0.5:
                        add(f"macrodetails/height/{g}-{a}-{m}-{w_}-maxheight", base_w * (h - 0.5) * 2)
                    elif h < 0.5:
                        add(f"macrodetails/height/{g}-{a}-{m}-{w_}-minheight", base_w * (0.5 - h) * 2)
                    if pr > 0.5:
                        add(f"macrodetails/proportions/{g}-{a}-{m}-{w_}-idealproportions", base_w * (pr - 0.5) * 2)
                    elif pr < 0.5:
                        add(f"macrodetails/proportions/{g}-{a}-{m}-{w_}-uncommonproportions", base_w * (0.5 - pr) * 2)
    return out


def apply_targets(V, weights: dict, missing: list | None = None):
    V = V.copy()
    for rel, w in weights.items():
        t = target(rel)
        if t is None:
            if missing is not None:
                missing.append(rel)
            continue
        idx, d = t
        V[idx] += d * w
    return V


def expression_delta(name: str, race: dict, nverts: int):
    """Race-blended expression unit as a dense (N,3) delta (dm)."""
    D = np.zeros((nverts, 3))
    tot = sum(w for r, w in race.items() if r in ("african", "caucasian")) or 1.0
    for r in ("african", "caucasian"):
        w = race.get(r, 0.0) / tot if r in race else 0.0
        if r == "caucasian" and "asian" in race:
            w += race["asian"] / tot
        if w <= 0:
            continue
        t = target(f"expression/units/{r}/{name}")
        if t is None:
            continue
        idx, d = t
        D[idx] += d * w
    return D


def to_blender(V):
    """dm Y-up -> m Z-up (x, -z, y) * 0.1"""
    V = np.asarray(V)
    return np.stack([V[..., 0], -V[..., 2], V[..., 1]], axis=-1) * 0.1


@lru_cache(maxsize=1)
def rig():
    return json.load(open(os.path.join(DATA, "rigs", "rig.game_engine.json")))


@lru_cache(maxsize=1)
def weights():
    w = json.load(open(os.path.join(DATA, "rigs", "weights.game_engine.json")))
    return w["weights"]


def joint_positions(V):
    """Centre of every joint-* cube in V (same space as V)."""
    _, _, _, vg = base()
    return {k: V[idx].mean(axis=0) for k, idx in vg.items() if k.startswith("joint-")}


def bone_positions(Vb):
    """Head/tail positions (Blender space) for every game_engine bone from joint cubes in Vb."""
    J = joint_positions(Vb)
    out = {}
    for name, b in rig().items():
        def pos(spec):
            if spec.get("strategy") == "CUBE" and spec.get("cube_name") in J:
                return J[spec["cube_name"]]
            if "vertex_index" in spec:
                return Vb[spec["vertex_index"]]
            if spec.get("strategy") == "MEAN" and "vertex_indices" in spec:
                return Vb[spec["vertex_indices"]].mean(axis=0)
            return np.array(spec["default_position"])
        out[name] = (pos(b["head"]), pos(b["tail"]), b.get("roll", 0.0), b.get("parent"))
    return out
