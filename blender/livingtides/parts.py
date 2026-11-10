"""Architectural kit of parts.  Pure geometry (no bpy).

Wall-local frame used by every facade element:
    x : along the wall, 0 at the left end as seen from outside
    y : 0 on the outer face, +y into the building (wall thickness)
    z : up
Everything that decorates a facade (windows, doors, balconies, timbering)
is authored in this frame and placed with Vol.side(...).
"""
from __future__ import annotations
import math
import numpy as np
from .geom import Mesh, T, Rz, Rx, Ry, S, frame


# ================================================================ walls
def wall(m: Mesh, W, H, t, openings, mat_out, mat_in, mat_rev=None, z0=0.0):
    """Solid wall slab with true rectangular holes.  openings: (x0, x1, z0, z1)."""
    mat_rev = mat_rev or mat_out
    ops = [(max(0, a), min(W, b), max(z0, c), min(z0 + H, d)) for a, b, c, d in openings]
    xs = sorted({0.0, W} | {v for o in ops for v in o[:2]})
    zs = sorted({z0, z0 + H} | {v for o in ops for v in o[2:]})

    def solid(i, j):
        if i < 0 or j < 0 or i >= len(xs) - 1 or j >= len(zs) - 1:
            return False
        cx, cz = (xs[i] + xs[i + 1]) / 2, (zs[j] + zs[j + 1]) / 2
        return not any(a < cx < b and c < cz < d for a, b, c, d in ops)

    pts, faces, mats = [], [], []

    def quad(a, b, c, d, mat):
        k = len(pts); pts.extend((a, b, c, d)); faces.append((k, k + 1, k + 2, k + 3)); mats.append(mat)

    for i in range(len(xs) - 1):
        for j in range(len(zs) - 1):
            if not solid(i, j):
                continue
            x0, x1, a, b = xs[i], xs[i + 1], zs[j], zs[j + 1]
            quad((x0, 0, a), (x1, 0, a), (x1, 0, b), (x0, 0, b), mat_out)
            quad((x1, t, a), (x0, t, a), (x0, t, b), (x1, t, b), mat_in)
            if not solid(i - 1, j): quad((x0, 0, a), (x0, 0, b), (x0, t, b), (x0, t, a), mat_rev)
            if not solid(i + 1, j): quad((x1, 0, a), (x1, t, a), (x1, t, b), (x1, 0, b), mat_rev)
            if not solid(i, j - 1): quad((x0, 0, a), (x0, t, a), (x1, t, a), (x1, 0, a), mat_rev)
            if not solid(i, j + 1): quad((x0, 0, b), (x1, 0, b), (x1, t, b), (x0, t, b), mat_rev)
    m.add(pts, faces, mats)


def gable_wall(m, W, rise, t, mat_out, mat_in, z0=0.0, apex=0.5):
    """Triangular wall top.  apex = ridge position along the wall (0..1)."""
    poly = [(0, z0), (W, z0), (W * apex, z0 + rise)]
    n = len(poly)
    pts = [(x, 0, z) for x, z in poly] + [(x, t, z) for x, z in poly]
    faces = [(0, 1, 2), (5, 4, 3)]
    mats = [mat_out, mat_in]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, i + n, j + n, j)); mats.append(mat_out)
    m.add(pts, faces, mats)


class Vol:
    """A rectangular building volume: owns its four walls and their openings.
    Local frame: centred on (cx, cy), base at z, front = -Y."""
    SIDES = ("front", "right", "back", "left")

    def __init__(self, W, D, H, t=0.28, cx=0.0, cy=0.0, z=0.0,
                 mat_out="plaster_main", mat_in="plaster_in"):
        self.W, self.D, self.H, self.t = W, D, H, t
        self.cx, self.cy, self.z = cx, cy, z
        self.mat_out, self.mat_in = mat_out, mat_in
        self.openings = {s: [] for s in self.SIDES}
        self.skip = set()

    def width(self, side):
        return self.W if side in ("front", "back") else self.D

    def side(self, side):
        """Matrix: wall-local -> building-local for the *full* facade."""
        W, D = self.W / 2, self.D / 2
        base = T(self.cx, self.cy, self.z)
        if side == "front": return base @ T(-W, -D, 0)
        if side == "back":  return base @ T(W, D, 0) @ Rz(math.pi)
        if side == "right": return base @ T(W, -D, 0) @ Rz(math.pi / 2)
        if side == "left":  return base @ T(-W, D, 0) @ Rz(-math.pi / 2)
        raise KeyError(side)

    def cut(self, side, x0, x1, z0, z1):
        self.openings[side].append((x0, x1, z0, z1))

    def build_walls(self, m, mats=None):
        """mats: optional {side: mat_out}.  Side walls are inset by t so that
        corners do not overlap."""
        mats = mats or {}
        for s in self.SIDES:
            if s in self.skip:
                continue
            mo = mats.get(s, self.mat_out)
            if s in ("front", "back"):
                with m.push(self.side(s)):
                    wall(m, self.W, self.H, self.t, self.openings[s], mo, self.mat_in)
            else:
                ops = [(a - self.t, b - self.t, c, d) for a, b, c, d in self.openings[s]]
                with m.push(self.side(s), T(self.t, 0, 0)):
                    wall(m, self.D - 2 * self.t, self.H, self.t, ops, mo, self.mat_in)

    def local(self, side, x, y=0.0, z=0.0):
        """Building-local position of a wall-local point."""
        M = self.side(side)
        return tuple(M[:3, :3] @ np.array([x, y, z]) + M[:3, 3])

    def yaw(self, side):
        """Yaw (rad) of the outward normal's opposite: direction facing INTO the room."""
        return {"front": math.pi / 2, "right": math.pi, "back": -math.pi / 2, "left": 0.0}[side]


# ================================================================ openings
def shutter_leaf(m, w, h, rng, mat="trim", style="louver", th=0.035, y0=0.0):
    """Leaf with origin at hinge bottom, extending +x."""
    y1 = y0 + th
    fw = 0.06
    m.box(0, y0, 0, fw, y1, h, mat); m.box(w - fw, y0, 0, w, y1, h, mat)
    m.box(fw, y0, 0, w - fw, y1, fw, mat); m.box(fw, y0, h - fw, w - fw, y1, h, mat)
    if style == "louver":
        n = max(4, int(h / 0.11))
        for i in range(n):
            z = fw + (h - 2 * fw) * (i + 0.5) / n
            with m.push(T(w / 2, (y0 + y1) / 2, z), Rx(0.5)):
                m.box(-w / 2 + fw, -0.008, -0.035, w / 2 - fw, 0.008, 0.035, mat)
    else:
        m.box(fw, y0 + 0.008, fw, w - fw, y1 - 0.008, h - fw, mat)
        m.beam((fw, y0 - 0.006, fw + 0.02), (w - fw, y0 - 0.006, h - fw - 0.02), 0.012, 0.07, mat, up=(0, 1, 0))


def window(m, x0, x1, z0, z1, t, rng, shutters="open", box=False, lintel="wood", arch=False,
           mullions=(1, 1), frame_mat="trim", shutter_style="louver", sill=True):
    """Window dressing for an opening already cut in the wall (wall-local)."""
    w, h = x1 - x0, z1 - z0
    fw = 0.065
    ya, yb = 0.05, 0.13
    for bx in ((x0, x0 + fw, z0, z1), (x1 - fw, x1, z0, z1), (x0 + fw, x1 - fw, z0, z0 + fw),
               (x0 + fw, x1 - fw, z1 - fw, z1)):
        m.box(bx[0], ya, bx[2], bx[1], yb, bx[3], frame_mat)
    nx, nz = mullions
    for i in range(1, nx + 1):
        x = x0 + w * i / (nx + 1)
        m.box(x - 0.022, ya + 0.01, z0 + fw, x + 0.022, yb - 0.01, z1 - fw, frame_mat)
    for j in range(1, nz + 1):
        z = z0 + h * j / (nz + 1)
        m.box(x0 + fw, ya + 0.01, z - 0.022, x1 - fw, yb - 0.01, z + 0.022, frame_mat)
    m.box(x0 + fw, 0.082, z0 + fw, x1 - fw, 0.094, z1 - fw, "glass")
    if arch:
        arch_infill(m, x0, x1, z1 - w * 0.32, z1, t, "plaster_accent")
        voussoirs(m, x0, x1, z1 - w * 0.32, z1, rng)
    elif lintel == "wood":
        m.box(x0 - 0.16, -0.035, z1, x1 + 0.16, 0.08, z1 + 0.17, "wood_dark", wob=0.012, rng=rng)
    elif lintel == "stone":
        m.box(x0 - 0.12, -0.04, z1, x1 + 0.12, 0.08, z1 + 0.16, "stone_light", wob=0.01, rng=rng)
    if sill:
        m.box(x0 - 0.10, -0.11, z0 - 0.075, x1 + 0.10, 0.10, z0, "stone_light", wob=0.008, rng=rng)
    if shutters:
        lw = w / 2
        a = math.radians(rng.uniform(150, 174)) if shutters == "open" else math.radians(rng.uniform(20, 60))
        with m.push(T(x0, -0.012, z0), Rz(-a)):
            shutter_leaf(m, lw, h, rng, style=shutter_style, y0=0.0)
        a2 = math.radians(rng.uniform(150, 174)) if shutters == "open" else math.radians(rng.uniform(20, 60))
        with m.push(T(x1, -0.012, z0), Rz(-(math.pi - a2))):
            with m.push(T(0, 0, 0), S(1, -1, 1)):
                # mirrored in y so the leaf thickness sits outside the wall
                shutter_leaf(m, lw, h, rng, style=shutter_style, y0=0.0)
    if box:
        flower_box(m, x0 + 0.02, x1 - 0.02, z0 - 0.09, rng)


def flower_box(m, x0, x1, ztop, rng):
    m.box(x0, -0.30, ztop - 0.20, x1, -0.10, ztop, "wood_mid", wob=0.01, rng=rng)
    m.box(x0 + 0.03, -0.27, ztop - 0.03, x1 - 0.03, -0.13, ztop + 0.01, "soil")
    n = max(3, int((x1 - x0) / 0.16))
    for i in range(n):
        x = x0 + (x1 - x0) * (i + 0.5) / n
        with m.push(T(x, -0.20 + rng.uniform(-0.03, 0.01), ztop + 0.07 + rng.uniform(0, 0.05))):
            m.blob(0.10, 0.10, 0.09, rng.choice(["foliage_a", "foliage_b"]), rng, sub=0, rough=0.25)
        if rng.random() < 0.8:
            with m.push(T(x + rng.uniform(-0.04, 0.04), -0.24, ztop + 0.15 + rng.uniform(0, 0.05))):
                m.blob(0.045, 0.045, 0.04, rng.choice(["flower_a", "flower_b", "flower_c"]), rng, sub=0, rough=0.1)


def arch_infill(m, x0, x1, zs, z1, t, mat, seg=10, y0=0.0, y1=None):
    """Fills a rectangular opening top so the hole reads as a round arch.
    zs = springing height, z1 = top of the rectangular hole."""
    y1 = t if y1 is None else y1
    w = x1 - x0; rise = z1 - zs - 0.0
    def zc(x):
        u = (x - x0) / w * 2 - 1
        return zs + rise * math.sqrt(max(0.0, 1 - u * u))
    for i in range(seg):
        xa, xb = x0 + w * i / seg, x0 + w * (i + 1) / seg
        za, zb = zc(xa), zc(xb)
        if z1 - min(za, zb) < 1e-4:
            continue
        pts = [(xa, y0, za), (xb, y0, zb), (xb, y0, z1), (xa, y0, z1),
               (xa, y1, za), (xb, y1, zb), (xb, y1, z1), (xa, y1, z1)]
        m.add(pts, Mesh._BOX_F, mat)


def voussoirs(m, x0, x1, zs, z1, rng, n=9, mat="stone_light", depth=0.16, proud=0.03):
    """Ring of wedge stones around an arch (decoration, proud of the wall)."""
    w = x1 - x0; cx = (x0 + x1) / 2; rise = z1 - zs
    for i in range(n):
        a0, a1 = math.pi * i / n, math.pi * (i + 1) / n
        pts = []
        for y in (-proud, 0.04):
            for a, k in ((a0, 1.0), (a1, 1.0), (a1, 1.0 + depth * 2 / w), (a0, 1.0 + depth * 2 / w)):
                kk = k + (rng.uniform(-0.012, 0.012) if k > 1 else 0)
                pts.append((cx - math.cos(a) * w / 2 * kk, y, zs + math.sin(a) * rise * kk + (0.0 if k == 1 else 0.0)))
        m.add(pts, Mesh._BOX_F, mat)


def door_frame(m, x0, x1, z0, z1, t, rng, mat="wood_dark", step=True, arch=False):
    jw = 0.10
    m.box(x0, 0.02, z0, x0 + jw, t - 0.02, z1, mat, wob=0.006, rng=rng)
    m.box(x1 - jw, 0.02, z0, x1, t - 0.02, z1, mat, wob=0.006, rng=rng)
    m.box(x0, 0.02, z1 - jw, x1, t - 0.02, z1, mat)
    if arch:
        voussoirs(m, x0 - 0.02, x1 + 0.02, z1 - 0.1, z1 + (x1 - x0) * 0.22, rng, n=7)
    else:
        m.box(x0 - 0.2, -0.045, z1, x1 + 0.2, 0.09, z1 + 0.2, mat, wob=0.012, rng=rng)
    if step:
        m.box(x0 - 0.2, -0.55, z0 - 0.20, x1 + 0.2, 0.0, z0, "stone_light", wob=0.015, rng=rng)


def door_leaf(w, h, rng, name="Door", mat="trim", th=0.05):
    """Separate mesh; origin on the hinge axis at floor level, leaf extends +x,
    outer face at y=0.  Swings inward (+y) with a positive Z rotation."""
    m = Mesh(name)
    n = 5
    bw = w / n
    for i in range(n):
        m.box(i * bw + 0.004, 0, 0.01, (i + 1) * bw - 0.004, th, h, mat, wob=0.004, rng=rng)
    for z in (0.22 * h, 0.78 * h):
        m.box(0.03, th, z - 0.06, w - 0.03, th + 0.028, z + 0.06, mat)
        m.box(0.0, -0.012, z - 0.03, w * 0.62, 0.0, z + 0.03, "metal_dark")       # strap hinge
        m.cyl(0.022, 0.12, 6, "metal_dark", z0=z - 0.06)
    m.beam((0.06, th + 0.014, 0.22 * h + 0.06), (w - 0.06, th + 0.014, 0.78 * h - 0.06), 0.028, 0.10, mat, up=(0, 1, 0))
    for y in (-0.03, th + 0.03):
        with m.push(T(w - 0.13, y, h * 0.47), Rx(math.pi / 2)):
            m.cyl(0.045, 0.02, 8, "brass", z0=-0.01)
    return m


# ================================================================ roofs
def _tiles(m, Lu, Sv, rng, clip=None, tw=0.30, exp=0.34, mats=("tile_a", "tile_b", "tile_c")):
    """Rows of humped clay tiles in a slope frame (x=u along eave, y=v down slope, z=normal)."""
    tl = exp + 0.10
    th, hump = 0.022, 0.05
    rows = max(1, int(math.ceil((Sv - 0.05) / exp)))
    exp = (Sv - (tl - exp)) / rows
    for j in range(rows):
        v0 = j * exp
        off = (j % 2) * tw * 0.5 + rng.uniform(-0.02, 0.02)
        nt = int(math.ceil(Lu / tw)) + 1
        for i in range(-1, nt):
            u0, u1 = i * tw + off, i * tw + off + tw - 0.012
            lo, hi = (0.0, Lu) if clip is None else clip(v0 + tl * 0.55)
            u0, u1 = max(u0, lo), min(u1, hi)
            if u1 - u0 < 0.07:
                continue
            w = u1 - u0
            lift = th + 0.012 + rng.uniform(0, 0.012)
            base = 0.004 + rng.uniform(0, 0.006)
            poly = [(u0, base), (u1, base), (u1, base + th), (u0 + w * 0.75, base + th + hump),
                    (u0 + w * 0.25, base + th + hump), (u0, base + th)]
            mat = mats[0] if rng.random() < 0.6 else rng.choice(mats)
            m.prism(poly, v0, v0 + tl, mat, dz1=lift)


def _slab(m, poly_uv, n0, n1, mat):
    n = len(poly_uv)
    pts = [(u, v, n1) for u, v in poly_uv] + [(u, v, n0) for u, v in poly_uv]
    faces = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, i + n, j + n, j))
    m.add(pts, faces, mat)


def _tin(m, Lu, Sv, rng, clip=None, role="tin", sheet_w=0.86, sheet_l=1.7):
    """Overlapping corrugated sheets in a slope frame.  Per-sheet tint, the odd
    rusty or patched sheet, slight skew - never a clean grid."""
    period, amp, th = 0.172, 0.022, 0.008
    rows = max(1, int(math.ceil(Sv / (sheet_l - 0.15))))
    rl = Sv / rows + 0.15
    for j in range(rows - 1, -1, -1):                 # bottom row first, upper rows lap over
        v0 = j * (Sv / rows) - (0.0 if j == 0 else 0.0)
        base = 0.006 + (rows - 1 - j) * 0.0 + (0.012 if j < rows - 1 else 0.0)
        off = rng.uniform(-0.3, 0.0)
        u = off
        while u < Lu:
            w = sheet_w + rng.uniform(-0.04, 0.04)
            lo, hi = (0.0, Lu) if clip is None else clip(v0 + rl * 0.5)
            a, b = max(u, lo), min(u + w, hi)
            if b - a > 0.12:
                n = max(2, int(round((b - a) / (period / 2))))
                top = [(a + (b - a) * i / n, base + (amp if i % 2 else 0.0)) for i in range(n + 1)]
                poly = top[::-1] + [(x, z - th) for x, z in top]
                r = role if rng.random() < 0.86 else role + "_rust"
                lift = 0.035 if j < rows - 1 else 0.02
                m.prism(poly, v0, min(v0 + rl + rng.uniform(-0.03, 0.03), Sv + 0.03), r, dz1=-lift * 0 ,
                        tint=1.0 + rng.uniform(-0.09, 0.07))
            u += w - 0.06
    # a patch sheet and a couple of weights
    if Lu > 1.6 and clip is None:
        pu, pv = rng.uniform(0.2, Lu - 1.0), rng.uniform(0.2, max(0.25, Sv - 1.0))
        n = 8
        top = [(pu + 0.7 * i / n, 0.05 + (amp if i % 2 else 0.0)) for i in range(n + 1)]
        m.prism(top[::-1] + [(x, z - th) for x, z in top], pv, pv + 0.8, role + "_patch", tint=1.0 + rng.uniform(-0.05, 0.05))
        for _ in range(rng.randint(1, 2)):
            with m.push(T(rng.uniform(0.3, Lu - 0.3), rng.uniform(0.3, Sv - 0.2), 0.09)):
                m.blob(0.13, 0.11, 0.07, "stone", rng, sub=0, rough=0.2)


def slope(m, Lu, Sv, rng, poly=None, clip=None, rafters=True, tiles=True, deck_mat="wood_mid",
          tile_mats=("tile_a", "tile_b", "tile_c"), cover=None, tin_role="tin"):
    """One roof plane in the current (slope) frame."""
    poly = poly or [(0, 0), (Lu, 0), (Lu, Sv), (0, Sv)]
    cover = cover or ("tiles" if tiles else "plain")
    if cover == "tin":
        # purlins instead of a closed deck: the underside of the sheets is visible
        k = max(2, int(Sv / 0.7))
        for i in range(k + 1):
            v = 0.06 + (Sv - 0.12) * i / k
            lo, hi = (0.0, Lu) if clip is None else clip(v)
            m.box(lo, v - 0.035, -0.05, hi, v + 0.035, 0.0, "wood_mid")
    else:
        _slab(m, poly, -0.07, 0.0, deck_mat)
    if rafters:
        n = max(2, int(Lu / 0.62))
        for i in range(n + 1):
            u = 0.12 + (Lu - 0.24) * i / n
            lo, hi = (0.0, Lu) if clip is None else clip(Sv * 0.98)
            if not (lo + 0.05 < u < hi - 0.05):
                continue
            v_start = 0.0
            if clip is not None:
                # start the rafter where it enters the clipped region
                for k in range(21):
                    vv = Sv * k / 20
                    a, b = clip(vv)
                    if a <= u <= b:
                        v_start = vv; break
            m.box(u - 0.045, v_start, -0.19, u + 0.045, Sv + 0.04, -0.07, "wood_dark")
    if cover == "tin":
        _tin(m, Lu, Sv, rng, clip=clip, role=tin_role)
    elif cover == "tiles":
        _tiles(m, Lu, Sv, rng, clip=clip, mats=tile_mats)
    else:
        _slab(m, poly, 0.0, 0.03, tile_mats[0])


def ridge_caps(m, p0, p1, rng, r=0.13, mat="tile_ridge"):
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
    d = p1 - p0; L = float(np.linalg.norm(d)); x = d / L
    y = np.cross((0, 0, 1), x); y /= np.linalg.norm(y)
    n = max(1, int(L / 0.42)); seg = L / n
    with m.push(frame(p0, x, y)):
        for i in range(n):
            with m.push(T(i * seg - 0.02, 0, -0.035 + rng.uniform(0, 0.012)), Ry(-0.05)):
                m.half_tube(r + rng.uniform(-0.006, 0.006), seg + 0.06, mat if rng.random() < 0.8 else "tile_b")


def gable_roof(m, L, D, z0, pitch_deg, rng, eave=0.45, verge=0.32, sag=0.07, tiles=True,
               barge_mat="trim", tile_mats=("tile_a", "tile_b", "tile_c"), ridge_off=0.0, cover=None, tin_role="tin"):
    """Ridge along local X, centred.  ridge_off shifts the ridge in Y (saltbox).
    Returns ridge height."""
    start = len(m.v)
    p = math.radians(pitch_deg)
    half_f = D / 2 + ridge_off          # horizontal run of the front slope
    half_b = D / 2 - ridge_off
    rise = half_f * math.tan(p)
    zr = z0 + rise
    pb = math.atan2(rise, half_b)
    Lu = L + 2 * verge
    for sgn, half, pp in ((-1, half_f, p), (1, half_b, pb)):
        c, s = math.cos(pp), math.sin(pp)
        Sv = (half + eave) / c
        if sgn < 0:
            M = frame((L / 2 + verge, ridge_off, zr), (-1, 0, 0), (0, -c, -s))
        else:
            M = frame((-L / 2 - verge, ridge_off, zr), (1, 0, 0), (0, c, -s))
        with m.push(M):
            slope(m, Lu, Sv, rng, tiles=tiles, tile_mats=tile_mats, cover=cover, tin_role=tin_role)
        # bargeboards
        for xe in (-L / 2 - verge, L / 2 + verge):
            top = (xe, ridge_off, zr - 0.11)
            bot = (xe, ridge_off + sgn * (half + eave), zr - 0.11 - (half + eave) * math.tan(pp))
            m.beam(top, bot, 0.045, 0.22, barge_mat, up=(1, 0, 0))
    if cover == "tin":
        # folded ridge flashing
        for sg in (-1, 1):
            m.beam((-Lu / 2 - 0.02, ridge_off + sg * 0.11, zr + 0.035 - 0.11 * math.tan(p) * 0.9), (Lu / 2 + 0.02, ridge_off + sg * 0.11, zr + 0.035 - 0.11 * math.tan(p) * 0.9),
                   0.24, 0.012, tin_role + "_patch", up=(0, -sg * math.sin(p), math.cos(p)))
    else:
        ridge_caps(m, (-Lu / 2, ridge_off, zr + 0.03), (Lu / 2, ridge_off, zr + 0.03), rng)
    # ridge beam + purlin ends poking through the gables
    m.box(-Lu / 2 + 0.04, ridge_off - 0.07, zr - 0.30, Lu / 2 - 0.04, ridge_off + 0.07, zr - 0.10, "wood_dark")
    if sag:
        def f(P):
            k = 1 - np.clip(np.abs(P[:, 0] - 0) / (Lu / 2), 0, 1) ** 2
            w = np.clip((P[:, 2] - z0) / max(rise, 1e-3), 0, 1.2)
            P = P.copy(); P[:, 2] -= sag * k * w
            return P
        _deform_local(m, start, f)
    return zr


def _deform_local(m, start, fn):
    """Deform in the mesh's current local frame."""
    if start >= len(m.v):
        return
    M = m.M; Mi = np.linalg.inv(M)
    P = np.asarray(m.v[start:], float)
    Pl = P @ Mi[:3, :3].T + Mi[:3, 3]
    Pl = fn(Pl)
    Pw = Pl @ M[:3, :3].T + M[:3, 3]
    m.v[start:] = list(map(tuple, Pw))


def hip_roof(m, L, D, z0, pitch_deg, rng, eave=0.5, tiles=True, finial=True,
             tile_mats=("tile_a", "tile_b", "tile_c")):
    """Hipped (L>D) or pyramid (L==D) roof.  Returns apex height."""
    p = math.radians(pitch_deg); c, s = math.cos(p), math.sin(p)
    Lx, Ly = L + 2 * eave, D + 2 * eave
    run = min(Lx, Ly) / 2
    rise = run * math.tan(p); zr = z0 + rise
    z_eave = z0
    Sv = run / c
    ridge_x = max(0.0, (Lx - Ly) / 2); ridge_y = max(0.0, (Ly - Lx) / 2)
    # the four planes: (origin on the apex line, u, v, eave length, ridge length)
    planes = [
        ((Lx / 2, -ridge_y, zr), (-1, 0, 0), (0, -c, -s), Lx, 2 * ridge_x),
        ((-Lx / 2, ridge_y, zr), (1, 0, 0), (0, c, -s), Lx, 2 * ridge_x),
        ((ridge_x, Ly / 2, zr), (0, -1, 0), (c, 0, -s), Ly, 2 * ridge_y),
        ((-ridge_x, -Ly / 2, zr), (0, 1, 0), (-c, 0, -s), Ly, 2 * ridge_y),
    ]
    for org, u, v, Le, Lr in planes:
        a0 = (Le - Lr) / 2
        def clip(vv, a0=a0, Le=Le):
            k = min(max(vv / Sv, 0.0), 1.0)
            return a0 * (1 - k) + 0.03, Le - a0 * (1 - k) - 0.03
        poly = [(a0, 0), (Le - a0, 0), (Le, Sv), (0, Sv)]
        if Lr < 1e-6:
            poly = [(Le / 2, 0), (Le, Sv), (0, Sv)]
        with m.push(frame(org, u, v)):
            slope(m, Le, Sv, rng, poly=poly, clip=clip, tiles=tiles, tile_mats=tile_mats)
    corners = [(Lx / 2, Ly / 2), (-Lx / 2, Ly / 2), (-Lx / 2, -Ly / 2), (Lx / 2, -Ly / 2)]
    for cx, cy in corners:
        ax = math.copysign(ridge_x, cx) if ridge_x else 0.0
        ay = math.copysign(ridge_y, cy) if ridge_y else 0.0
        ridge_caps(m, (cx, cy, z_eave + 0.05), (ax, ay, zr + 0.05), rng, r=0.12)
    if ridge_x or ridge_y:
        ridge_caps(m, (-ridge_x, -ridge_y, zr + 0.04), (ridge_x, ridge_y, zr + 0.04), rng)
    if finial:
        with m.push(T(0, 0, zr)):
            m.lathe([(0.10, 0.0), (0.13, 0.10), (0.05, 0.22), (0.09, 0.36), (0.02, 0.62), (0.0, 0.64)], 8, "tile_ridge")
    return zr


def shed_roof(m, L, D, z_low, pitch_deg, rng, eave=0.4, verge=0.3, tiles=True, mats=("tile_a", "tile_b", "tile_c"),
              deck_mat="wood_mid", cover=None, tin_role="tin"):
    """Single slope: low edge at -Y (front), high at +Y.  Returns high-edge height."""
    p = math.radians(pitch_deg); c, s = math.cos(p), math.sin(p)
    rise = D * math.tan(p)
    Lu = L + 2 * verge
    Sv = (D + 2 * eave) / c
    org = (L / 2 + verge, D / 2 + eave, z_low + rise + eave * math.tan(p))
    with m.push(frame(org, (-1, 0, 0), (0, -c, -s))):
        slope(m, Lu, Sv, rng, tiles=tiles, tile_mats=mats, deck_mat=deck_mat, cover=cover, tin_role=tin_role)
    return z_low + rise


def chimney(m, x, y, z0, h, rng, w=0.62, d=0.5, mat="plaster_accent", pots=2):
    with m.push(T(x, y, z0)):
        m.box(-w / 2, -d / 2, 0, w / 2, d / 2, h, mat, wob=0.015, rng=rng, taper=0.06)
        m.box(-w / 2 - 0.05, -d / 2 - 0.05, h - 0.02, w / 2 + 0.05, d / 2 + 0.05, h + 0.09, "stone_light", wob=0.01, rng=rng)
        for i in range(pots):
            px = (i - (pots - 1) / 2) * 0.26
            with m.push(T(px, 0, h + 0.09)):
                m.lathe([(0.085, 0), (0.095, 0.05), (0.07, 0.24), (0.085, 0.30), (0.05, 0.30)], 8, "tile_ridge")


# ================================================================ timber, stone
def timber(m, W, z0, z1, rng, studs=2, braces=True, sill=True, mat="wood_dark", b=0.14, proud=0.035):
    """Half-timbering on a facade (wall-local)."""
    ya, yb = -proud, 0.03
    if sill:
        m.box(-0.02, ya, z0, W + 0.02, yb, z0 + b, mat, wob=0.008, rng=rng)
    m.box(-0.02, ya, z1 - b, W + 0.02, yb, z1, mat, wob=0.008, rng=rng)
    xs = [b / 2] + [W * (i + 1) / (studs + 1) for i in range(studs)] + [W - b / 2]
    for x in xs:
        m.box(x - b / 2, ya, z0, x + b / 2, yb, z1, mat, wob=0.008, rng=rng)
    if braces:
        dz = (z1 - z0) - 2 * b
        for x, sg in ((xs[0], 1), (xs[-1], -1)):
            m.beam((x + sg * b * 0.5, (ya + yb) / 2, z0 + b * 0.9), (x + sg * min(dz * 0.6, W * 0.22), (ya + yb) / 2, z1 - b * 0.9),
                   yb - ya, b * 0.85, mat, up=(0, 1, 0))


def stone_course(m, W, h, rng, proud=0.10, rows=2, mat=("stone", "stone", "stone_b"), z0=0.0, depth=0.30):
    """Irregular stone blocks along a facade base (wall-local)."""
    rh = h / rows
    for r in range(rows):
        x = -proud if r % 2 == 0 else -proud - 0.15
        while x < W + proud:
            L = rng.uniform(0.32, 0.78)
            x1 = min(x + L, W + proud)
            pr = proud + rng.uniform(-0.03, 0.03)
            m.box(max(x, -proud) + 0.008, -pr, z0 + r * rh + 0.006, x1 - 0.008, depth, z0 + (r + 1) * rh - 0.004,
                  rng.choice(mat), wob=0.018, rng=rng)
            x = x1


def quoins(m, H, rng, z0=0.0, mat="stone_light", n=None):
    """Corner stones at wall-local x=0 (use on both ends via transforms)."""
    n = n or int(H / 0.36)
    hh = H / n
    for i in range(n):
        L = 0.42 if i % 2 == 0 else 0.26
        m.box(-0.035, -0.035, z0 + i * hh + 0.01, L, 0.05, z0 + (i + 1) * hh - 0.01, mat, wob=0.01, rng=rng)


# ================================================================ balconies, stairs, floors
def balcony(m, x0, x1, z, depth, rng, rail_h=0.95, style="baluster", mat="trim", deck_mat="wood_mid",
            brackets=True, posts_to=None, wood="wood_dark"):
    """Timber balcony projecting toward -y (wall-local).  posts_to: if set,
    corner posts continue up to that height (to carry a roof)."""
    W = x1 - x0
    nj = max(2, int(W / 0.75))
    for i in range(nj + 1):
        x = x0 + 0.06 + (W - 0.12) * i / nj
        m.box(x - 0.05, -depth + 0.02, z - 0.19, x + 0.05, 0.12, z - 0.045, wood, wob=0.006, rng=rng)
        if brackets and (i in (0, nj) or i % 2 == 0):
            m.beam((x, 0.0, z - 0.85), (x, -depth * 0.78, z - 0.17), 0.08, 0.09, wood, up=(1, 0, 0))
    m.box(x0, -depth - 0.03, z - 0.21, x1, -depth + 0.07, z - 0.045, wood)           # fascia beam
    np_ = max(3, int(depth / 0.19))
    pw = depth / np_
    for i in range(np_):
        m.box(x0 - 0.03, -depth + i * pw + 0.006, z - 0.045, x1 + 0.03, -depth + (i + 1) * pw - 0.006, z,
              deck_mat, wob=0.004, rng=rng)
    # posts
    npost = max(2, int(round(W / 1.7)) + 1)
    px = [x0 + 0.05 + (W - 0.10) * i / (npost - 1) for i in range(npost)]
    top = posts_to if posts_to else z + rail_h
    for x in px:
        m.box(x - 0.045, -depth + 0.01, z, x + 0.045, -depth + 0.10, top if x in (px[0], px[-1]) or posts_to else z + rail_h, mat)
    for x in (px[0], px[-1]):
        m.box(x - 0.045, -0.10, z, x + 0.045, -0.01, z + rail_h, mat)
    yf = -depth + 0.055
    # rails: front + both returns
    runs = [((x0, yf), (x1, yf)), ((x0 + 0.05, yf), (x0 + 0.05, -0.02)), ((x1 - 0.05, yf), (x1 - 0.05, -0.02))]
    for (ax, ay), (bx, by) in runs:
        m.beam((ax, ay, z + rail_h), (bx, by, z + rail_h), 0.085, 0.055, mat)
        m.beam((ax, ay, z + 0.11), (bx, by, z + 0.11), 0.05, 0.05, mat)
        L = math.hypot(bx - ax, by - ay)
        if style == "baluster":
            n = max(2, int(L / 0.135))
            for i in range(1, n):
                k = i / n
                x, y = ax + (bx - ax) * k, ay + (by - ay) * k
                m.box(x - 0.016, y - 0.016, z + 0.13, x + 0.016, y + 0.016, z + rail_h - 0.02, mat)
        elif style == "slat":
            n = max(2, int(L / 0.17))
            for i in range(n):
                k = (i + 0.5) / n
                x, y = ax + (bx - ax) * k, ay + (by - ay) * k
                dx, dy = (bx - ax) / L, (by - ay) / L
                m.beam((x - dx * 0.055, y - dy * 0.055, z + (rail_h + 0.11) / 2), (x + dx * 0.055, y + dy * 0.055, z + (rail_h + 0.11) / 2),
                       0.018, rail_h - 0.16, mat)
        elif style == "cross":
            n = max(1, int(round(L / 0.9)))
            for i in range(n):
                a, b = i / n, (i + 1) / n
                p0 = (ax + (bx - ax) * a, ay + (by - ay) * a); p1 = (ax + (bx - ax) * b, ay + (by - ay) * b)
                m.beam((*p0, z + 0.13), (*p1, z + rail_h - 0.03), 0.03, 0.04, mat)
                m.beam((*p0, z + rail_h - 0.03), (*p1, z + 0.13), 0.03, 0.04, mat)


def stair_flight(m, run, rise, width, rng, mat="wood_mid", solid=False, n=None, stringer="wood_dark",
                 rail=None, rail_mat="trim", tread_mat=None):
    """Flight starting at local origin, climbing +x; width spans y 0..width."""
    n = n or max(2, int(round(rise / 0.19)))
    tr, rs = run / n, rise / n
    tread_mat = tread_mat or mat
    for i in range(n):
        ztop = (i + 1) * rs
        if solid:
            m.box(i * tr, 0, 0, (i + 1) * tr + (0.0 if i < n - 1 else 0), width, ztop - 0.04, mat, wob=0.006, rng=rng)
            m.box(i * tr - 0.03, -0.02, ztop - 0.045, (i + 1) * tr, width + 0.02, ztop, tread_mat, wob=0.006, rng=rng)
        else:
            m.box(i * tr - 0.02, 0.03, ztop - 0.045, (i + 1) * tr + 0.03, width - 0.03, ztop, tread_mat, wob=0.004, rng=rng)
    if not solid:
        for y in (0.0, width):
            m.beam((-0.05, y, -0.10 + rs * 0.2), (run + 0.02, y, rise - 0.10 + rs * 0.2), 0.05, 0.22, stringer)
    if rail:
        for y in ((0.02, width - 0.02) if rail == "both" else ((0.02,) if rail == "left" else (width - 0.02,))):
            m.beam((0, y, rs + 0.9), (run, y, rise + 0.9), 0.05, 0.055, rail_mat)
            k = max(2, int(run / 0.5))
            for i in range(k + 1):
                x = run * i / k
                zb = rise * i / k + (rs if i < k else 0) * 0
                m.box(x - 0.025, y - 0.025, zb, x + 0.025, y + 0.025, zb + rs + 0.9, rail_mat)


def floor_planks(m, x0, x1, y0, y1, z, rng, mat="wood_light", th=0.05, pw=0.22, hole=None, joists=True,
                 joist_mat="wood_dark"):
    """Plank floor (planks run along X).  hole = (hx0, hx1, hy0, hy1) stairwell."""
    n = max(1, int(round((y1 - y0) / pw)))
    w = (y1 - y0) / n
    for i in range(n):
        a, b = y0 + i * w, y0 + (i + 1) * w
        segs = [(x0, x1)]
        if hole and b > hole[2] + 1e-6 and a < hole[3] - 1e-6:
            segs = [(x0, hole[0]), (hole[1], x1)]
        for sa, sb in segs:
            if sb - sa > 0.02:
                m.box(sa, a + 0.004, z - th, sb, b - 0.004, z, mat if rng.random() < 0.75 else "wood_mid", wob=0.003, rng=rng)
    if joists:
        k = max(2, int((x1 - x0) / 0.8))
        for i in range(k + 1):
            x = x0 + 0.08 + (x1 - x0 - 0.16) * i / k
            if hole and hole[0] - 0.05 < x < hole[1] + 0.05:
                m.box(x - 0.06, y0, z - th - 0.16, x + 0.06, hole[2], z - th, joist_mat)
                m.box(x - 0.06, hole[3], z - th - 0.16, x + 0.06, y1, z - th, joist_mat)
            else:
                m.box(x - 0.06, y0, z - th - 0.16, x + 0.06, y1, z - th, joist_mat)


def pergola(m, x0, x1, y0, y1, z, h, rng, mat="wood_dark", vines=True):
    for x in (x0 + 0.08, x1 - 0.08):
        for y in (y0 + 0.08, y1 - 0.08):
            m.box(x - 0.06, y - 0.06, z, x + 0.06, y + 0.06, z + h, mat, wob=0.008, rng=rng)
    for y in (y0 + 0.08, y1 - 0.08):
        m.box(x0 - 0.25, y - 0.05, z + h, x1 + 0.25, y + 0.05, z + h + 0.14, mat)
    n = max(3, int((x1 - x0) / 0.4))
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n
        m.box(x - 0.03, y0 - 0.3, z + h + 0.14, x + 0.03, y1 + 0.3, z + h + 0.22, mat, wob=0.006, rng=rng)
    if vines:
        for _ in range(int((x1 - x0) * (y1 - y0) * 1.6)):
            with m.push(T(rng.uniform(x0, x1), rng.uniform(y0 - 0.2, y1 + 0.2), z + h + 0.2 + rng.uniform(-0.12, 0.1))):
                m.blob(rng.uniform(0.2, 0.42), rng.uniform(0.2, 0.42), 0.14, rng.choice(["foliage_a", "foliage_b", "foliage_b"]), rng, sub=0, rough=0.3)
        for _ in range(5):
            with m.push(T(rng.uniform(x0, x1), rng.uniform(y0, y1), z + h + 0.02)):
                m.blob(0.09, 0.09, 0.14, "flower_c", rng, sub=0, rough=0.15)


def awning(m, x0, x1, z, depth, rng, drop=0.55, mats=("fabric_awning", "fabric_white")):
    """Striped cloth awning with poles (wall-local, projecting -y)."""
    n = max(4, int((x1 - x0) / 0.32))
    w = (x1 - x0) / n
    for i in range(n):
        a, b = x0 + i * w, x0 + (i + 1) * w
        mat = mats[i % 2]
        pts = [(a, 0.0, z), (b, 0.0, z), (b, -depth, z - drop), (a, -depth, z - drop),
               (a, 0.0, z + 0.02), (b, 0.0, z + 0.02), (b, -depth, z - drop + 0.02), (a, -depth, z - drop + 0.02)]
        m.add(pts, Mesh._BOX_F, mat)
        pts = [(a, -depth, z - drop - 0.16 - (0.05 if i % 2 else 0)), (b, -depth, z - drop - 0.16 - (0.05 if i % 2 else 0)),
               (b, -depth, z - drop + 0.02), (a, -depth, z - drop + 0.02),
               (a, -depth - 0.012, z - drop - 0.16), (b, -depth - 0.012, z - drop - 0.16),
               (b, -depth - 0.012, z - drop + 0.02), (a, -depth - 0.012, z - drop + 0.02)]
        m.add(pts, Mesh._BOX_F, mat)
    for x in (x0 + 0.04, x1 - 0.04):
        m.beam((x, -depth + 0.03, z - drop), (x, -0.02, z - drop - 0.75), 0.035, 0.035, "wood_dark")


# ================================================================ plank cladding
def _free(a0, a1, cuts):
    """Sub-intervals of [a0, a1] not covered by cuts [(c0, c1)]."""
    out, a = [], a0
    for c0, c1 in sorted(cuts):
        if c1 <= a or c0 >= a1:
            continue
        if c0 > a:
            out.append((a, c0))
        a = max(a, c1)
    if a < a1:
        out.append((a, a1))
    return [(p, q) for p, q in out if q - p > 0.03]


def clad(m, W, z0, z1, openings, rng, style="lap", role="wall", th=0.028, x0=0.0, vary=0.075):
    """Painted boards on the outside of a wall (wall-local), cut round openings.
    lap = horizontal weatherboards, vertical = board-and-batten."""
    if style == "lap":
        n = max(1, int(round((z1 - z0) / 0.21)))
        bh = (z1 - z0) / n
        for i in range(n):
            a, b = z0 + i * bh, z0 + (i + 1) * bh
            cuts = [(o[0], o[1]) for o in openings if o[3] > a + 0.01 and o[2] < b - 0.01]
            for p, q in _free(x0, W, cuts):
                # break long runs into boards
                x = p
                while x < q - 1e-6:
                    L = min(q - x, rng.uniform(1.6, 3.2))
                    if q - (x + L) < 0.35:
                        L = q - x
                    lean = rng.uniform(-0.006, 0.006)
                    pts = [(x + 0.004, -th - 0.012, a + lean), (x + L - 0.004, -th - 0.012, a - lean),
                           (x + L - 0.004, 0.0, a), (x + 0.004, 0.0, a),
                           (x + 0.004, -th * 0.45, b + 0.02 + lean), (x + L - 0.004, -th * 0.45, b + 0.02 - lean),
                           (x + L - 0.004, 0.0, b + 0.02), (x + 0.004, 0.0, b + 0.02)]
                    m.add(pts, Mesh._BOX_F, role, 1.0 + rng.uniform(-vary, vary))
                    x += L
    else:
        x = x0
        while x < W - 1e-6:
            bw = min(rng.uniform(0.20, 0.34), W - x)
            if W - (x + bw) < 0.1:
                bw = W - x
            cuts = [(o[2], o[3]) for o in openings if o[1] > x + 0.01 and o[0] < x + bw - 0.01]
            for p, q in _free(z0, z1, cuts):
                lean = rng.uniform(-0.008, 0.008)
                pts = [(x + 0.005, -th, p), (x + bw - 0.005, -th, p), (x + bw - 0.005, 0, p), (x + 0.005, 0, p),
                       (x + 0.005 + lean, -th, q), (x + bw - 0.005 + lean, -th, q), (x + bw - 0.005 + lean, 0, q), (x + 0.005 + lean, 0, q)]
                m.add(pts, Mesh._BOX_F, role, 1.0 + rng.uniform(-vary, vary))
                if rng.random() < 0.9:      # batten over the joint
                    m.box(x + bw - 0.03, -th - 0.014, p, x + bw + 0.03, -th, q, role, rng=rng, vary=vary)
            x += bw


def clad_gable(m, W, z0, rise, rng, role="wall", th=0.028, apex=0.5, vary=0.075, style="lap"):
    """Boards filling a gable triangle (wall-local)."""
    n = max(1, int(round(rise / 0.21)))
    bh = rise / n
    for i in range(n):
        a, b = i * bh, (i + 1) * bh
        xa0, xa1 = W * apex * a / rise, W - W * (1 - apex) * a / rise
        xb0, xb1 = W * apex * b / rise, W - W * (1 - apex) * b / rise
        if xa1 - xa0 < 0.05:
            continue
        pts = [(xa0, -th - 0.012, z0 + a), (xa1, -th - 0.012, z0 + a), (xa1, 0, z0 + a), (xa0, 0, z0 + a),
               (xb0, -th * 0.45, z0 + b + 0.01), (xb1, -th * 0.45, z0 + b + 0.01), (xb1, 0, z0 + b + 0.01), (xb0, 0, z0 + b + 0.01)]
        m.add(pts, Mesh._BOX_F, role, 1.0 + rng.uniform(-vary, vary))


def stovepipe(m, x, y, z0, h, rng, r=0.085):
    """Tin flue with a rain cap."""
    with m.push(T(x, y, z0)):
        m.cyl(r, h, 8, "tin_bare")
        m.cyl(r + 0.03, 0.05, 8, "tin_bare", z0=h * 0.45)
        m.lathe([(r + 0.02, h + 0.06), (r + 0.11, h + 0.07), (0.01, h + 0.2)], 8, "tin_bare_rust")


def footings(m, W, D, h, rng, cx=0.0, cy=0.0, role="stone", step=1.3):
    """Stone pads under a timber sill beam: the building sits ON the ground,
    it does not grow out of it."""
    nx, ny = max(2, int(W / step) + 1), max(2, int(D / step) + 1)
    for i in range(nx):
        for j in range(ny):
            if 0 < i < nx - 1 and 0 < j < ny - 1:
                continue
            x = cx - W / 2 + W * i / (nx - 1); y = cy - D / 2 + D * j / (ny - 1)
            m.cbox(x, y, h / 2 - 0.25, 0.42 + rng.uniform(-0.05, 0.08), 0.40 + rng.uniform(-0.05, 0.08), h + 0.5,
                   role, rz=rng.uniform(-0.3, 0.3), wob=0.03, rng=rng, vary=0.08)
    for y in (cy - D / 2, cy + D / 2):
        m.box(cx - W / 2 - 0.05, y - 0.08, h - 0.02, cx + W / 2 + 0.05, y + 0.08, h + 0.12, "wood_dark")
    for x in (cx - W / 2, cx + W / 2):
        m.box(x - 0.08, cy - D / 2 - 0.05, h - 0.02, x + 0.08, cy + D / 2 + 0.05, h + 0.12, "wood_dark")
