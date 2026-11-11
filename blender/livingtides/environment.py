"""Environment generators: terrain with irregular cliffs, The Gate, stairs,
ladder, rope bridge, decks, paths, boats, lamps, vegetation, landmarks.

Everything is derived from data/village_layout.json.  The walkable data is
never changed: inside a keep-out zone (walk links, building plots, decks) the
ground is exactly the layout height.  Irregularity lives in the cliff faces,
terrace lips and rock masses around that walkable skeleton.

Authoring is in layout axes (x east, y up, z south); P() converts to Blender.
"""
from __future__ import annotations
import math
import numpy as np
from .geom import Mesh, T, Rz, Rx, Ry, frame, rng_for
from . import parts, furniture as F
from .world import ground_h, seg_dist

SEABED = -2.6


def P(x, y, z):
    return (x, -z, y)


def n2(x, z, s=0.0):
    return (np.sin(x * 0.31 + s) * np.cos(z * 0.27 - s * 0.7) * 0.5
            + np.sin(x * 0.83 + z * 0.61 + s * 2.1) * 0.3
            + np.sin(x * 1.7 - z * 1.9 + s * 1.3) * 0.2)


# ================================================================ terrain
class Terrain:
    def __init__(self, L, cell=0.5, x=(-53.0, 51.0), z=(-41.0, 37.0)):
        self.L = L; self.cell = cell
        self.xs = np.arange(x[0], x[1] + 1e-6, cell)
        self.zs = np.arange(z[0], z[1] + 1e-6, cell)
        self.X, self.Z = np.meshgrid(self.xs, self.zs)
        self._build()

    # ---- polygon helpers (vectorised)
    @staticmethod
    def _inside(X, Z, poly):
        ins = np.zeros(X.shape, bool)
        n = len(poly)
        for i in range(n):
            x1, z1 = poly[i]; x2, z2 = poly[(i + 1) % n]
            if z1 == z2:
                continue
            c = ((z1 > Z) != (z2 > Z)) & (X < (x2 - x1) * (Z - z1) / (z2 - z1) + x1)
            ins ^= c
        return ins

    @staticmethod
    def _dist(X, Z, poly):
        d = np.full(X.shape, 1e9)
        n = len(poly)
        for i in range(n):
            ax, az = poly[i]; bx, bz = poly[(i + 1) % n]
            vx, vz = bx - ax, bz - az
            t = np.clip(((X - ax) * vx + (Z - az) * vz) / (vx * vx + vz * vz), 0, 1)
            d = np.minimum(d, np.hypot(X - (ax + t * vx), Z - (az + t * vz)))
        return d

    def _build(self):
        L, X, Z = self.L, self.X, self.Z
        data = np.full(X.shape, np.nan)
        H = np.full(X.shape, SEABED) + 0.35 * n2(X, Z, 5.0)
        for li, l in enumerate(L["land"]):
            ins = self._inside(X, Z, l["poly"])
            d = np.where(ins, 0.0, self._dist(X, Z, l["poly"]))
            h = l["h"]
            data = np.where(ins, np.where(np.isnan(data), h, np.maximum(data, h)), data)
            low = l["id"] in ("SP", "T1")
            # irregular lip: the cliff top wanders out past the surveyed edge
            bulge = (0.35 if low else 1.9) * (0.5 + 0.5 * n2(X * 1.3, Z * 1.3, 3.0 + li)) \
                + (0.0 if low else 1.3) * np.maximum(0.0, n2(X * 0.45, Z * 0.45, 9.0 + li * 2))
            de = np.maximum(0.0, d - bulge)
            if l["id"] == "SP":
                cand = h - 0.55 * de - 0.05 * de * de                 # shingle beach
            else:
                steep = 5.5 + 2.0 * n2(X * 0.6, Z * 0.6, 1.0 + li)
                cand = h - steep * de - 0.35 * de * de
                # ledges: strata steps in the face
                q = np.floor(cand / 1.15) * 1.15 + 0.25
                cand = np.where(de > 0, 0.45 * cand + 0.55 * np.minimum(q, h), cand)
                # talus apron at the foot
                cand = np.maximum(cand, h - 0.9 * h * np.clip(de / 3.2, 0, 1) ** 0.6 - 2.4 * de + 0.0 * de)
            H = np.maximum(H, cand)
        self.data = data
        # ---- keep-out: walk links, building plots, decks keep the surveyed height
        keep = np.zeros(X.shape, bool)
        nodes = L["nav"]["nodes"]
        self.span_edges = []
        for e in L["nav"]["edges"]:
            a, b = nodes[e["a"]], nodes[e["b"]]
            if e["type"] in ("stair", "ladder", "bridge", "archwalk", "board"):
                self.span_edges.append((e, a, b)); continue
            if a["kind"] == "water" or b["kind"] == "water":
                continue
            vx, vz = b["x"] - a["x"], b["z"] - a["z"]
            L2 = max(vx * vx + vz * vz, 1e-9)
            t = np.clip(((X - a["x"]) * vx + (Z - a["z"]) * vz) / L2, 0, 1)
            keep |= np.hypot(X - (a["x"] + t * vx), Z - (a["z"] + t * vz)) < 1.25
        for b in L["buildings"]:
            x0, x1, z0, z1 = b["footprint"]
            keep |= (X > x0 - 0.9) & (X < x1 + 0.9) & (Z > z0 - 0.9) & (Z < z1 + 1.3)
        for dk in L["decks"]:
            x0, x1, z0, z1 = dk["rect"]
            keep |= (X > x0 - 0.3) & (X < x1 + 0.3) & (Z > z0 - 0.3) & (Z < z1 + 0.3)
        self.keep = keep
        H = np.where(keep & ~np.isnan(data), data, H)
        H = np.where(~np.isnan(data), np.maximum(H, data), H)
        # decks stand over water / low ground: never let rock poke through them
        for dk in L["decks"]:
            x0, x1, z0, z1 = dk["rect"]
            m = (X > x0 - 0.4) & (X < x1 + 0.4) & (Z > z0 - 0.4) & (Z < z1 + 0.4) & np.isnan(data)
            H = np.where(m, np.minimum(H, dk["y"] - 1.2), H)
        # ---- ramps cut down through the quay edge to the decks and the spit
        for e in L["nav"]["edges"]:
            if e["type"] != "ramp":
                continue
            a, b = nodes[e["a"]], nodes[e["b"]]
            vx, vz = b["x"] - a["x"], b["z"] - a["z"]
            t = np.clip(((X - a["x"]) * vx + (Z - a["z"]) * vz) / max(vx * vx + vz * vz, 1e-9), 0, 1)
            dist = np.hypot(X - (a["x"] + t * vx), Z - (a["z"] + t * vz))
            line = a["y"] + (b["y"] - a["y"]) * t - 0.1 * np.sin(np.pi * t)
            H = np.where(dist < 0.9, np.minimum(H, line), H)
        # ---- stairs and the ladder: clear a corridor so nothing buries them
        for e, a, b in self.span_edges:
            if e["type"] not in ("stair", "ladder"):
                continue
            w = L["nav"]["stairs"].get(e["a"], {}).get("width", 1.2) / 2 + 0.35
            vx, vz = b["x"] - a["x"], b["z"] - a["z"]
            L2 = max(vx * vx + vz * vz, 1e-9)
            t = np.clip(((X - a["x"]) * vx + (Z - a["z"]) * vz) / L2, 0, 1)
            dist = np.hypot(X - (a["x"] + t * vx), Z - (a["z"] + t * vz))
            line = a["y"] + (b["y"] - a["y"]) * t - 0.22
            H = np.where(dist < w, np.minimum(H, np.maximum(line, np.where(np.isnan(data), SEABED, data))), H)
            self.keep = self.keep | (dist < w + 0.9)
        for e, a, b in self.span_edges:
            if e["type"] == "bridge":
                vx, vz = b["x"] - a["x"], b["z"] - a["z"]
                t = np.clip(((X - a["x"]) * vx + (Z - a["z"]) * vz) / (vx * vx + vz * vz), 0, 1)
                self.keep = self.keep | (np.hypot(X - (a["x"] + t * vx), Z - (a["z"] + t * vz)) < 1.6)
        # the Gate opening: keep the channel under the arch clear
        ar = L["arch"]
        m = (X > ar["x0"] - 1.5) & (X < ar["x1"] + 1.5) & (Z > ar["z0"] + 2.6) & (Z < ar["z1"] - 2.2)
        H = np.where(m, np.minimum(H, SEABED + 0.4), H)
        self.H = H

    def h(self, x, z):
        fx = (x - self.xs[0]) / self.cell; fz = (z - self.zs[0]) / self.cell
        i = int(np.clip(math.floor(fx), 0, len(self.xs) - 2)); j = int(np.clip(math.floor(fz), 0, len(self.zs) - 2))
        tx, tz = min(max(fx - i, 0), 1), min(max(fz - j, 0), 1)
        H = self.H
        return float((H[j, i] * (1 - tx) + H[j, i + 1] * tx) * (1 - tz) + (H[j + 1, i] * (1 - tx) + H[j + 1, i + 1] * tx) * tz)

    def is_keep(self, x, z):
        i = int(np.clip(round((x - self.xs[0]) / self.cell), 0, len(self.xs) - 1))
        j = int(np.clip(round((z - self.zs[0]) / self.cell), 0, len(self.zs) - 1))
        return bool(self.keep[j, i])

    def mesh(self):
        m = Mesh("LT_TERRAIN")
        X, Z, H = self.X, self.Z, self.H
        rng = rng_for("terrain")
        nz, nx = H.shape
        # jitter rock vertices sideways a little so the grid does not show
        jx = 0.16 * n2(X * 2.3, Z * 2.1, 7.0); jz = 0.16 * n2(X * 2.1, Z * 2.6, 8.0)
        flat = self.keep | (~np.isnan(self.data) & (np.abs(H - np.nan_to_num(self.data, nan=-99)) < 1e-6))
        Xj = np.where(flat, X, X + jx); Zj = np.where(flat, Z, Z + jz)
        V = np.stack([Xj, -Zj, H], axis=-1).reshape(-1, 3)
        m.v = list(map(tuple, V))
        idx = lambda j, i: j * nx + i
        for j in range(nz - 1):
            for i in range(nx - 1):
                a, b, c, d = idx(j, i), idx(j, i + 1), idx(j + 1, i + 1), idx(j + 1, i)
                tris = ((a, d, c), (a, c, b)) if (i + j) % 2 else ((a, d, b), (b, d, c))
                for tri in tris:
                    hs = [H.flat[k] for k in tri]
                    hmin, hmax = min(hs), max(hs)
                    if hmax < -1.2:
                        if rng.random() < 0.0:
                            continue
                        role = "seabed"
                    else:
                        slope = (hmax - hmin) / self.cell
                        hm = (hmin + hmax) / 2
                        cx = sum(Xj.flat[k] for k in tri) / 3; cz = sum(Zj.flat[k] for k in tri) / 3
                        if slope < 0.35:
                            if hm < 0.25: role = "rock_wet"
                            elif hm < 1.2: role = "sand"
                            else:
                                g = float(n2(cx * 0.9, cz * 0.9, 11.0)) + (0.25 if hm > 9 else -0.15)
                                role = "grass" if (g > 0.28 and not self.is_keep(cx, cz)) else "ground"
                        else:
                            band = math.floor((hm + 0.5 * float(n2(cx * 0.5, cz * 0.5, 4.0))) / 1.15)
                            role = ("rock_m", "rock_l", "rock_m", "rock_d")[int(band) % 4]
                            if hm < 0.3: role = "rock_wet"
                    m.f.append(tri); m.fm.append(role); m.ft.append(1.0 + rng.uniform(-0.07, 0.07))
        return m


# ================================================================ cliffs
def cliffs(L, ter):
    """Rock masses that break the terrace steps: buttresses against the faces,
    boulders at the foot, sea rocks.  Never placed inside a keep-out zone."""
    m = Mesh("LT_CLIFFS")
    rng = rng_for("cliffs")
    nodes = L["nav"]["nodes"]

    def blocked(x, z, r):
        for dx, dz in ((0, 0), (r, 0), (-r, 0), (0, r), (0, -r), (r * .7, r * .7), (-r * .7, r * .7), (r * .7, -r * .7), (-r * .7, -r * .7)):
            if ter.is_keep(x + dx, z + dz):
                return True
        ar = L["arch"]
        if ar["x0"] - 2 < x < ar["x1"] + 2 and ar["z0"] + 1.5 < z < ar["z1"] - 1.5:
            return True
        return False

    for l in L["land"]:
        if l["id"] in ("SP",):
            continue
        poly = l["poly"]; h = l["h"]
        for i in range(len(poly)):
            ax, az = poly[i]; bx, bz = poly[(i + 1) % len(poly)]
            Ls = math.hypot(bx - ax, bz - az)
            nx, nz = (bz - az) / Ls, -(bx - ax) / Ls
            # make sure the normal points out of the polygon
            mx, mz = (ax + bx) / 2 + nx * 0.4, (az + bz) / 2 + nz * 0.4
            from .world import pt_in_poly
            if pt_in_poly(mx, mz, poly):
                nx, nz = -nx, -nz
            s = rng.uniform(0.5, 2.0)
            while s < Ls:
                r = rng.uniform(1.3, 2.9)
                off = rng.uniform(0.2, 1.3)
                x, z = ax + (bx - ax) * s / Ls + nx * off, az + (bz - az) * s / Ls + nz * off
                lower = ground_h(L, x + nx * 2.5, z + nz * 2.5)
                lower = SEABED if lower is None else lower
                drop = h - lower
                if drop >= 2.5 and not blocked(x, z, r * 0.75):
                    hz = drop * rng.uniform(0.42, 0.6)
                    cy = lower + hz * rng.uniform(0.75, 1.0)
                    with m.push(T(*P(x, cy, z)), Rz(rng.uniform(0, 6.28))):
                        m.blob(r, r * rng.uniform(0.6, 0.95), hz, rng.choice(["rock_m", "rock_m", "rock_l", "rock_d"]), rng,
                               sub=2, rough=0.22, strata=rng.uniform(0.8, 1.3))
                    # cap stone / overhang near the lip
                    if rng.random() < 0.35 and drop > 4:
                        with m.push(T(*P(x + nx * 0.6, h - 0.5, z + nz * 0.6)), Rz(rng.uniform(0, 6.28))):
                            m.blob(r * 0.9, r * 0.6, 0.55, "rock_l", rng, sub=1, rough=0.25, strata=0.5)
                s += r * rng.uniform(0.9, 1.9)
    # boulders at the waterline and sea rocks
    placed = 0; tries = 0
    while placed < 46 and tries < 3000:
        tries += 1
        x, z = rng.uniform(-50, 48), rng.uniform(-38, 35)
        g = ter.h(x, z)
        if -2.2 < g < 0.6 and not blocked(x, z, 1.6) and ground_h(L, x, z) is None:
            r = rng.uniform(0.5, 1.7)
            with m.push(T(*P(x, g + r * 0.25, z)), Rz(rng.uniform(0, 6.28))):
                m.blob(r, r * rng.uniform(0.6, 1.0), r * rng.uniform(0.5, 0.9), rng.choice(["rock_m", "rock_d", "rock_wet"]), rng,
                       sub=1, rough=0.28, strata=0.6 if r > 1 else 0.0)
            placed += 1
    for (x, z, r, hh) in [(44.5, 24.0, 2.3, 5.5), (-47.0, 20.0, 2.6, 7.0), (24.0, 31.0, 1.6, 2.6), (46.0, -24.0, 3.0, 8.0), (-12.0, 33.5, 1.4, 2.0)]:
        with m.push(T(*P(x, hh * 0.3, z)), Rz(rng.uniform(0, 6.28))):
            m.blob(r, r * 0.8, hh, "rock_m", rng, sub=2, rough=0.24, strata=1.1)
        with m.push(T(*P(x + r * 0.9, 0.2, z + r * 0.5))):
            m.blob(r * 0.6, r * 0.5, r * 0.6, "rock_d", rng, sub=1, rough=0.3, strata=0.6)
    return m


def gate(L, ter):
    """The Gate: a sea arch from the headland to the beacon stack, walkable on top."""
    ar = L["arch"]
    m = Mesh("LT_GATE")
    rng = rng_for("gate")
    cx = (ar["x0"] + ar["x1"]) / 2; hw = (ar["x1"] - ar["x0"]) / 2
    z0, z1 = ar["z0"] - 1.2, ar["z1"] + 1.2
    zc, half = (ar["z0"] + ar["z1"]) / 2, (ar["z1"] - ar["z0"]) / 2 - 1.4
    n, k = 34, 14
    rings = []
    for i in range(n + 1):
        z = z0 + (z1 - z0) * i / n
        u = (z - zc) / half
        under = ar["y0"] * math.sqrt(max(0.0, 1 - u * u)) if abs(u) < 1 else SEABED - 0.3
        if abs(u) >= 1:
            under = SEABED - 0.3
        top = ar["y1"] - 0.3 * min(1.0, abs(u)) ** 2 if abs(u) < 1.25 else ar["y1"] - 0.3
        top = min(top, ar["y1"])
        ring = []
        for j in range(k):
            a = 2 * math.pi * j / k
            # superellipse section
            ca, sa = math.cos(a), math.sin(a)
            ex = math.copysign(abs(ca) ** 0.55, ca); ey = math.copysign(abs(sa) ** 0.55, sa)
            w = hw * (1.0 + 0.16 * math.sin(z * 0.9 + j) + (0.25 if abs(u) > 0.8 else 0.0))
            x = cx + ex * w + 0.25 * math.sin(z * 1.7 + j * 2.1)
            mid, hh = (top + under) / 2, (top - under) / 2
            y = mid + ey * hh
            if ey > 0.93:
                y = top                     # flat walkway on top
            elif sa > 0:
                y = min(y + 0.18 * math.sin(j * 1.3 + z), top - 0.02)
            ring.append(P(x, y, z))
        rings.append(ring)
    base = len(m.v)
    for ring in rings:
        m.v.extend(ring)
    for i in range(n):
        for j in range(k):
            a = base + i * k + j; b = base + i * k + (j + 1) % k
            c = base + (i + 1) * k + (j + 1) % k; d = base + (i + 1) * k + j
            y = (m.v[a][2] + m.v[c][2]) / 2
            top_face = j in (k // 4 - 1, k // 4, k // 4 + 1) and y > ar["y1"] - 0.5
            band = math.floor((y + 0.4 * math.sin(i * 0.7)) / 1.15)
            role = "ground" if top_face else ("rock_m", "rock_l", "rock_m", "rock_d")[int(band) % 4]
            if y < 0.4: role = "rock_wet"
            for tri in ((a, b, c), (a, c, d)):
                m.f.append(tri); m.fm.append(role); m.ft.append(1.0 + rng.uniform(-0.07, 0.07))
    m.f.append(tuple(base + j for j in range(k))); m.fm.append("rock_d"); m.ft.append(1.0)
    m.f.append(tuple(base + n * k + j for j in range(k - 1, -1, -1))); m.fm.append("rock_d"); m.ft.append(1.0)
    return m


# ================================================================ circulation
def _path_frame(a, b):
    """Frame at node a looking toward node b (horizontal), Blender coords."""
    dx, dy = b["x"] - a["x"], -(b["z"] - a["z"])
    Lh = math.hypot(dx, dy)
    return frame(P(a["x"], a["y"], a["z"]), (dx / Lh, dy / Lh, 0), (-dy / Lh, dx / Lh, 0)), Lh


def structures(L, ter):
    """Stairs, ladder, rope bridge, decks, ramps, paving."""
    m = Mesh("LT_STRUCTURES")
    rng = rng_for("structures")
    nodes = L["nav"]["nodes"]
    for e in L["nav"]["edges"]:
        a, b = nodes[e["a"]], nodes[e["b"]]
        if e["type"] == "stair":
            st = L["nav"]["stairs"].get(e["a"], {})
            w = st.get("width", 1.6); stone = st.get("stone", False)
            M, run = _path_frame(a, b)
            rise = b["y"] - a["y"]
            with m.push(M, T(0, -w / 2, 0)):
                if stone:
                    parts.stair_flight(m, run, rise, w, rng, mat="stone", solid=True, tread_mat="stone_light", n=max(2, int(round(rise / 0.18))))
                    for y in (-0.22, w):
                        for i in range(int(run / 0.9) + 1):
                            x = i * 0.9
                            zb = rise * x / run
                            m.box(x, y, zb - 1.2, min(run, x + 0.9), y + 0.22, zb + rise * 0.9 / run + 0.75, "stone_b", wob=0.02, rng=rng, vary=0.07)
                else:
                    parts.stair_flight(m, run, rise, w, rng, mat="wood_light", rail="both", rail_mat="wood_mid", n=max(2, int(round(rise / 0.19))))
                    # trestle posts down to the rock
                    for i in range(1, int(run / 1.4) + 1):
                        x = i * run / (int(run / 1.4) + 1)
                        zs = rise * x / run
                        for y in (0.06, w - 0.06):
                            wx = a["x"] + (b["x"] - a["x"]) * x / run; wz = a["z"] + (b["z"] - a["z"]) * x / run
                            g = ter.h(wx, wz) - a["y"]
                            if zs - g > 0.3:
                                m.box(x - 0.05, y - 0.05, g - 0.3, x + 0.05, y + 0.05, zs - 0.1, "wood_dark", wob=0.01, rng=rng)
                        m.box(x - 0.04, 0.0, zs - 0.32, x + 0.04, w, zs - 0.2, "wood_dark")
        elif e["type"] == "ladder":
            p0, p1 = P(a["x"], a["y"], a["z"]), P(b["x"], b["y"] + 0.9, b["z"] + (b["z"] - a["z"]) * 0.22)
            for sx in (-0.26, 0.26):
                m.beam((p0[0] + sx, p0[1], p0[2]), (p1[0] + sx, p1[1], p1[2]), 0.06, 0.07, "wood_mid")
            n = int((b["y"] - a["y"]) / 0.3)
            for i in range(1, n + 1):
                k = i / (n + 3)
                q = [p0[j] + (p1[j] - p0[j]) * k for j in range(3)]
                m.box(q[0] - 0.3, q[1] - 0.02, q[2] - 0.02, q[0] + 0.3, q[1] + 0.02, q[2] + 0.02, "wood_light")
        elif e["type"] == "bridge":
            M, run = _path_frame(a, b)
            rise = b["y"] - a["y"]
            w = 1.3
            with m.push(M):
                n = int(run / 0.24)
                def zline(x):
                    k = x / run
                    return rise * k - 0.28 * math.sin(math.pi * k)
                for i in range(n):
                    x = (i + 0.5) * run / n
                    with m.push(T(x, 0, zline(x) - 0.02), Ry(-math.atan2(zline(x + 0.1) - zline(x - 0.1), 0.2))):
                        m.box(-0.105, -w / 2, -0.03, 0.105, w / 2, 0.0, "wood_light" if rng.random() < 0.8 else "wood_grey", wob=0.008, rng=rng, vary=0.1)
                for y in (-w / 2, w / 2):
                    for (x0, zt) in ((0.0, 0.0), (run, rise)):
                        m.box(x0 - 0.09, y - 0.09, zt - 1.2, x0 + 0.09, y + 0.09, zt + 1.45, "wood_dark", wob=0.015, rng=rng)
                    seg = 26
                    for i in range(seg):
                        xa, xb = run * i / seg, run * (i + 1) / seg
                        for hgt, sag in ((1.05, 0.55), (0.0, 0.3)):
                            za = rise * xa / run + hgt - sag * math.sin(math.pi * xa / run) + (0.25 if hgt else -0.05)
                            zb = rise * xb / run + hgt - sag * math.sin(math.pi * xb / run) + (0.25 if hgt else -0.05)
                            m.beam((xa, y, za), (xb, y, zb), 0.035, 0.035, "rope")
                        if i % 2 == 0:
                            xm = xa
                            m.beam((xm, y, zline(xm) - 0.02), (xm, y, rise * xm / run + 1.3 - 0.55 * math.sin(math.pi * xm / run)), 0.02, 0.02, "rope")
        elif e["type"] == "ramp":
            M, run = _path_frame(a, b)
            rise = b["y"] - a["y"]
            if abs(rise) > 0.05:
                with m.push(M):
                    n = max(2, int(run / 0.22))
                    for i in range(n):
                        x0, x1 = run * i / n, run * (i + 1) / n
                        z = rise * (i + 0.5) / n
                        m.box(x0 + 0.005, -0.7, z - 0.05, x1 - 0.005, 0.7, z, "wood_light", wob=0.006, rng=rng, vary=0.1)
        if e["type"] in ("walk", "door") and a["kind"] == "ground" and b["kind"] == "ground":
            # paving: irregular pale flags, so routes read from the overview
            M, run = _path_frame(a, b)
            w = 0.62 if e["type"] == "door" else 0.8
            with m.push(M):
                x = 0.0
                while x < run:
                    Ls = min(rng.uniform(0.45, 0.85), run - x)
                    if Ls < 0.12: break
                    split = rng.uniform(-0.2, 0.2)
                    for y0, y1 in ((-w, split), (split, w)):
                        m.box(x + 0.02, y0 + 0.02 + rng.uniform(-0.04, 0.04), -0.05, x + Ls - 0.02, y1 - 0.02 + rng.uniform(-0.04, 0.04), 0.022,
                              "path", wob=0.012, rng=rng, vary=0.06)
                    x += Ls
    # decks
    for dk in L["decks"]:
        x0, x1, z0, z1 = dk["rect"]; y = dk["y"]
        along_x = (x1 - x0) >= (z1 - z0)
        grey = dk["id"] in ("pier_A", "pier_B", "slipway")
        if along_x:
            n = int((x1 - x0) / 0.24)
            for i in range(n):
                a_, b_ = x0 + (x1 - x0) * i / n, x0 + (x1 - x0) * (i + 1) / n
                m.box(*P(a_ + 0.006, y - 0.05, z0)[:2], y - 0.05, *P(b_ - 0.006, y, z1)[:2], y, "wood_grey" if grey and rng.random() < 0.5 else "wood_light", wob=0.006, rng=rng, vary=0.1)
        else:
            n = int((z1 - z0) / 0.24)
            for i in range(n):
                a_, b_ = z0 + (z1 - z0) * i / n, z0 + (z1 - z0) * (i + 1) / n
                m.box(x0, -b_ + 0.006, y - 0.05, x1, -a_ - 0.006, y, "wood_grey" if grey and rng.random() < 0.5 else "wood_light", wob=0.006, rng=rng, vary=0.1)
        # bearers and piles
        nxp = max(2, int((x1 - x0) / 2.2) + 1); nzp = max(2, int((z1 - z0) / 2.2) + 1)
        for i in range(nxp):
            x = x0 + 0.12 + (x1 - x0 - 0.24) * i / (nxp - 1)
            m.box(x - 0.06, -z1, y - 0.2, x + 0.06, -z0, y - 0.05, "wood_dark")
            for j in range(nzp):
                z = z0 + 0.12 + (z1 - z0 - 0.24) * j / (nzp - 1)
                if 0 < i < nxp - 1 and 0 < j < nzp - 1:
                    continue
                g = min(ter.h(x, z), y - 0.3)
                top = y + (0.45 if (i + j) % 2 == 0 and dk["id"] != "stilt_deck" and dk["id"] != "slipway" else -0.05)
                with m.push(T(x, -z, 0)):
                    m.cyl(0.11, top - g + 0.5, 7, "wood_dark", z0=g - 0.5, r_top=0.095)
    return m


# ================================================================ boats
def boat(m, rng, kind="skiff", role="boat_a"):
    """Hull lofted from stations; origin at waterline centre, bow toward +x."""
    Lh = 3.7 if kind == "skiff" else 5.6
    bm = 0.72 if kind == "skiff" else 1.05
    dp = 0.55 if kind == "skiff" else 0.8
    n = 10
    st = []
    for i in range(n + 1):
        u = i / n
        x = -Lh / 2 + Lh * u
        hb = bm * (math.sin(math.pi * min(1.0, u * 1.12 + 0.07)) ** 0.6) * (0.55 + 0.45 * min(1.0, (1 - u) * 3.2)) if u < 1 else 0.02
        hb = max(hb, 0.03)
        sheer = 0.34 + 0.22 * (2 * u - 1) ** 2 + (0.12 * u)
        keel = -dp * (0.55 + 0.45 * math.sin(math.pi * u) ** 0.5) * 0.6
        st.append((x, hb, sheer, keel))
    k = 5
    def section(x, hb, sheer, keel, inset=0.0):
        pts = []
        for j in range(k + 1):
            v = j / k
            y = (hb - inset) * math.sin(v * math.pi / 2) ** 0.75
            z = keel + inset + (sheer - keel - inset) * (1 - math.cos(v * math.pi / 2)) ** 1.25
            pts.append((y, z))
        return pts
    for i in range(n):
        s0, s1 = section(*st[i]), section(*st[i + 1])
        i0, i1 = section(*st[i], inset=0.05), section(*st[i + 1], inset=0.05)
        for j in range(k):
            for sg in (1, -1):
                r = role if j >= k - 2 else ("boat_hull" if j < k - 3 else "frame")
                pts = [(st[i][0], sg * s0[j][0], s0[j][1]), (st[i + 1][0], sg * s1[j][0], s1[j][1]),
                       (st[i + 1][0], sg * s1[j + 1][0], s1[j + 1][1]), (st[i][0], sg * s0[j + 1][0], s0[j + 1][1]),
                       (st[i][0], sg * i0[j][0], i0[j][1]), (st[i + 1][0], sg * i1[j][0], i1[j][1]),
                       (st[i + 1][0], sg * i1[j + 1][0], i1[j + 1][1]), (st[i][0], sg * i0[j + 1][0], i0[j + 1][1])]
                m.add(pts, Mesh._BOX_F, r, 1.0 + rng.uniform(-0.05, 0.05))
    # transom, gunwale, thwarts, floor boards
    x0, hb0, sh0, kl0 = st[0]
    m.box(x0 - 0.03, -hb0, kl0, x0 + 0.03, hb0, sh0, role)
    for t in (0.3, 0.55, 0.78) if kind == "skiff" else (0.2, 0.42):
        i = int(t * n); x, hb, sh, kl = st[i]
        m.box(x - 0.11, -hb + 0.04, sh - 0.2, x + 0.11, hb - 0.04, sh - 0.16, "wood_light", rng=rng, vary=0.08)
    for i in range(2, n - 2):
        x, hb, sh, kl = st[i]
        m.box(x - 0.17, -hb * 0.55, kl + 0.1, x + 0.17, hb * 0.55, kl + 0.13, "wood_mid", rng=rng, vary=0.1)
    if kind == "skiff":
        for sg in (-1, 1):
            m.beam((-0.9, sg * 0.3, 0.3), (1.2, sg * 0.42, 0.42), 0.05, 0.04, "wood_light")
            m.box(1.2, sg * 0.42 - 0.07, 0.40, 1.65, sg * 0.42 + 0.07, 0.43, "wood_light")
    else:
        # wheelhouse, mast, boom, net pile
        m.box(-1.5, -0.55, 0.1, -0.2, 0.55, 1.45, "frame", wob=0.01, rng=rng)
        m.box(-1.6, -0.65, 1.45, -0.1, 0.65, 1.52, role)
        for sg in (-1, 1):
            m.box(-1.2, sg * 0.56, 0.85, -0.5, sg * 0.57, 1.25, "glass")
        m.box(-0.2, -0.4, 0.85, -0.19, 0.4, 1.25, "glass")
        with m.push(T(0.6, 0, 0.1)):
            m.cyl(0.06, 3.4, 7, "wood_mid", r_top=0.04)
        m.beam((0.6, 0, 1.6), (2.3, 0, 2.0), 0.05, 0.05, "wood_mid")
        with m.push(T(1.6, 0, 0.35)):
            m.blob(0.55, 0.45, 0.22, "net", rng, sub=1, rough=0.25)
        with m.push(T(0.61, 0, 3.2)):
            m.box(0, -0.01, 0, 0.45, 0.01, 0.28, role)
    # mooring fender
    with m.push(T(0.4, bm * 0.9, 0.25)):
        m.blob(0.1, 0.1, 0.18, "float_b", rng, sub=0, rough=0.05)


def boats(L):
    out = {}
    info = []
    nodes = L["nav"]["nodes"]
    roles = ["boat_a", "boat_b", "boat_c", "boat_d", "boat_b", "boat_a"]
    for i, bt in enumerate(L["boats"]):
        rng = rng_for("boat", bt["id"])
        m = Mesh(bt["id"])
        boat(m, rng, bt["kind"], roles[i % len(roles)])
        nd = nodes[bt["mooring"]]
        yaw = 0.0 if bt["mooring"] == "moor_BW" else -90.0        # bow east along the boardwalk, else bow south
        out[bt["id"]] = m
        info.append(dict(id=bt["id"], kind=bt["kind"], mooring=bt["mooring"], pos=[nd["x"], 0.0, nd["z"]], yaw_deg=yaw))
    return out, info


# ================================================================ props
def lamp_post(m, rng, h=2.7):
    m.box(-0.11, -0.11, -0.3, 0.11, 0.11, 0.14, "stone_b", wob=0.01, rng=rng)
    m.box(-0.045, -0.045, 0.1, 0.045, 0.045, h, "wood_dark", wob=0.006, rng=rng)
    m.beam((0, 0, h - 0.12), (0.5, 0, h - 0.02), 0.045, 0.045, "wood_dark")
    m.beam((0, 0, h - 0.55), (0.3, 0, h - 0.1), 0.035, 0.035, "wood_dark")
    with m.push(T(0.46, 0, h - 0.06)):
        F.lamp_hanging(m, rng, drop=0.1)
    return (0.46, 0.0, h - 0.34)


def palm(m, rng, h=5.0):
    lean = rng.uniform(0.05, 0.22); az = rng.uniform(0, 6.28)
    n = 8; pts = []
    for i in range(n + 1):
        k = i / n
        off = lean * h * k * k
        pts.append((math.cos(az) * off, math.sin(az) * off, h * k))
    for i in range(n):
        r0, r1 = 0.17 - 0.07 * i / n, 0.17 - 0.07 * (i + 1) / n
        with m.push(T(*pts[i])):
            m.cyl(r0 + 0.02, (pts[i + 1][2] - pts[i][2]) * 1.02, 6, "trunk", r_top=r1)
    top = pts[-1]
    for j in range(9):
        a = 2 * math.pi * j / 9 + rng.uniform(-0.2, 0.2)
        Lf = rng.uniform(1.7, 2.4); droop = rng.uniform(0.7, 1.3)
        prev = None
        for s in range(7):
            k = s / 6
            r = Lf * k; z = 0.45 * math.sin(k * math.pi * 0.7) - droop * k * k
            w = 0.34 * math.sin(math.pi * min(1.0, k * 1.1 + 0.08)) + 0.03
            c = (top[0] + math.cos(a) * r, top[1] + math.sin(a) * r, top[2] + z)
            l_ = (c[0] - math.sin(a) * w, c[1] + math.cos(a) * w, c[2] - 0.1 * w)
            r_ = (c[0] + math.sin(a) * w, c[1] - math.cos(a) * w, c[2] - 0.1 * w)
            if prev:
                role = "foliage_a" if j % 2 else "foliage_c"
                tint = 1.0 + rng.uniform(-0.08, 0.08)
                m.add([prev[1], prev[0], c, l_], [(0, 1, 2, 3), (3, 2, 1, 0)], role, tint)
                m.add([prev[0], prev[2], r_, c], [(0, 1, 2, 3), (3, 2, 1, 0)], role, tint * 0.9)
            prev = (c, l_, r_)
    for j in range(3):
        with m.push(T(top[0] + rng.uniform(-0.15, 0.15), top[1] + rng.uniform(-0.15, 0.15), top[2] - 0.2)):
            m.blob(0.1, 0.1, 0.12, "wood_light", rng, sub=0, rough=0.1)


def round_tree(m, rng, h=3.6, big=False):
    r = 0.14 if not big else 0.5
    m.cyl(r * 1.4, h * 0.55, 7, "trunk", r_top=r * 0.8)
    if big:
        for a in range(5):
            an = a * 1.26 + rng.uniform(-0.2, 0.2)
            m.beam((0, 0, h * 0.45), (math.cos(an) * h * 0.38, math.sin(an) * h * 0.38, h * 0.8), 0.22, 0.22, "trunk")
    k = 7 if big else 4
    for i in range(k):
        a = rng.uniform(0, 6.28); d = rng.uniform(0, h * (0.36 if big else 0.2))
        s = h * rng.uniform(0.2, 0.32) * (1.25 if big else 1.0)
        with m.push(T(math.cos(a) * d, math.sin(a) * d, h * rng.uniform(0.6, 0.95))):
            m.blob(s, s * rng.uniform(0.8, 1.1), s * 0.8, rng.choice(["foliage_a", "foliage_b", "foliage_c"]), rng, sub=1, rough=0.2)


def shrub(m, rng):
    for i in range(rng.randint(2, 4)):
        s = rng.uniform(0.25, 0.5)
        with m.push(T(rng.uniform(-0.35, 0.35), rng.uniform(-0.35, 0.35), s * 0.6)):
            m.blob(s, s, s * 0.8, rng.choice(["foliage_a", "foliage_b", "foliage_c"]), rng, sub=0, rough=0.3)
    if rng.random() < 0.4:
        for i in range(4):
            with m.push(T(rng.uniform(-0.4, 0.4), rng.uniform(-0.4, 0.4), rng.uniform(0.45, 0.7))):
                m.blob(0.06, 0.06, 0.05, rng.choice(["flower_a", "flower_b", "flower_c"]), rng, sub=0, rough=0.1)


def well(m, rng):
    n = 12
    for i in range(n):
        a = 2 * math.pi * i / n
        for k in range(3):
            m.cbox(math.cos(a + k * 0.26) * 0.75, math.sin(a + k * 0.26) * 0.75, 0.14 + k * 0.27, 0.42, 0.26, 0.26, rng.choice(["stone", "stone_b", "stone_light"]),
                   rz=a + k * 0.26 + math.pi / 2, wob=0.02, rng=rng, vary=0.08)
    m.cyl(0.62, 0.05, 12, "water_still", z0=0.5)
    for x in (-0.82, 0.82):
        m.box(x - 0.06, -0.06, 0, x + 0.06, 0.06, 2.0, "wood_dark", wob=0.01, rng=rng)
    with m.push(T(0, 0, 0)):
        parts.gable_roof(m, 1.9, 1.3, 2.0, 30, rng, eave=0.12, verge=0.1, sag=0.0, cover="tin", barge_mat="wood_mid")
    with m.push(T(-0.8, 0, 1.45), Ry(math.pi / 2)):
        m.cyl(0.07, 1.6, 8, "wood_mid")
    m.box(-0.008, -0.008, 0.75, 0.008, 0.008, 1.45, "rope")
    with m.push(T(0, 0, 0.6)):
        m.lathe([(0.1, 0), (0.13, 0.2), (0.12, 0.22)], 8, "wood_mid")


def cistern(m, rng):
    for x in (-1.0, 1.0):
        for y in (-1.0, 1.0):
            m.box(x - 0.09, y - 0.09, -0.2, x + 0.09, y + 0.09, 1.7, "wood_dark", wob=0.015, rng=rng)
    for sg in (-1, 1):
        m.beam((-1.0, sg, 0.2), (1.0, sg, 1.5), 0.07, 0.07, "wood_dark"); m.beam((sg, -1.0, 1.5), (sg, 1.0, 0.2), 0.07, 0.07, "wood_dark")
    m.box(-1.25, -1.25, 1.7, 1.25, 1.25, 1.82, "wood_mid")
    n = 16
    for i in range(n):
        a0 = 2 * math.pi * i / n
        m.cbox(math.cos(a0) * 1.1, math.sin(a0) * 1.1, 2.72, 0.44, 0.06, 1.8, "wood_light", rz=a0 + math.pi / 2, rng=rng, vary=0.1)
    for z in (2.1, 2.75, 3.4):
        m.lathe([(1.14, z), (1.16, z), (1.16, z + 0.06), (1.14, z + 0.06)], 16, "iron")
    m.lathe([(1.25, 3.62), (0.7, 3.95), (0.05, 4.2)], 16, "tin")
    m.cyl(0.05, 1.7, 6, "tin_bare", z0=0.0)


def lookout(m, rng):
    for i in range(9):
        m.box(-1.3 + i * 0.29, -1.0, 0.0, -1.3 + (i + 1) * 0.29 - 0.01, 1.0, 0.05, "wood_light", rng=rng, vary=0.1)
    for (ax, ay), (bx, by) in (((-1.3, -1.0), (1.3, -1.0)), ((-1.3, -1.0), (-1.3, 1.0))):
        m.beam((ax, ay, 1.0), (bx, by, 1.0), 0.07, 0.05, "frame")
        n = 8
        for i in range(n + 1):
            x, y = ax + (bx - ax) * i / n, ay + (by - ay) * i / n
            m.box(x - 0.03, y - 0.03, 0, x + 0.03, y + 0.03, 1.0, "frame")
    with m.push(T(0.3, 0.5, 0.05), Rz(math.pi)):
        F.bench(m, rng)
    m.box(-0.85, -0.6, 0.05, -0.79, -0.54, 1.35, "iron")
    with m.push(T(-0.82, -0.57, 1.4), Ry(math.pi / 2 - 0.15), Rz(0.6)):
        m.cyl(0.05, 0.55, 8, "brass", z0=-0.2, r_top=0.07)
    # flag
    m.box(1.2, 0.9, 0, 1.26, 0.96, 4.2, "wood_mid")
    for i in range(5):
        m.box(1.26 + i * 0.22, 0.925, 3.5 + 0.04 * math.sin(i * 1.4), 1.26 + (i + 1) * 0.22, 0.935, 4.1 + 0.04 * math.sin(i * 1.4 + 0.7), "fabric_a" if i % 2 else "fabric_white")


def beacon(m, rng):
    for i in range(4):
        a = math.pi / 4 + i * math.pi / 2
        m.beam((math.cos(a) * 1.0, math.sin(a) * 1.0, -0.2), (math.cos(a) * 0.45, math.sin(a) * 0.45, 4.2), 0.12, 0.12, "wood_dark")
    for z, r in ((1.2, 0.86), (2.6, 0.67)):
        for i in range(4):
            a0, a1 = math.pi / 4 + i * math.pi / 2, math.pi / 4 + (i + 1) * math.pi / 2
            m.beam((math.cos(a0) * r, math.sin(a0) * r, z), (math.cos(a1) * r, math.sin(a1) * r, z), 0.08, 0.08, "wood_dark")
            m.beam((math.cos(a0) * r, math.sin(a0) * r, z), (math.cos(a1) * (r - 0.19), math.sin(a1) * (r - 0.19), z + 1.4), 0.05, 0.05, "wood_mid")
    m.box(-0.8, -0.8, 4.2, 0.8, 0.8, 4.3, "wood_mid")
    for x in (-0.75, 0.75):
        for y in (-0.75, 0.75):
            m.box(x - 0.03, y - 0.03, 4.3, x + 0.03, y + 0.03, 5.0, "iron")
    with m.push(T(0, 0, 4.3)):
        m.lathe([(0.2, 0), (0.3, 0.15), (0.3, 0.6), (0.2, 0.75)], 8, "emit_lamp")
        m.lathe([(0.34, 0.02), (0.36, 0.02), (0.36, 0.72), (0.34, 0.72)], 8, "glass")
        m.lathe([(0.2, 0.75), (0.85, 0.9), (0.05, 1.5)], 8, "tin")
    return (0, 0, 4.7)


def props(L, ter):
    """Lamps, landmarks, vegetation, harbour clutter."""
    m = Mesh("LT_PROPS")
    veg = Mesh("LT_VEG")
    rng = rng_for("props")
    nodes = L["nav"]["nodes"]
    info = dict(lamps=[], landmarks=[])

    def free(x, z, r=0.6):
        g = ground_h(L, x, z)
        if g is None:
            return False
        for dx, dz in ((0, 0), (r, 0), (-r, 0), (0, r), (0, -r)):
            if ter.is_keep(x + dx, z + dz) or ground_h(L, x + dx, z + dz) != g:
                return False
        return True

    def beside(n, dist=1.75, fr=0.25):
        """A free spot next to a walk node, else as close as possible."""
        best = None
        for d in (dist, dist + 0.5, dist - 0.4, dist + 1.0):
            for k in range(12):
                a = k * math.pi / 6 + 0.26
                x, z = n["x"] + math.cos(a) * d, n["z"] + math.sin(a) * d
                if n["kind"] == "deck":
                    continue
                if free(x, z, fr):
                    return x, z
        return None

    for nid in L["lamps"]:
        n = nodes[nid]
        spot = beside(n)
        if spot is None:
            # deck / pier lamps stand on the deck edge
            x, z = n["x"] + 1.0, n["z"] + 0.2
        else:
            x, z = spot
        ang = math.atan2(-(n["z"] - z), n["x"] - x)
        with m.push(T(*P(x, n["y"], z)), Rz(ang)):
            lp = lamp_post(m, rng)
            wp = m.M[:3, :3] @ np.array(lp) + m.M[:3, 3]
        info["lamps"].append(dict(id="LAMP_" + nid, node=nid, pos=[round(float(wp[0]), 3), round(float(wp[2]), 3), round(float(-wp[1]), 3)]))

    def landmark(name, nid, fn, dist, **kw):
        n = nodes[nid]
        spot = beside(n, dist, fr=kw.pop("fr", 1.0)) or (n["x"] + dist, n["z"])
        with m.push(T(*P(spot[0], n["y"], spot[1]))):
            r = fn(veg if kw.pop("veg", False) else m, rng, **kw)
        d = dict(id=name, node=nid, pos=[round(spot[0], 3), n["y"], round(spot[1], 3)])
        if r:
            d["light"] = [round(spot[0] + r[0], 3), round(n["y"] + r[2], 3), round(spot[1] - r[1], 3)]
        info["landmarks"].append(d)

    landmark("well", "plaza", well, 2.6, fr=1.0)
    landmark("cistern", "k_cistern", cistern, 2.4, fr=1.3)
    landmark("lookout", "k_look", lookout, 2.0, fr=1.2)
    landmark("great_tree", "k_tree", round_tree, 2.4, fr=0.6, veg=True, h=7.5, big=True)
    landmark("beacon", "st_beacon", beacon, 1.9, fr=0.8)

    # vegetation: palms low, round trees high, shrubs anywhere there is room
    count = dict(palm=0, tree=0, shrub=0)
    for _ in range(5000):
        x, z = rng.uniform(-44, 42), rng.uniform(-34, 28)
        g = ground_h(L, x, z)
        if g is None:
            continue
        k = rng.random()
        if k < 0.12 and count["palm"] < 16 and g < 6 and free(x, z, 0.8):
            with veg.push(T(*P(x, g, z))): palm(veg, rng, h=rng.uniform(3.8, 6.0))
            count["palm"] += 1
        elif k < 0.3 and count["tree"] < 22 and g > 5 and free(x, z, 1.0):
            with veg.push(T(*P(x, g, z))): round_tree(veg, rng, h=rng.uniform(2.6, 4.4))
            count["tree"] += 1
        elif count["shrub"] < 90 and free(x, z, 0.45):
            with veg.push(T(*P(x, g, z))): shrub(veg, rng)
            count["shrub"] += 1
    info["vegetation"] = count
    # harbour clutter on the quay and decks: crates, barrels, coiled rope, bollards
    for nid in ("q_n_pierA", "q_n_pierB", "q_n_mkt", "q_w_yard", "q_w_loft", "q_n_wh", "q_corner", "q_w_bw"):
        n = nodes[nid]
        spot = beside(n, 1.9, fr=0.5)
        if not spot:
            continue
        with m.push(T(*P(spot[0], n["y"], spot[1])), Rz(rng.uniform(0, 6.28))):
            F.loading_point(m, rng)
            with m.push(T(0.7, 0.1, 0)):
                m.lathe([(0.2, 0), (0.27, 0.3), (0.27, 0.5), (0.2, 0.8), (0.0, 0.8)], 9, "wood_mid")
            with m.push(T(-0.5, -0.3, 0)):
                m.lathe([(0.25, 0), (0.25, 0.1), (0.12, 0.1), (0.12, 0.0)], 10, "rope")
    for nid in ("pierA_end", "pierB_end", "pierA_mid"):
        n = nodes[nid]
        with m.push(T(*P(n["x"] + 0.9, n["y"], n["z"] + 0.6))):
            m.lathe([(0.1, 0), (0.1, 0.3), (0.15, 0.36), (0.15, 0.42), (0.0, 0.44)], 8, "iron")
    return m, veg, info


def sea_preview(L):
    """Static faceted sea for Blender renders (Godot uses its own shader)."""
    m = Mesh("LT_SEA_PREVIEW")
    rng = rng_for("sea")
    s = 2.0
    xs = np.arange(-70, 70 + 1e-6, s); zs = np.arange(-56, 54 + 1e-6, s)
    Hh = {}
    for j, z in enumerate(zs):
        for i, x in enumerate(xs):
            Hh[(i, j)] = (x + rng.uniform(-0.5, 0.5), -(z + rng.uniform(-0.5, 0.5)), 0.0 + rng.uniform(-0.07, 0.07))
    for j in range(len(zs) - 1):
        for i in range(len(xs) - 1):
            a, b, c, d = Hh[(i, j)], Hh[(i + 1, j)], Hh[(i + 1, j + 1)], Hh[(i, j + 1)]
            base = len(m.v); m.v.extend([a, b, c, d])
            for tri in ((0, 3, 2), (0, 2, 1)):
                m.f.append(tuple(base + q for q in tri)); m.fm.append("sea"); m.ft.append(1.0 + rng.uniform(-0.1, 0.1))
    return m
