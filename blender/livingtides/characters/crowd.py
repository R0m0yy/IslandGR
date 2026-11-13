"""Crowd villagers: every resident of Saltcrown gets a real character.

A parametric builder on top of the hero pipeline (cast.py): a MakeHuman body
with a randomised face, hair and beard styles, and an outfit assembled from
modular garments (tops, bottoms, skirts, vests, aprons, hats, footwear). The
14 variants below, plus the four heroes, are exported as game GLBs; Godot
assigns them to residents by age group and look and varies clothing colour
and skin tone per resident through the vertex-colour alpha channel:
    alpha 1.0  clothing   (hue / value shifted per resident)
    alpha 0.5  skin       (tone shifted per resident)
    alpha 0.0  fixed      (hair, eyes, teeth, props, metal)
"""
from __future__ import annotations
import math
import numpy as np
import bpy, bmesh
from . import hero, mh
from . import garments as G
from .hero import BONES, BI, rgb
from .cast import (Char, fabric, front_back, smoothstep, armhole, footwear_sole, sandals, hat_shell,
                   TORSO, ARM_L, ARM_R, LEGS, FEET, HANDS, NOT_LOWER, NOT_VEST)

FACE_TARGETS = ["nose/nose-scale-horiz-incr", "nose/nose-scale-horiz-decr", "nose/nose-scale-vert-incr", "nose/nose-flaring-incr",
                "nose/nose-hump-incr", "nose/nose-point-width-incr", "chin/chin-width-incr", "chin/chin-prominent-incr",
                "chin/chin-prominent-decr", "cheek/l-cheek-bones-incr", "cheek/r-cheek-bones-incr", "mouth/mouth-scale-horiz-incr",
                "mouth/mouth-lowerlip-volume-incr", "mouth/mouth-upperlip-volume-incr", "head/head-round", "head/head-square",
                "head/head-oval", "eyes/l-eye-scale-incr", "eyes/r-eye-scale-incr", "eyebrows/eyebrows-trans-down",
                "ears/l-ear-scale-incr", "ears/r-ear-scale-incr", "neck/measure-neck-circ-incr"]

SKINS = ["#3E2418", "#4A2C1F", "#5C3826", "#6A4430", "#7A4E36", "#8A5A3C", "#A06C48", "#B98058"]

# --------------------------------------------------------------------------- variants
#  look: "m" / "f" body; age group: adult / elder / child
VARIANTS = {
    "V01": dict(look="m", age=38, skin=2, hair="crop", beard="stubble", top=("rolled", "#EFEBE1", "v"), bottom=("rolled", "#26355A"),
                feet="boots", hat=("flatcap", "#55595E"), weight=0.55, muscle=0.7, role="fisher"),
    "V02": dict(look="m", age=29, skin=1, hair="coils", beard="short", top=("short", "#D7A546", "crew"), bottom=("trousers", "#B59E73"),
                feet="sandals", weight=0.5, muscle=0.6, role="worker"),
    "V03": dict(look="m", age=24, skin=3, hair="crop", beard=None, top=("tank", "#F1EEE6", "crew"), bottom=("shorts", "#3FA79E"),
                feet="sandals", hat=("straw", "#D9BE7A"), weight=0.42, muscle=0.6, role="worker"),
    "V04": dict(look="m", age=46, skin=0, hair="coils", beard="short", top=("long", "#E9DFC6", "v"), vest="#7B4F86",
                bottom=("trousers", "#3B3A3F"), feet="boots", weight=0.62, muscle=0.5, role="trader"),
    "V05": dict(look="f", age=34, skin=2, hair="bun", top=("blouse", "#D8725F", "scoop"), bottom=("skirt_long", "#3FA79E"),
                apron="#EBDCB4", feet="sandals", weight=0.55, role="trader"),
    "V06": dict(look="f", age=27, skin=1, hair="wrap", wrap="#D7A546", top=("short", "#F1EEE6", "scoop"), bottom=("skirt", "#7B4F86"),
                feet="sandals", weight=0.48, role="worker"),
    "V07": dict(look="f", age=41, skin=4, hair="coils", top=("long", "#F3EFE4", "v"), bottom=("rolled", "#3F7DC0"),
                feet="sandals", hat=("straw", "#D9BE7A"), weight=0.6, role="worker"),
    "V08": dict(look="f", age=22, skin=3, hair="bun", top=("tank", "#B5463C", "scoop"), bottom=("skirt", "#B5463C"),
                apron="#F1EEE6", feet="bare", weight=0.45, role="cook"),
    "V09": dict(look="m", age=68, skin=4, hair="side_white", beard="short_white", top=("long", "#C9D6DA", "v"),
                bottom=("trousers", "#55595E"), feet="sandals", hat=("flatcap", "#8A6A4A"), weight=0.5, muscle=0.35, role="elder"),
    "V10": dict(look="m", age=72, skin=1, hair="side_white", beard="stubble_white", top=("short", "#3F7DC0", "crew"),
                bottom=("rolled", "#B59E73"), feet="bare", hat=("straw", "#C9A86A"), weight=0.42, muscle=0.3, role="elder"),
    "V11": dict(look="f", age=66, skin=5, hair="bun_white", top=("long", "#EBDCB4", "crew"), bottom=("skirt_long", "#553828"),
                feet="sandals", weight=0.62, role="elder"),
    "V12": dict(look="f", age=70, skin=0, hair="wrap", wrap="madras", top=("short", "#3F7DC0", "scoop"), bottom=("skirt_long", "#3F7DC0"),
                apron="#F1EEE6", feet="sandals", weight=0.6, role="elder"),
    "V13": dict(look="m", age=9, skin=2, hair="coils", top=("short", "#B5463C", "crew", "stripes"), bottom=("shorts", "#3F7DC0"),
                feet="bare", weight=0.45, role="child"),
    "V14": dict(look="f", age=7, skin=3, hair="puffs", top=("short", "#E9B92F", "scoop"), bottom=("skirt", "#E9B92F"),
                feet="sandals", weight=0.45, role="child"),
}


def make_spec(key, v):
    rng = np.random.default_rng(abs(hash(key)) % (2 ** 31))
    age = v["age"]
    child = age < 13
    detail = {}
    for t in rng.choice(FACE_TARGETS, size=6, replace=False):
        detail[str(t)] = float(rng.uniform(0.15, 0.6))
    if age > 60:
        detail.update({"head/head-age-incr": 0.8, "mouth/mouth-laugh-lines-in": 0.8, "eyes/l-eye-bag-incr": 0.6, "eyes/r-eye-bag-incr": 0.6})
    if child:
        detail.update({"eyes/l-eye-scale-incr": 0.6, "eyes/r-eye-scale-incr": 0.6})
    height_m = {True: 1.12 + (age - 6) * 0.06}.get(child, 1.74 if v["look"] == "m" else 1.64)
    if not child:
        height_m += rng.uniform(-0.06, 0.06) - (0.04 if age > 65 else 0.0)
    race = {"african": 1.0} if v["skin"] < 6 else {"african": 0.6, "caucasian": 0.4}
    return dict(name=f"{key}_crowd", title=key, gender=1.0 if v["look"] == "m" else 0.0, age_years=age, muscle=v.get("muscle", 0.5),
                weight=v.get("weight", 0.5), height=0.5, proportions=0.55, race=race, head_scale=1.28 if child else 1.38,
                height_m=float(height_m), skin=SKINS[v["skin"]], iris="#4A2E1C", detail=detail,
                hand_scale=1.08 if child else 1.12, lash=(0.05, 0.035, 0.03) if v["look"] == "f" else (0.13, 0.09, 0.07))


# --------------------------------------------------------------------------- tint channel
def set_alpha(ob, a):
    me = ob.data
    if "Col" not in me.color_attributes or len(me.loops) == 0:
        return
    ca = me.color_attributes["Col"]
    cols = np.zeros(len(me.loops) * 4)
    ca.data.foreach_get("color", cols)
    cols = cols.reshape(-1, 4)
    cols[:, 3] = a
    ca.data.foreach_set("color", cols.ravel())


def tag_tint_channel(c):
    """Clothing 1.0, skin 0.5, everything else 0.0 (see module docstring)."""
    for n, (ob, cat) in c.parts.items():
        if ob.type != "MESH":
            continue
        if n == "body":
            me = ob.data
            part = np.zeros(len(me.polygons), dtype=np.int64)
            if "part" in me.attributes:
                me.attributes["part"].data.foreach_get("value", part)
            ca = me.color_attributes["Col"]
            cols = np.zeros(len(me.loops) * 4); ca.data.foreach_get("color", cols); cols = cols.reshape(-1, 4)
            for p in me.polygons:
                cols[p.loop_start:p.loop_start + p.loop_total, 3] = 0.5 if part[p.index] == 0 else 0.0
            ca.data.foreach_set("color", cols.ravel())
        elif cat in ("clothing", "footwear") and not n.startswith(("boot", "belt", "buckle")) and "sole" not in n:
            set_alpha(ob, 1.0)
        elif cat == "hat" and not n.endswith("_band"):
            set_alpha(ob, 1.0)
        else:
            set_alpha(ob, 0.0)


# --------------------------------------------------------------------------- pieces
def hair(c, style):
    k = c.k
    dark = lambda P, N, b, g: G.mixc(np.tile([0.045, 0.032, 0.026], (len(P), 1)), np.array([0.16, 0.12, 0.09]), np.clip(b / (0.004 * k) + g * 0, 0, 1) ** 1.4)
    white = lambda P, N, b, g: G.mixc(np.tile([0.93, 0.92, 0.88], (len(P), 1)), np.array([0.68, 0.66, 0.62]), np.clip(g / (0.003 * k) + 0.2 * (b > 0), 0, 1))
    if style in ("coils", "puffs"):
        hf = c.hair_field(front=0.9, side=0.3, back=-0.55, temple_dip=0.05, ear_clear=0.035)
        coils = c.coil_bumps(hf, 0.0075, 0.0045, 0.6, seed=hash(c.key) % 100)
        t = lambda P: (0.01 + 0.012 * np.clip(((P - c.hc) / c.hr)[:, 2] + 0.2, 0, 1.2)) * k
        c.hair_volume("hair", hf, t, dark, subdiv=1, bumps=coils, taper=0.004, sharp=1.3)
        if style == "puffs":       # two round puffs on top
            bm = bmesh.new()
            for sx in (1, -1):
                ctr = c.hc + np.array([sx * 0.06 * k, 0.01, 0.1 * k])
                G.ellipsoid(bm, ctr, (0.045 * k, 0.045 * k, 0.042 * k), segs=14, rings=9)
            c.solid("hair_puffs", bm, lambda P, N, W: np.tile([0.05, 0.035, 0.03], (len(P), 1)) * (1 + 0.5 * np.abs(G.vnoise(P, 0.006, 3)))[:, None],
                    cat="hair", weights={"head": 1.0}, sharp=1.3)
    elif style == "crop":
        hf = c.hair_field(front=0.88, side=0.25, back=-0.85, temple_dip=0.05)
        coils = c.coil_bumps(hf, 0.004, 0.0018, 0.6, seed=3)
        c.hair_volume("hair", hf, lambda P: np.full(len(P), 0.0045 * k), dark, subdiv=0, bumps=coils)
    elif style in ("bun", "bun_white"):
        hf = c.hair_field(front=0.88, side=0.25, back=-0.7, temple_dip=0.04)
        col = white if style == "bun_white" else dark
        c.hair_volume("hair", hf, lambda P: np.full(len(P), 0.007 * k), col, subdiv=0,
                      grooves=lambda P, N: 0.0025 * k * np.abs(np.sin(np.arctan2(P[:, 0] - c.hc[0], P[:, 2] - c.hc[2]) * 30)), taper=0.006)
        bm = bmesh.new()
        ctr = c.hc + np.array([0, 0.11 * k, 0.07 * k])
        G.ellipsoid(bm, ctr, (0.05 * k, 0.045 * k, 0.045 * k), segs=16, rings=10)
        G.torus(bm, ctr + np.array([0, -0.02 * k, -0.01 * k]), (0, 1, 0.4), 0.04 * k, 0.008 * k, segs=24, sides=6)
        bc = (np.array([0.93, 0.92, 0.88]) if style == "bun_white" else np.array([0.05, 0.035, 0.03]))
        c.solid("hair_bun", bm, lambda P, N, W: np.tile(bc, (len(P), 1)) * (1 - 0.25 * np.abs(np.sin(np.arctan2(P[:, 1] - ctr[1], P[:, 0] - ctr[0]) * 12)))[:, None],
                cat="hair", weights={"head": 1.0}, sharp=1.3)
    elif style == "side_white":
        hf = c.hair_field(front=0.75, side=0.05, back=-0.85, temple_dip=0.05)
        c.hair_volume("hair", hf, lambda P: np.full(len(P), 0.007 * k), white, subdiv=0,
                      grooves=lambda P, N: 0.003 * k * np.abs(np.sin(P[:, 2] * 220 + P[:, 1] * 60)), taper=0.01)
    elif style == "wrap":
        pass                        # handled with the hats
    # brows for everyone
    colb = white if c.spec["age_years"] > 60 else (lambda P, N, b, g: np.tile([0.07, 0.05, 0.04], (len(P), 1)))
    c.hair_volume("brows", c.brow_field(0.18, 1.35), lambda P: np.full(len(P), 0.0016 * k), colb, subdiv=2, taper=0.005)


def beard(c, style):
    if not style or style.startswith("stubble"):
        return
    k = c.k; m = c.m
    white = style.endswith("white")
    col = (lambda P, N, b, g: G.mixc(np.tile([0.93, 0.92, 0.88], (len(P), 1)), np.array([0.7, 0.68, 0.64]), np.clip(g / (0.003 * k), 0, 1))) if white else \
          (lambda P, N, b, g: G.mixc(np.tile([0.05, 0.035, 0.03], (len(P), 1)), np.array([0.14, 0.1, 0.08]), np.clip(g / (0.002 * k), 0, 1)))
    # short beard = painted stubble (paint_skin) + a neat goatee on the chin; the lips stay clear
    gf = lambda P, W: np.minimum(np.minimum(0.024 * k - np.abs(P[:, 0] - m[0]), (m[2] - 0.016 * k) - P[:, 2]),
                                 np.minimum(P[:, 2] - (m[2] - 0.06 * k), np.where(P[:, 1] < m[1] + 0.015, 1.0, -1.0)))
    c.hair_volume("beard", gf, lambda P: np.full(len(P), 0.005 * k), col, subdiv=1,
                  grooves=lambda P, N: 0.0015 * k * np.abs(np.sin(P[:, 0] * 380)), taper=0.006)


def top(c, spec):
    style, colour, neck = spec[0], spec[1], spec[2]
    striped = len(spec) > 3 and spec[3] == "stripes"
    k = c.k; wz = c.waist_z; nz = c.neck_z
    sel_arms = TORSO + (ARM_L + ARM_R if style in ("long", "rolled") else (("upperarm_l", "upperarm_r") if style in ("short", "blouse") else ()))
    faces = lambda C, FW: (G.bone_sum(FW, sel_arms + ("thigh_l", "thigh_r")) > 0.5) & (C[:, 2] > c.hip_z - 0.08)
    if neck == "v":
        nf = lambda P, W: front_back(P, (nz - 0.006 - 0.07 * k * np.clip(1 - np.abs(P[:, 0]) / (0.05 * k), 0, 1)) - P[:, 2], (nz - 0.006) - P[:, 2])
    elif neck == "scoop":
        nf = lambda P, W: front_back(P, (c.clav_z + 0.03 - 0.07 * k * np.sqrt(np.clip(1 - (P[:, 0] / (0.1 * k)) ** 2, 0, 1))) - P[:, 2],
                                     (c.clav_z + 0.03) - P[:, 2], y0=-0.01, w=0.05)
    else:
        nf = lambda P, W: front_back(P, (nz - 0.012 - 0.02 * k * np.clip(1 - np.abs(P[:, 0]) / (0.06 * k), 0, 1)) - P[:, 2], (nz - 0.006) - P[:, 2])
    cuts = [nf]
    tucked = c.spec.get("_tucked", False)
    cuts.append((lambda P, W: P[:, 2] - (wz - 0.08)) if tucked else (lambda P, W: P[:, 2] - (c.hip_z - 0.01)))
    if style == "long":
        cuts += [G.limb_plane(c.B["lowerarm_l"], 0.92), G.limb_plane(c.B["lowerarm_r"], 0.92)]
    elif style == "rolled":
        cuts += [G.limb_plane(c.B["lowerarm_l"], 0.42), G.limb_plane(c.B["lowerarm_r"], 0.42)]
    elif style in ("short", "blouse"):
        cuts += [G.limb_plane(c.B["upperarm_l"], 0.48), G.limb_plane(c.B["upperarm_r"], 0.48)]
    else:   # tank
        cuts += [armhole(c, "l", 0.0), armhole(c, "r", 0.0),
                 lambda P, W: np.linalg.norm((P - (c.sh["l"] + np.array([0.0, 0, -0.06]))) * np.array([1, 1, 0.8]), axis=1) - 0.07 * k,
                 lambda P, W: np.linalg.norm((P - (c.sh["r"] + np.array([0.0, 0, -0.06]))) * np.array([1, 1, 0.8]), axis=1) - 0.07 * k]
    field = G.fmin(*cuts)

    def extra(P, N, W):
        e = 0.003 * G.vnoise(P, 0.04, 2)
        if not tucked:
            e = e + 0.014 * smoothstep(wz + 0.03, wz - 0.03, P[:, 2])
        if style == "blouse":
            for s in ("l", "r"):
                h, t = c.B[f"upperarm_{s}"]; d = (t - h) / np.linalg.norm(t - h)
                a = ((P - h) @ d) / np.linalg.norm(t - h)
                e = e + 0.014 * np.sin(np.pi * np.clip(a / 0.48, 0, 1)) * (G.bone_sum(W, (f"upperarm_{s}",)) > 0.5)
        return e
    kw = {}
    if striped:
        sw = 0.024 * k
        alt = np.asarray(rgb("#F1EEE6")); main = np.asarray(rgb(colour))
        kw = dict(pattern=lambda ob: G.plane_cuts(ob, (0, 0, 1), sw), pattern_cuts=[((0, 0, 1), sw)],
                  face_colour=lambda C, N, I: np.where((np.floor(C[:, 2] / sw) % 2 == 0)[:, None], main, alt))
    ob, _ = c.garment("top", faces, field, 0.007, 0.003, fabric(colour, 0.05, 0.07, 1, fade=0.12, shade=0.15), extra=extra, relax=4,
                      hems=[(0.0035, colour, None)], **kw)
    if style == "rolled":
        for s in ("l", "r"):
            h, t = c.B[f"lowerarm_{s}"]; co = h + (t - h) * 0.42
            bm = bmesh.new()
            for loop in c.loops("top"):
                if np.linalg.norm(loop.mean(axis=0) - co) < 0.06:
                    pts = G.smooth_path(G.resample(loop, 0.006), 1); d = (t - h) / np.linalg.norm(t - h); cc = pts.mean(axis=0)
                    for j, (dz, rr) in enumerate(((-0.004, 0.011), (-0.026, 0.012))):
                        G.ring_tube(bm, cc + (pts - cc) * (1.1 + 0.05 * j) + d * dz, rr * k, sides=7)
            c.solid(f"sleeve_roll_{s}", bm, fabric(colour, 0.05, 0.05, 2, shade=0.15), cat="clothing",
                    weights=G.bone_sum(c.W, (f"lowerarm_{s}", f"upperarm_{s}")) > 0.5)
    if neck == "v" and style in ("long", "rolled"):
        col = G.collar(c.pre["top"], lambda L: L[:, 2].mean() > nz - 0.05, 0.026 * k, 0.025 * k, 0.003, c.coll, f"{c.key}_collar", points=0.03 * k)
        G.copy_weights_from(col, c.P, c.W); G.paint_vertices(col, fabric(colour, 0.04, 0.05, 3), smooth=True); hero.assign(col)
        c.add("collar", col, "clothing")
    return ob


def bottom(c, spec):
    style, colour = spec
    k = c.k; wz = c.waist_z
    if style.startswith("skirt"):
        return skirt(c, colour, long=style == "skirt_long")
    faces = lambda C, FW: (G.bone_sum(FW, NOT_LOWER) < 0.5) & (C[:, 2] < wz + 0.06)
    if style == "shorts":
        legs = [G.limb_plane(c.B["thigh_l"], 0.56), G.limb_plane(c.B["thigh_r"], 0.56)]
        faces = lambda C, FW: (G.bone_sum(FW, NOT_LOWER + ("calf_l", "calf_r")) < 0.5) & (C[:, 2] < wz + 0.06)
    elif style == "rolled":
        legs = [G.limb_plane(c.B["calf_l"], 0.62), G.limb_plane(c.B["calf_r"], 0.62)]
    else:
        legs = [G.limb_plane(c.B["calf_l"], 0.93), G.limb_plane(c.B["calf_r"], 0.93)]
    field = G.fmin(lambda P, W: (wz + 0.01) - P[:, 2], *legs)
    folds = lambda P, N, W: 0.004 * G.vnoise(P, 0.04, 6) + 0.006 * np.exp(-((P[:, 2] - 0.12) / 0.06) ** 2) * np.abs(np.sin(P[:, 2] * 140))
    ob, _ = c.garment("bottom", faces, field, 0.011 if style != "shorts" else 0.013, 0.004,
                      fabric(colour, 0.06, 0.08, 4, fade=0.15, shade=0.2), extra=folds, rim_only=style != "shorts",
                      hems=[(0.006 if style != "rolled" else 0.011, colour, lambda L: L[:, 2].mean() < c.hip_z)])
    belt_f = lambda P, W: 0.016 * k - np.abs(P[:, 2] - (wz - 0.006 * k))
    c.patch("bottom", "belt", belt_f, 0.004, 0.003, fabric("#3A2416" if style != "shorts" else colour, 0.06, 0.03, 7), hems=[(0.0016, "#2A1A10")])
    return ob


def skirt(c, colour, long=False):
    k = c.k; wz = c.waist_z; P, W = c.P, c.W
    hem_z = (float(c.B["calf_l"][0][2]) * (0.25 if long else 0.85)) + (0.0 if long else -0.05 * k)
    rings, segs = 14, 64
    legs = G.bone_sum(W, ("pelvis", "spine_01", "thigh_l", "thigh_r", "calf_l", "calf_r")) > 0.6
    centre = P[(np.abs(P[:, 2] - wz) < 0.03) & (G.bone_sum(W, ("spine_01", "pelvis", "spine_02")) > 0.5)].mean(axis=0)
    lower = P[legs & (P[:, 2] < wz + 0.03) & (P[:, 2] > hem_z)]
    verts, faces = [], []
    prof = None
    flare = 0.15 if long else 0.19
    for j in range(rings + 1):
        u = j / rings
        z = wz - (wz - hem_z) * u
        sl = lower[np.abs(lower[:, 2] - z) < 0.035]
        q = sl - centre; q[:, 2] = 0
        row = []
        for s in range(segs):
            a = 2 * math.pi * s / segs; dv = np.array([math.cos(a), math.sin(a), 0])
            proj = q @ dv; mm = (q @ np.array([-dv[1], dv[0], 0])) ** 2 < 0.03 ** 2
            row.append(proj[mm].max() if mm.any() else (prof[s] if prof is not None else 0.15))
        row = np.array(row)
        for _ in range(3):
            row = (np.roll(row, 1) + 2 * row + np.roll(row, -1)) / 4
        prof = row if prof is None else np.maximum(row, prof * 0.98)
        for s in range(segs):
            a = 2 * math.pi * s / segs; dv = np.array([math.cos(a), math.sin(a), 0])
            rr = prof[s] + 0.012 + flare * u ** 1.5 + 0.016 * u ** 1.2 * math.sin(a * 11 + 0.6)
            verts.append(tuple(np.array([centre[0], centre[1], z]) + dv * rr * np.array([1, 0.92, 1])))
    for j in range(rings):
        for s in range(segs):
            s2 = (s + 1) % segs
            faces.append((j * segs + s, (j + 1) * segs + s, (j + 1) * segs + s2, j * segs + s2))
    bm = bmesh.new(); G.add_geom(bm, verts, faces)
    sk = G.bm_to_object(bm, "bottom", c.coll)
    hem_ring = np.array(verts[rings * segs:])
    G.thicken(sk, 0.005)
    Ps = hero.get_co(sk.data)
    Ws = np.zeros((len(Ps), len(BONES)))
    t = np.clip((wz - Ps[:, 2]) / (wz - hem_z), 0, 1)
    Ws[:, BI["pelvis"]] = 1 - 0.65 * t
    Ws[:, BI["thigh_l"]] = 0.65 * t * np.clip(0.5 + Ps[:, 0] * 8, 0, 1)
    Ws[:, BI["thigh_r"]] = 0.65 * t * np.clip(0.5 - Ps[:, 0] * 8, 0, 1)
    hero.set_groups(sk, Ws)
    G.paint_vertices(sk, fabric(colour, 0.05, 0.08, 4, shade=0.18), smooth=True, sharp_angle=1.1)
    hero.assign(sk); c.add("bottom", sk, "clothing")
    bm = bmesh.new()
    G.ring_tube(bm, G.smooth_path(hem_ring + np.array([0, 0, 0.003]), 1), 0.006, sides=6)
    top_ring = np.array(verts[:segs])
    G.ring_tube(bm, G.smooth_path(top_ring + np.array([0, 0, 0.012]), 1), 0.011, sides=6)
    hm = G.bm_to_object(bm, "skirt_hems", c.coll); G.copy_weights_from(hm, Ps, Ws)
    G.paint_vertices(hm, fabric(colour, 0.03, 0.04, 5), smooth=True); hero.assign(hm); c.add("skirt_hems", hm, "clothing")
    G.hide_body_under(c.body, lambda P_, W_: np.where(legs & (P_[:, 2] < wz - 0.02) & (P_[:, 2] > hem_z + 0.04), 1.0, -1.0), margin=0.0,
                      sel=lambda P_, W_: (P_[:, 2] < wz - 0.02) & (P_[:, 2] > hem_z + 0.05) & (G.bone_sum(W_, ("pelvis", "thigh_l", "thigh_r")) > 0.5))
    c._skirt = dict(verts=verts, rings=rings, segs=segs, Ps=Ps, Ws=Ws, hem_z=hem_z)
    return sk


def apron(c, colour):
    k = c.k; wz = c.waist_z
    sk = getattr(c, "_skirt", None)
    if sk is None:
        # apron over trousers: a patch on the front of the bottom garment
        af = lambda P, W: np.minimum(np.minimum(0.11 * k - np.abs(P[:, 0]), P[:, 2] - (c.hip_z - 0.2 * k)),
                                     np.minimum((wz - 0.005) - P[:, 2], np.where(P[:, 1] < -0.0, 1.0, -1.0)))
        c.patch("bottom", "apron", af, 0.008, 0.003, fabric(colour, 0.05, 0.06, 7, shade=0.12), hems=[(0.0022, colour)])
        return
    verts, rings, segs, Ps, Ws = sk["verts"], sk["rings"], sk["segs"], sk["Ps"], sk["Ws"]
    av, af = [], []
    cols_n, arow = 15, 10
    for j in range(arow + 1):
        u = j / arow
        jj = min(rings, int(round(u * rings * 0.7)))
        for q_ in range(cols_n):
            a = -math.pi / 2 + (q_ / (cols_n - 1) - 0.5) * 1.5
            s = int(round((a % (2 * math.pi)) / (2 * math.pi) * segs)) % segs
            p = np.array(verts[jj * segs + s]); dv = np.array([math.cos(a), math.sin(a), 0])
            av.append(tuple(p + dv * (0.014 + 0.005 * (1 - u) * math.sin(q_ * 2.4) + 0.003 * u)))
    for j in range(arow):
        for q_ in range(cols_n - 1):
            af.append((j * cols_n + q_, (j + 1) * cols_n + q_, (j + 1) * cols_n + q_ + 1, j * cols_n + q_ + 1))
    bm = bmesh.new(); G.add_geom(bm, av, af)
    ap = G.bm_to_object(bm, "apron", c.coll)
    bm2 = G.piping(ap, 0.0025)
    ae = G.bm_to_object(bm2, "apron_hem", c.coll); G.copy_weights_from(ae, Ps, Ws)
    G.paint_vertices(ae, fabric(colour, 0.03, 0.04, 6), smooth=True); hero.assign(ae); c.add("apron_hem", ae, "clothing")
    G.copy_weights_from(ap, Ps, Ws)
    G.thicken(ap, 0.004)
    G.paint_vertices(ap, fabric(colour, 0.05, 0.06, 7, shade=0.12), smooth=True); hero.assign(ap); c.add("apron", ap, "clothing")


def vest(c, colour):
    k = c.k; wz = c.waist_z; nz = c.neck_z
    faces = lambda C, FW: (G.bone_sum(FW, NOT_VEST) < 0.5) & (C[:, 2] > wz - 0.16)
    arm_l = lambda P, W: np.linalg.norm((P - (c.sh["l"] + np.array([0.02, 0, -0.045]))) * np.array([1, 1, 0.8]), axis=1) - 0.072 * k
    arm_r = lambda P, W: np.linalg.norm((P - (c.sh["r"] + np.array([-0.02, 0, -0.045]))) * np.array([1, 1, 0.8]), axis=1) - 0.072 * k
    opening = lambda P, W: np.abs(P[:, 0]) - (0.02 * k + 0.25 * np.clip(P[:, 2] - (wz + 0.08), 0, None)) + 6.0 * np.clip(P[:, 1] + 0.03, 0, None)
    field = G.fmin(arm_l, arm_r, armhole(c, "l", 0.02), armhole(c, "r", 0.02), opening, lambda P, W: P[:, 2] - (wz - 0.085),
                   lambda P, W: (nz - 0.025) - P[:, 2])
    c.garment("vest", faces, field, 0.022, 0.006, fabric(colour, 0.07, 0.07, 8, fade=0.15, shade=0.15), relax=4,
              hems=[(0.004, colour, None)], hide=False)
    bm = bmesh.new()
    vb = G.bvh_of(c.parts["vest"][0])
    for j in range(4):
        z = wz + 0.02 + j * 0.055 * k
        hit, nn = G.surface_hit(vb, (0.03 * k, -0.6, z), (0, 1, 0))
        if hit is not None:
            G.cylinder(bm, hit + nn * 0.001, hit + nn * 0.005, 0.006, segs=10)
    c.solid("vest_buttons", bm, "#C9A14A", mat=hero.char_material_metal())


def headwear(c, spec, wrap=None):
    k = c.k
    if wrap:
        wf = c.hair_field(front=0.62, side=0.15, back=-0.6, temple_dip=0.0, ear_clear=0.02)
        hc = c.hc
        t = lambda P: (0.02 + 0.04 * np.clip(((P - hc) / c.hr)[:, 2] + 0.1, 0, 1.2) ** 1.4 + 0.025 * np.clip(((P - hc) / c.hr)[:, 1], 0, 1)) * k
        folds = lambda P, N: 0.005 * k * np.abs(np.sin((P[:, 2] * 0.8 + P[:, 1] * 0.55 + np.abs(P[:, 0]) * 0.3) * 95))
        if wrap == "madras":
            A1 = np.array([1.0, 0.0, 0.3]); A1 /= np.linalg.norm(A1); A2 = np.array([-0.3, 0.2, 1.0]); A2 /= np.linalg.norm(A2); cell = 1 / 60

            def madras(C, N, I):
                a = np.floor((C @ A1) / cell + 1000).astype(int) % 6; b = np.floor((C @ A2) / cell + 1000).astype(int) % 6
                base = np.where(((a + b) % 2 == 0)[:, None], np.array([0.72, 0.12, 0.1]), np.array([0.84, 0.22, 0.14]))
                base = np.where(((a == 0) | (b == 0))[:, None], np.array([0.86, 0.64, 0.2]), base)
                return np.where(((a == 3) | (b == 3))[:, None], np.array([0.15, 0.36, 0.2]), base)
            c.hair_volume("headwrap", wf, t, None, subdiv=1, grooves=folds, cat="hat", taper=0.006, sharp=0.7,
                          cuts=[(A1, cell), (A2, cell)], face_colour=madras, rim=(0.011 * k, madras))
        else:
            wc = np.asarray(rgb(wrap))
            c.hair_volume("headwrap", wf, t, lambda P, N, b, g: np.tile(wc, (len(P), 1)) * (1 - 4 * np.clip(g, 0, 0.05))[:, None], subdiv=1,
                          grooves=folds, cat="hat", taper=0.006, sharp=0.7)
        return
    if not spec:
        return
    style, colour = spec
    col = np.asarray(rgb(colour))
    shade = lambda P, N, W: np.tile(col, (len(P), 1)) * (1 + 0.06 * G.vnoise(P, 0.02, 9))[:, None]
    if style == "flatcap":
        hat_shell(c, "hat", shade, base_lift=0.06, tilt=0.15, crown_h=0.085, bulge=1.12, brim=(0.075, 0.0, 0.0), droop=0.25,
                  forward=0.035, flat=0.85, thick=0.007, rings=7)
    elif style == "straw":
        straw = lambda P, N, W: np.tile(col, (len(P), 1)) * (1 + 0.12 * np.sin(np.arctan2(P[:, 1] - c.hc[1], P[:, 0]) * 90) * 0.5
                                                               + 0.08 * G.vnoise(P, 0.01, 4))[:, None]
        _, hi = hat_shell(c, "hat", straw, base_lift=0.055, tilt=0.1, crown_h=0.1, bulge=1.0, brim=(0.085, 0.085, 0.085), droop=0.12,
                          flat=0.7, thick=0.005, rings=6)
        bm = bmesh.new()
        pts = np.array([hi["ctr"] + dv * hi["rs"][s] * 1.01 + hi["axis"] * 0.012 for s, dv in enumerate(hi["dirs"])])
        G.ring_tube(bm, pts, 0.008, sides=6)
        c.solid("hat_band", bm, "#5A3A24", cat="hat", weights={"head": 1.0})
    elif style == "souwester":
        hat_shell(c, "hat", shade, base_lift=0.05, tilt=0.3, crown_h=0.13, bulge=1.05, brim=(0.05, 0.065, 0.1), droop=0.55, thick=0.006)


def footwear(c, kind):
    if kind == "sandals":
        sandals(c, "#7A4A2A")
    elif kind == "boots":
        boot_faces = lambda C, FW: G.bone_sum(FW, FEET + ("calf_l", "calf_r")) > 0.5
        boot_f = G.fmin(G.limb_plane(c.B["calf_l"], 0.45, keep="tail"), G.limb_plane(c.B["calf_r"], 0.45, keep="tail"))
        boots = c.part_from_body("boots", boot_faces, boot_f, "footwear")
        bm = bmesh.new(); bm.from_mesh(boots.data)
        for _ in range(40):
            bmesh.ops.smooth_vert(bm, verts=[v for v in bm.verts if not v.is_boundary], factor=0.8, use_axis_x=True, use_axis_y=True, use_axis_z=True)
        bm.to_mesh(boots.data); bm.free()
        G.displace(boots, lambda P, N, W: 0.016 + 0.004 * (P[:, 2] > 0.06))
        V = hero.get_co(boots.data); V[:, 2] = np.maximum(V[:, 2], 0.012); hero.set_co(boots.data, V)
        G.thicken(boots, 0.004)
        G.paint_vertices(boots, lambda P, N, W: np.tile([0.06, 0.06, 0.065], (len(P), 1)) * (1 + 0.15 * G.vnoise(P, 0.03, 12))[:, None], smooth=True)
        hero.assign(boots, hero.char_material_gloss()); c.add("boots", boots, "footwear")
        G.hide_body_under(c.body, G.fmin(boot_f, lambda P, W: np.where(boot_faces(P, W), 1.0, -1.0)), margin=0.004)
        footwear_sole(c, "boot_soles", "#2A2420", thick=0.02, grow=0.012, heel=0.012)


def build_variant(key):
    v = VARIANTS[key]
    spec = make_spec(key, v)
    spec["_tucked"] = (v["top"][0] in ("long", "rolled") and v["bottom"][0] in ("trousers", "rolled")) or v["bottom"][0].startswith("skirt")
    c = Char(key, spec)
    c.variant = v
    c.build_body()
    stub = 0.5 if v.get("beard") and (v["beard"].startswith("stubble") or v["beard"].startswith("short")) and not v["beard"].endswith("white") else 0.0
    c.paint_skin(lips="#3B1E18" if v["look"] == "m" else "#5A2A26", stubble=stub, blush=0.1, age=1.0 if v["age"] > 60 else 0.2)
    c.eyes()
    hair(c, v["hair"])
    beard(c, v.get("beard"))
    top(c, v["top"])
    bottom(c, v["bottom"])
    if v.get("vest"):
        vest(c, v["vest"])
    if v.get("apron"):
        apron(c, v["apron"])
    headwear(c, v.get("hat"), wrap=v.get("wrap") if v["hair"] == "wrap" else None)
    footwear(c, v.get("feet", "bare"))
    c.finish()
    tag_tint_channel(c)
    c.relaxed()
    return c
