"""Environmental storytelling for buildings and the village (pure geometry).

Every item is tied to a use (ART_BIBLE §2: "every prop tied to a simulated
use") and placed by rule, not scattered: gutters feed barrels, laundry hangs
where there is sun and room, nets and pots belong to fishing households,
crates to traders, gardens to plots with space.
"""
from __future__ import annotations
import math
from .geom import Mesh, T, Rz, Rx, Ry
from . import furniture as F
from .world import FLOOR_Z, STOREY, side_clearance


def gutter_and_barrel(m, vol, side, rng, H, at_left=True):
    """Eaves gutter along a wall, downpipe at one end, rain barrel under it (wall-local)."""
    W = vol.width(side)
    z = H - 0.02
    m.box(-0.25, -0.50, z - 0.07, W + 0.25, -0.38, z - 0.05, "tin_bare")
    m.box(-0.25, -0.52, z - 0.07, W + 0.25, -0.50, z + 0.02, "tin_bare")
    m.box(-0.25, -0.38, z - 0.07, W + 0.25, -0.36, z + 0.02, "tin_bare")
    x = -0.16 if at_left else W + 0.16
    m.beam((x, -0.44, z - 0.06), (x, -0.12, z - 0.5), 0.05, 0.05, "tin_bare")
    m.box(x - 0.03, -0.15, 0.75, x + 0.03, -0.09, z - 0.48, "tin_bare")
    with m.push(T(x, -0.34, -FLOOR_Z)):
        m.lathe([(0.24, 0), (0.30, 0.3), (0.30, 0.55), (0.25, 0.85), (0.22, 0.85), (0.22, 0.8), (0.0, 0.8)], 10, "wood_mid")
        for zz in (0.18, 0.66):
            m.lathe([(0.305, zz), (0.31, zz), (0.31, zz + 0.04), (0.305, zz + 0.04)], 10, "iron")
        m.cyl(0.215, 0.02, 10, "water_still", z0=0.74)


def lantern(m, x, z, rng):
    """Wall lantern on a bracket beside the door (wall-local)."""
    m.box(x - 0.015, -0.22, z, x + 0.015, 0.0, z + 0.03, "iron")
    with m.push(T(x, -0.2, z)):
        F.lamp_hanging(m, rng, drop=0.06)


def laundry(m, p0, p1, rng, sag=0.18):
    """Clothes line between two points (building-local) with washing pegged on it."""
    n = 14
    pts = []
    for i in range(n + 1):
        k = i / n
        pts.append((p0[0] + (p1[0] - p0[0]) * k, p0[1] + (p1[1] - p0[1]) * k, p0[2] + (p1[2] - p0[2]) * k - sag * math.sin(math.pi * k)))
    for a, b in zip(pts, pts[1:]):
        m.beam(a, b, 0.012, 0.012, "rope")
    L = math.dist(p0[:2], p1[:2])
    dx, dy = (p1[0] - p0[0]) / L, (p1[1] - p0[1]) / L
    k = 0.12
    while k < 0.9:
        w = rng.uniform(0.28, 0.5); hgt = rng.uniform(0.35, 0.7)
        i = int(k * n); a = pts[i]
        role = rng.choice(["fabric_white", "fabric_white", "fabric_a", "fabric_b", "wall", "flower_b"])
        lean = rng.uniform(-0.06, 0.06)
        pts4 = [(a[0], a[1], a[2] - 0.01), (a[0] + dx * w, a[1] + dy * w, a[2] - 0.01 - sag * 0.1),
                (a[0] + dx * w + lean * dy, a[1] + dy * w - lean * dx, a[2] - hgt), (a[0] + lean * dy, a[1] - lean * dx, a[2] - hgt)]
        m.add(pts4, [(0, 1, 2, 3), (3, 2, 1, 0)], role, 1.0 + rng.uniform(-0.06, 0.06))
        k += w / L + rng.uniform(0.03, 0.09)


def patch_planks(m, W, H, openings, rng, n=3):
    """Odd boards nailed over the cladding (wall-local): repairs you can read."""
    for _ in range(n):
        for _try in range(6):
            x, z = rng.uniform(0.3, W - 1.0), rng.uniform(0.35, H - 0.5)
            L, wd = rng.uniform(0.55, 1.1), rng.uniform(0.12, 0.2)
            if any(o[0] - 0.15 < x + L and x < o[1] + 0.15 and o[2] - 0.15 < z + wd + 0.2 and z - 0.2 < o[3] + 0.15 for o in openings):
                continue
            a = rng.uniform(-0.12, 0.12)
            m.beam((x, -0.05, z), (x + L * math.cos(a), -0.05, z + L * math.sin(a)), 0.02, wd,
                   rng.choice(["wood_light", "wood_mid", "wood_grey"]), up=(0, 1, 0))
            break


def crab_pots(m, rng, n=3):
    for i in range(n):
        with m.push(T(i * 0.42 + rng.uniform(-0.04, 0.04), rng.uniform(-0.05, 0.05), (0.0 if i < 2 else 0.3) - 0.0), Rz(rng.uniform(-0.3, 0.3))):
            if i == 2:
                m.M[0, 3] -= 0.63
            for x in (-0.18, 0.18):
                for y in (-0.14, 0.14):
                    m.box(x - 0.012, y - 0.012, 0, x + 0.012, y + 0.012, 0.28, "wood_mid")
            for z in (0.0, 0.27):
                m.box(-0.19, -0.15, z, 0.19, 0.15, z + 0.015, "wood_mid")
            m.box(-0.17, -0.13, 0.02, 0.17, 0.13, 0.26, "net")
    with m.push(T(n * 0.42 - 0.3, 0.25, 0.1)):
        m.blob(0.1, 0.1, 0.13, "float_a", rng, sub=0, rough=0.05)
    with m.push(T(n * 0.42 - 0.05, 0.2, 0.1)):
        m.blob(0.09, 0.09, 0.12, "float_b", rng, sub=0, rough=0.05)


def garden(m, w, d, rng):
    """Fenced kitchen plot, origin at one corner, extends +x, +y."""
    m.box(0.08, 0.08, 0.0, w - 0.08, d - 0.08, 0.07, "soil")
    for x0, y0, x1, y1 in ((0, 0, w, 0), (w, 0, w, d), (w, d, 0, d)):
        L = math.hypot(x1 - x0, y1 - y0); n = max(2, int(L / 0.28))
        for i in range(n + 1):
            k = i / n
            h = 0.5 + rng.uniform(-0.05, 0.08)
            m.cbox(x0 + (x1 - x0) * k, y0 + (y1 - y0) * k, h / 2, 0.07, 0.025, h, "frame" if rng.random() < 0.8 else "wood_light",
                   rz=math.atan2(y1 - y0, x1 - x0) + rng.uniform(-0.06, 0.06), rng=rng, vary=0.06)
        m.beam((x0, y0, 0.34), (x1, y1, 0.34), 0.03, 0.04, "wood_mid")
    rows = max(2, int(d / 0.42))
    for r in range(rows):
        y = 0.25 + (d - 0.5) * r / max(1, rows - 1)
        kind = rng.choice(["foliage_c", "foliage_a", "flower_b", "flower_a"])
        for i in range(int(w / 0.3)):
            with m.push(T(0.25 + i * 0.3 + rng.uniform(-0.04, 0.04), y, 0.12)):
                if kind.startswith("flower"):
                    m.blob(0.08, 0.08, 0.1, "foliage_a", rng, sub=0, rough=0.3)
                    with m.push(T(0, 0, 0.1)):
                        m.blob(0.05, 0.05, 0.05, kind, rng, sub=0, rough=0.1)
                else:
                    m.blob(0.11, 0.11, 0.13, kind, rng, sub=0, rough=0.35)


def vine(m, W, H, rng, x0=0.0):
    """Creeper climbing a wall corner (wall-local)."""
    x, z = x0 + 0.2, 0.0
    while z < H - 0.2:
        with m.push(T(x, -0.07, z)):
            m.blob(rng.uniform(0.14, 0.26), 0.06, rng.uniform(0.14, 0.24), rng.choice(["foliage_a", "foliage_b", "foliage_c"]), rng, sub=0, rough=0.35)
        if rng.random() < 0.25:
            with m.push(T(x + rng.uniform(-0.1, 0.1), -0.13, z + 0.05)):
                m.blob(0.05, 0.04, 0.05, "flower_c", rng, sub=0, rough=0.1)
        z += rng.uniform(0.14, 0.26)
        x = min(max(x + rng.uniform(-0.16, 0.2), x0 + 0.05), min(W - 0.1, x0 + 1.5 + z * 0.4))


def roof_load(m, rng):
    """Something left on the roof: a wash basin, a spare sheet under a block, a coil of rope."""
    k = rng.random()
    if k < 0.4:
        m.lathe([(0.2, 0.0), (0.3, 0.14), (0.29, 0.15), (0.19, 0.02)], 9, "tin_bare")
    elif k < 0.75:
        m.cbox(0, 0, 0.012, 0.9, 0.6, 0.02, "tin_patch", rz=rng.uniform(-0.4, 0.4))
        m.cbox(0.1, 0.05, 0.08, 0.26, 0.18, 0.13, "stone", rz=rng.uniform(0, 1), wob=0.02, rng=rng)
    else:
        m.lathe([(0.26, 0), (0.26, 0.09), (0.14, 0.09), (0.14, 0.0)], 10, "rope")


def dress(out, b, L, vol, wm, roof, rng, fam, H, flank, open_front, ridge_x, zr):
    """Adds the storytelling layer to one building. Returns a list of what was added."""
    W, D = vol.W, vol.D
    added = []
    fm = wm["front"]
    # 1. rainwater: gutter + barrel on an eaves wall
    eave_sides = ("front", "back") if ridge_x else ("left", "right")
    s = eave_sides[0] if not open_front else eave_sides[1]
    if not (fam == "family_house" and s == "front") and b["level"] != "DECK":
        with wm[s].push(vol.side(s)):
            gutter_and_barrel(wm[s], vol, s, rng, H, at_left=rng.random() < 0.5)
        added.append("gutter + rain barrel")
    # 2. light by the door
    if not open_front:
        with fm.push(vol.side("front")):
            lantern(fm, W / 2 + 0.75, 1.75, rng)
        out.meta["door_lantern"] = (0.75, -0.2, FLOOR_Z + 1.6)
        added.append("door lantern")
    # 3. repairs
    for s2 in ("front", "right", "left"):
        if s2 in vol.skip or rng.random() < 0.35:
            continue
        with wm[s2].push(vol.side(s2)):
            patch_planks(wm[s2], vol.width(s2), H, vol.openings[s2], rng, n=rng.randint(1, 3))
    added.append("patch planks")
    # 4. washing: across the balcony, or on a line to a post where the plot has room
    if b["kind"] in ("home", "stilt_home", "store"):
        if fam == "family_house":
            laundry(fm, (-W / 2 + 0.25, -0.8, FLOOR_Z + STOREY + 1.85), (W / 2 - 0.25, -0.8, FLOOR_Z + STOREY + 1.85), rng)
            added.append("laundry on the balcony")
        else:
            for s2 in ("left", "right"):
                if side_clearance(L, b, s2, 1.9) > 0:
                    sx = -1 if s2 == "left" else 1
                    px, py = sx * (W / 2 + 1.75), D * 0.62
                    m = wm[s2]
                    m.box(px - 0.04, py - 0.04, -0.2, px + 0.04, py + 0.04, 2.05, "wood_mid", wob=0.01, rng=rng)
                    laundry(m, (sx * (W / 2 + 0.05), D * 0.3, FLOOR_Z + 1.95), (px, py, 1.98), rng)
                    added.append("laundry line (%s)" % s2)
                    break
    # 5. trade and craft at the door
    if b["kind"] in ("stilt_home",) or (b["kind"] == "home" and b["level"] == "T1"):
        with fm.push(T(-W / 2 + 0.35, -0.42, FLOOR_Z if b["level"] == "DECK" else 0.0)):
            crab_pots(fm, rng)
        added.append("crab pots + floats")
    if b["kind"] in ("store", "warehouse", "market", "eatery", "netloft"):
        with fm.push(T(W / 2 - 0.9, -0.5, 0.0), Rz(math.pi)):
            F.loading_point(fm, rng)
        added.append("crates")
    # 6. gardens and creepers where there is ground
    if b["level"] != "DECK" and fam in ("cottage", "family_house") and side_clearance(L, b, "back", 1.6) > 0 and rng.random() < 0.9:
        gw = min(W - 0.8, 3.0)
        with wm["back"].push(T(-gw / 2, D + 0.12, 0.0)):
            garden(wm["back"], gw, 1.3, rng)
        added.append("kitchen garden")
    if rng.random() < 0.55 and b["level"] != "DECK":
        s2 = rng.choice(["right", "left"])
        if s2 not in vol.skip:
            with wm[s2].push(vol.side(s2)):
                vine(wm[s2], vol.width(s2), H * rng.uniform(0.6, 1.0), rng, x0=0.0 if rng.random() < 0.5 else vol.width(s2) - 1.2)
            added.append("creeper")
    # 7. something on the roof
    if rng.random() < 0.7:
        pitch_z = zr - (FLOOR_Z + H)
        with roof.push(T(rng.uniform(-W * 0.25, W * 0.25), D * 0.5 + (0.0 if not ridge_x else rng.choice([-1, 1]) * D * 0.22), FLOOR_Z + H + pitch_z * (0.52 if ridge_x else 0.98) + 0.06)):
            if ridge_x:
                roof_load(roof, rng)
        added.append("roof load")
    return added
