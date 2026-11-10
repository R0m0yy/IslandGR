"""Parametric building generator.

Input : one building record from data/village_layout.json (+ the layout).
Output: Built - named mesh groups, interaction anchors and an interior walk
        graph, all in the building-local frame.

Local frame (Blender): origin at the front-door threshold on the terrace
surface; +x to the right as seen in plan with the front at the bottom,
+y into the building, +z up.  The front faces -y.

Mesh groups follow BUILDING_CONTRACT.md so that any side can fade:
    WALL_S / WALL_E / WALL_N / WALL_W   exterior walls + everything fixed to them
    ROOF                                roof, tie beams, flue above the eaves
    BASE                                footings, ground floor, steps, porch deck
    INTERIOR                            ground-floor furniture, stair
    FLOOR2                              upper floor + its furniture (2 storeys)
    DOOR_main                           door leaf, pivot on the hinge
"""
from __future__ import annotations
import math
from . import parts, furniture as F
from .geom import Mesh, T, Rz, rng_for
from .parts import Vol
from .world import STOREY, T_WALL, FLOOR_Z, DOOR_W, DOOR_H, compass, side_clearance, to_godot

FAMILY = {  # layout kind -> architectural family
    "home": "cottage", "stilt_home": "stilt", "store": "stacked", "netloft": "stacked",
    "eatery": "stacked", "carpenter": "long_shed", "clinic": "cottage", "market": "long_shed",
    "boatyard": "long_shed", "warehouse": "long_shed", "hall": "civic", "school": "civic",
}


def family_of(b):
    f = FAMILY[b["kind"]]
    if b["kind"] == "home" and b["storeys"] == 2:
        f = "family_house"
    return f


class Built:
    def __init__(self, b):
        self.b = b
        self.meshes = {}
        self.anchors = []
        self.nodes = {}      # interior walk nodes: name -> blender-local xyz
        self.edges = []      # (a, b, type)
        self.unplaced = []
        self.meta = {}

    def g(self, name):
        if name not in self.meshes:
            self.meshes[name] = Mesh(name)
        return self.meshes[name]

    def node(self, name, x, y, z):
        self.nodes[name] = (round(x, 3), round(y, 3), round(z, 3)); return name

    def edge(self, a, b, t="interior"):
        self.edges.append((a, b, t))

    @property
    def tri_count(self):
        return sum(m.tri_count for m in self.meshes.values())


# ------------------------------------------------------------------ helpers
def _inner(vol, side):
    """Frame on the inside face of a wall: x along the wall, +y into the room."""
    return vol.side(side) @ T(0, vol.t, 0)


def _wall_len(vol, side):
    return vol.width(side)


def _loc(M, x, y, z=0.0):
    import numpy as np
    p = M[:3, :3] @ np.array([x, y, z]) + M[:3, 3]
    return float(p[0]), float(p[1]), float(p[2])


def _dir(M, dx, dy):
    import numpy as np
    d = M[:3, :3] @ np.array([dx, dy, 0.0])
    return float(d[0]), float(d[1])


# ------------------------------------------------------------------ main
def build(b, L):
    rng = rng_for("bld", b["id"])
    fam = family_of(b)
    W, D, n_st = float(b["front"]), float(b["depth"]), int(b["storeys"])
    t = T_WALL
    H = n_st * STOREY
    out = Built(b)
    cmp_ = compass(b)
    vol = Vol(W, D, H, t=t, cx=0.0, cy=D / 2, z=FLOOR_Z, mat_out="frame_dark", mat_in="wall_in")
    wm = {s: out.g("WALL_" + cmp_[s]) for s in Vol.SIDES}
    base, roof, inter = out.g("BASE"), out.g("ROOF"), out.g("INTERIOR")
    floor2 = out.g("FLOOR2") if n_st == 2 else None
    is_open_front = b["kind"] in ("market", "boatyard")
    lap = "vertical" if b["wall"] in ("dwoodl", "lwoodw") or fam == "long_shed" and rng.random() < 0.5 else "lap"
    if b["kind"] == "warehouse":
        lap = "vertical"

    # ---------------- openings plan
    windows = []     # (side, x0, x1, z0, z1, style)
    dx0, dx1 = W / 2 - DOOR_W / 2, W / 2 + DOOR_W / 2
    if not is_open_front:
        vol.cut("front", dx0, dx1, 0.0, DOOR_H)
    flank = (W - DOOR_W) / 2

    def win(side, xc, zs, w=0.74, h=0.82, **style):
        zs = zs
        vol.cut(side, xc - w / 2, xc + w / 2, zs, zs + h)
        windows.append((side, xc - w / 2, xc + w / 2, zs, zs + h, style))

    sill = 0.98
    box_chance = 0.55 if fam in ("cottage", "family_house", "stilt") else 0.2
    if not is_open_front:
        if b["kind"] in ("store", "eatery"):
            win("front", flank / 2, 0.75, w=min(1.5, flank - 0.5), h=1.15, shutters=None, mullions=(2, 1), lintel="wood")
            if flank > 1.5:
                win("front", W - flank / 2, sill, box=True)
        elif b["kind"] == "warehouse":
            # cart doorway beside the personnel door
            vol.cut("front", 0.45, 0.45 + min(1.7, flank - 0.7), 0.0, 2.05)
        elif flank >= 1.45:
            for xc in (flank / 2, W - flank / 2):
                win("front", xc, sill, w=min(0.8, flank - 0.75), box=rng.random() < box_chance)
    for fl in range(n_st):
        zs = sill + fl * STOREY
        n_side = 2 if D >= 4.4 else 1
        for i in range(n_side):
            yc = D * (i + 1) / (n_side + 1) if n_side > 1 else D * 0.45
            if not (n_st == 2 and fl == 0 and yc > D - 1.3):
                win("right", yc, zs, box=rng.random() < box_chance * 0.5)
        win("left", D * 0.5, zs, w=0.66)
        if fl == 1:
            if fam == "family_house":
                vol.cut("front", W / 2 - 0.42, W / 2 + 0.42, STOREY, STOREY + 1.9)        # balcony door
                for xc in (flank / 2, W - flank / 2):
                    if flank >= 1.45:
                        win("front", xc, zs, w=0.66)
            else:
                k = 3 if W >= 7 else 2
                for i in range(k):
                    win("front", W * (i + 1) / (k + 1), zs, box=fam == "stacked" and rng.random() < 0.6)
    if fam in ("civic", "long_shed") and W >= 6.5 and not is_open_front:
        win("back", W * 0.3, sill + 0.5, w=0.6, h=0.5, shutters=None)
        win("back", W * 0.7, sill + 0.5, w=0.6, h=0.5, shutters=None)

    # ---------------- walls: slab + cladding + corner posts + windows
    if is_open_front:
        vol.skip.add("front")
    for s in Vol.SIDES:
        m = wm[s]
        Ws = vol.width(s)
        if s in vol.skip:
            # open front: posts and a head beam instead of a wall
            with m.push(vol.side(s)):
                n = max(3, int(round(Ws / 2.4)) + 1)
                for i in range(n):
                    x = 0.07 + (Ws - 0.14) * i / (n - 1)
                    m.box(x - 0.08, 0.0, 0, x + 0.08, 0.16, H, "wood_dark", wob=0.01, rng=rng, vary=0.05)
                    if 0 < i < n - 1 or True:
                        for sg in (-1, 1):
                            if 0.2 < x + sg * 0.55 < Ws - 0.2:
                                m.beam((x + sg * 0.08, 0.08, H - 0.75), (x + sg * 0.6, 0.08, H - 0.16), 0.09, 0.09, "wood_dark", up=(0, 1, 0))
                m.box(-0.05, -0.02, H - 0.2, Ws + 0.05, 0.18, H, "wood_dark")
            continue
        with m.push(vol.side(s)):
            ops = vol.openings[s]
            if s in ("front", "back"):
                parts.wall(m, Ws, H, t, ops, "wood_mid", "wall_in", mat_rev="frame")
            else:
                with m.push(T(t, 0, 0)):
                    parts.wall(m, Ws - 2 * t, H, t, [(a - t, c - t, d, e) for a, c, d, e in ops], "wood_mid", "wall_in", mat_rev="frame")
            if b["kind"] == "warehouse":
                parts.stone_course(m, Ws, 1.1, rng, proud=0.05, rows=4, depth=0.02)
                parts.clad(m, Ws, 1.1, H, ops, rng, style="vertical")
            else:
                parts.clad(m, Ws, 0.0, H, ops, rng, style=lap)
            # corner posts + storey band
            for x in (0.0, Ws):
                m.box(x - 0.07, -0.075, -0.04, x + 0.07, 0.07, H, "frame", wob=0.006, rng=rng)
            if n_st == 2:
                m.box(-0.05, -0.06, STOREY - 0.09, Ws + 0.05, 0.0, STOREY + 0.05, "frame")
            m.box(-0.05, -0.055, H - 0.12, Ws + 0.05, 0.0, H, "frame")
        for (sd, x0, x1, z0, z1, style) in windows:
            if sd == s:
                st = dict(shutters="open", lintel=None, frame_mat="frame", shutter_style=rng.choice(["louver", "plank"]))
                st.update(style)
                with m.push(vol.side(s)):
                    parts.window(m, x0, x1, z0, z1, t, rng, **st)
                    if st.get("lintel") is None:
                        m.box(x0 - 0.07, -0.05, z1, x1 + 0.07, 0.02, z1 + 0.07, "frame")

    # ---------------- door
    fm = wm["front"]
    if not is_open_front:
        with fm.push(vol.side("front")):
            parts.door_frame(fm, dx0, dx1, 0.0, DOOR_H, t, rng, mat="frame", step=False)
        leaf = parts.door_leaf(DOOR_W - 0.2, DOOR_H - 0.11, rng, name="DOOR_main")
        out.meshes["DOOR_main"] = leaf
        out.meta["door_pivot"] = (-DOOR_W / 2 + 0.10, 0.04, FLOOR_Z + 0.005)
        if b["kind"] == "warehouse":
            with fm.push(vol.side("front"), T(0.45, 0.03, 0), Rz(math.radians(-100))):
                fm.merge(parts.door_leaf(min(1.7, flank - 0.7) / 2, 2.0, rng))
    # doorstep
    base.box(-0.75, -0.42, -0.25, 0.75, 0.0, FLOOR_Z - 0.01, "stone_light", wob=0.02, rng=rng, vary=0.05)
    base.box(-0.6, -0.72, -0.25, 0.6, -0.42, FLOOR_Z * 0.5, "stone_light", wob=0.02, rng=rng, vary=0.05)

    # ---------------- base + floors
    if b["level"] != "DECK":
        parts.footings(base, W, D, FLOOR_Z - 0.06, rng, cx=0, cy=D / 2)
    xi0, xi1, yi0, yi1 = -W / 2 + t, W / 2 - t, t, D - t
    parts.floor_planks(base, xi0, xi1, yi0, yi1, FLOOR_Z, rng, joists=False, th=0.06)
    stair = None
    if n_st == 2:
        sx0 = xi1 - 2.5; sw = 0.78
        stair = dict(x0=sx0, x1=xi1 - 0.1, y0=yi1 - sw - 0.04, y1=yi1 - 0.04)
        with inter.push(T(sx0, stair["y0"], FLOOR_Z)):
            parts.stair_flight(inter, 2.4, STOREY, sw, rng, mat="wood_light", rail="left", rail_mat="frame")
        hole = (sx0 + 0.55, xi1, stair["y0"] - 0.02, yi1)
        parts.floor_planks(floor2, xi0, xi1, yi0, yi1, FLOOR_Z + STOREY, rng, hole=hole, th=0.05)
        # guard rail round the stairwell
        z2 = FLOOR_Z + STOREY
        floor2.beam((hole[0], hole[2], z2 + 0.9), (hole[1] - 0.85, hole[2], z2 + 0.9), 0.05, 0.05, "frame")
        for i in range(4):
            x = hole[0] + (hole[1] - 0.85 - hole[0]) * i / 3
            floor2.box(x - 0.02, hole[2] - 0.02, z2, x + 0.02, hole[2] + 0.02, z2 + 0.9, "frame")
        floor2.beam((hole[0], hole[2], z2 + 0.9), (hole[0], hole[3], z2 + 0.9), 0.05, 0.05, "frame")
        floor2.box(hole[0] - 0.02, hole[3] - 0.04, z2, hole[0] + 0.02, hole[3], z2 + 0.9, "frame")

    # ---------------- roof
    ztop = FLOOR_Z + H
    pitch = {"cottage": rng.uniform(27, 34), "family_house": rng.uniform(30, 36), "stilt": 16.0,
             "stacked": rng.uniform(24, 30), "long_shed": rng.uniform(17, 22), "civic": rng.uniform(26, 30)}[fam]
    ridge_x = True
    if fam == "family_house" or (fam == "cottage" and rng.random() < 0.4) or (fam == "civic" and b["kind"] == "school"):
        ridge_x = False                        # gable faces the street
    eave = 0.36
    if fam == "stilt":
        with roof.push(T(0, D / 2, 0)):
            zhi = parts.shed_roof(roof, W, D, ztop + 0.45, pitch, rng, eave=0.42, verge=0.3, cover="tin")
        # wedge walls under the mono-pitch: front is the high side here (rotate)
        out.meta["roof"] = "shed"
        rise = D * math.tan(math.radians(pitch))
        for s in ("left", "right"):
            m = wm[s]
            with m.push(vol.side(s)):
                apex = 1.0 if s == "left" else 0.0     # high edge at the back (+y)
                parts.gable_wall(m, D, rise + 0.45, t, "wood_mid", "wall_in", z0=H, apex=apex)
                parts.clad_gable(m, D, H, rise + 0.45, rng, apex=apex)
        with wm["back"].push(vol.side("back")):
            parts.wall(wm["back"], W, rise + 0.45, t, [], "wood_mid", "wall_in", z0=H)
            parts.clad(wm["back"], W, H, H + rise + 0.45, [], rng, style=lap)
        with wm["front"].push(vol.side("front")):
            parts.wall(wm["front"], W, 0.45, t, [], "wood_mid", "wall_in", z0=H)
            parts.clad(wm["front"], W, H, H + 0.45, [], rng, style=lap)
        zr = zhi
    else:
        if ridge_x:
            with roof.push(T(0, D / 2, 0)):
                zr = parts.gable_roof(roof, W, D, ztop, pitch, rng, eave=eave, verge=0.3, sag=0.035, cover="tin", barge_mat="frame")
            gs, gw = ("left", "right"), D
        else:
            over = 0.95 if fam == "family_house" else 0.3
            with roof.push(T(0, D / 2 - (over - 0.3) / 2, 0), Rz(math.pi / 2)):
                zr = parts.gable_roof(roof, D + (over - 0.3), W, ztop, pitch, rng, eave=eave, verge=0.3, sag=0.03, cover="tin", barge_mat="frame")
            gs, gw = ("front", "back"), W
        rise = gw / 2 * math.tan(math.radians(pitch))
        for s in gs:
            m = wm[s]
            if s in vol.skip:
                m = roof
            with m.push(vol.side(s)):
                parts.gable_wall(m, gw, rise, t, "wood_mid", "wall_in", z0=H)
                parts.clad_gable(m, gw, H, rise, rng)
                # louvred vent
                m.box(gw / 2 - 0.2, -0.06, H + rise * 0.3, gw / 2 + 0.2, -0.03, H + rise * 0.3 + 0.32, "frame")
                for i in range(4):
                    m.box(gw / 2 - 0.16, -0.075, H + rise * 0.3 + 0.04 + i * 0.07, gw / 2 + 0.16, -0.055, H + rise * 0.3 + 0.08 + i * 0.07, "trim")
        out.meta["roof"] = "gable_x" if ridge_x else "gable_y"
    # tie beams
    for i in range(max(2, int(W / 1.5)) if not ridge_x else max(2, int(W / 1.6))):
        k = (i + 0.5) / max(2, int(W / 1.6))
        if ridge_x:
            x = -W / 2 + W * k
            roof.box(x - 0.05, 0.02, ztop - 0.02, x + 0.05, D - 0.02, ztop + 0.10, "wood_dark")
        else:
            y = D * k
            roof.box(-W / 2 + 0.02, y - 0.05, ztop - 0.02, W / 2 - 0.02, y + 0.05, ztop + 0.10, "wood_dark")

    # ---------------- family features (each building breaks its box at least twice)
    feats = []
    if fam in ("cottage", "stilt"):
        # door canopy on posts
        pw = min(2.6, W - 0.6)
        with fm.push(T(0, -0.42, FLOOR_Z + DOOR_H + 0.28), Rz(math.pi)):
            parts.shed_roof(fm, pw, 0.9, 0.0, 14, rng, eave=0.06, verge=0.1, cover="tin")
        for x in (-pw / 2 + 0.06, pw / 2 - 0.06):
            fm.box(x - 0.05, -0.86, -0.05, x + 0.05, -0.76, FLOOR_Z + DOOR_H + 0.28, "frame", wob=0.008, rng=rng)
            fm.beam((x, -0.81, FLOOR_Z + DOOR_H - 0.25), (x - math.copysign(0.4, x), -0.81, FLOOR_Z + DOOR_H + 0.2), 0.06, 0.06, "frame", up=(0, 1, 0))
        feats.append("door canopy")
    if fam == "family_house":
        with fm.push(vol.side("front")):
            parts.balcony(fm, 0.12, W - 0.12, STOREY, 0.86, rng, style=rng.choice(["baluster", "slat", "cross"]), mat="trim",
                          posts_to=H - 0.05, wood="wood_dark", deck_mat="wood_light")
            # balcony door, ajar
            with fm.push(T(W / 2 - 0.42 + 0.03, 0.03, STOREY + 0.02), Rz(math.radians(-70))):
                fm.merge(parts.door_leaf(0.78, 1.84, rng))
            # posts down to the ground
            for x in (0.17, W - 0.17):
                fm.box(x - 0.05, -0.84, -FLOOR_Z, x + 0.05, -0.74, STOREY - 0.2, "wood_dark", wob=0.008, rng=rng)
        feats.append("front balcony under the gable")
    if fam == "stacked":
        with fm.push(vol.side("front")):
            aw = flank - 0.25 if b["kind"] in ("store", "eatery") else W - 0.5
            ax0 = 0.12 if b["kind"] in ("store", "eatery") else 0.25
            parts.awning(fm, ax0, ax0 + aw, 2.2 if n_st == 1 else 2.25, 0.8, rng, drop=0.32)
            # sign board on brackets
            sx = W - flank / 2 if b["kind"] in ("store", "eatery") else W / 2
            fm.box(sx - 0.62, -0.09, 2.02 if n_st == 2 else H - 0.42, sx + 0.62, -0.05, (2.02 if n_st == 2 else H - 0.42) + 0.34, "frame", wob=0.01, rng=rng)
            fm.box(sx - 0.56, -0.10, (2.02 if n_st == 2 else H - 0.42) + 0.05, sx + 0.56, -0.09, (2.02 if n_st == 2 else H - 0.42) + 0.29, "trim")
        feats.append("awning + sign")
    if fam in ("long_shed", "civic") and b["kind"] in ("market", "boatyard"):
        with fm.push(vol.side("front")):
            parts.awning(fm, 0.1, W - 0.1, H - 0.05, 0.85, rng, drop=0.36)
        feats.append("open front + awning")
    if fam == "civic":
        # bell-cot / cupola on the ridge
        cx_, cy_ = 0.0, D / 2
        with roof.push(T(cx_, cy_, zr - 0.25)):
            for x in (-0.3, 0.3):
                for y in (-0.3, 0.3):
                    roof.box(x - 0.045, y - 0.045, 0, x + 0.045, y + 0.045, 1.05, "frame")
            parts.hip_roof(roof, 0.6, 0.6, 1.05, 38, rng, eave=0.16, tiles=False, finial=True, tile_mats=("tin",))
            roof.box(-0.36, -0.36, 0.0, 0.36, 0.36, 0.3, "wall", rng=rng, vary=0.05)
            with roof.push(T(0, 0, 0.55)):
                roof.lathe([(0.05, 0.3), (0.1, 0.24), (0.14, 0.02), (0.15, 0.0), (0.12, 0.0)], 8, "brass")
        feats.append("bell-cot")
    # side lean-to store where the plot has room
    for s in ("right", "left"):
        if fam in ("cottage", "family_house", "stacked", "civic", "long_shed") and b["level"] != "DECK" and len(feats) < 3 \
                and side_clearance(L, b, s, 1.5) > 0 and not is_open_front:
            m = wm[s]
            lw = min(2.4, D - 1.2)
            x0 = (D - lw) - 0.25 if s == "right" else 0.25
            with m.push(vol.side(s)):
                with m.push(T(x0 + lw / 2, -0.55, 1.75), Rz(math.pi)):
                    parts.shed_roof(m, lw, 1.1, 0.0, 16, rng, eave=0.05, verge=0.12, cover="tin")
                for x in (x0 + 0.05, x0 + lw - 0.05):
                    m.box(x - 0.045, -1.12, -FLOOR_Z, x + 0.045, -1.03, 1.78, "wood_dark", wob=0.01, rng=rng)
                # firewood, barrel, crate under it
                for k in range(3):
                    for j in range(int(lw / 0.14) - 6):
                        m.cbox(x0 + 0.25 + j * 0.13, -0.3, -FLOOR_Z + 0.07 + k * 0.12, 0.11, 0.42, 0.11, "wood_light", rz=rng.uniform(-0.1, 0.1), rng=rng, vary=0.14)
                with m.push(T(x0 + lw - 0.4, -0.6, -FLOOR_Z)):
                    m.lathe([(0.2, 0), (0.26, 0.3), (0.26, 0.5), (0.2, 0.8), (0.0, 0.8)], 9, "wood_mid")
            feats.append("lean-to store (%s)" % cmp_[s])
            break
    if fam == "stilt":
        # porch rail + net rack on the boardwalk side
        with fm.push(T(W / 2 - 1.0, -0.5, 0), Rz(math.pi)):
            F.net_rack(fm, rng, w=1.3)
        feats.append("net rack")
    out.meta["features"] = feats

    # ---------------- interior: anchors
    _furnish(out, b, vol, rng, stair, floor2, inter, roof, zr, fam, is_open_front)
    # exterior touches by the door: bench / pots
    if fam in ("cottage", "family_house") and flank > 1.6:
        with fm.push(T(-W / 2 + flank / 2, -0.02, 0), Rz(math.pi)):
            F.bench(fm, rng, w=min(1.2, flank - 0.5))
    for x in (-0.72, 0.72):
        if rng.random() < 0.7:
            with fm.push(T(x, -0.25, FLOOR_Z - 0.0)):
                fm.lathe([(0.09, 0), (0.14, 0.16), (0.12, 0.2), (0.1, 0.2)], 8, "clay")
                with fm.push(T(0, 0, 0.3)):
                    fm.blob(0.17, 0.17, 0.16, rng.choice(["foliage_a", "foliage_c"]), rng, sub=0, rough=0.3)
    return out


# ------------------------------------------------------------------ interior
def _furnish(out, b, vol, rng, stair, floor2, inter, roof, zr, fam, open_front):
    W, D, t = vol.W, vol.D, vol.t
    n_st = int(b["storeys"])
    xi0, xi1, yi0, yi1 = -W / 2 + t, W / 2 - t, t, D - t
    items = list(enumerate(a["type"] for a in b["interior"]["anchors"]))
    # which floor each anchor wants
    def floor_of(i, typ):
        if n_st == 1:
            return 0
        if b["kind"] == "home":
            return 1 if typ == "bed" or i >= 13 else 0
        if b["kind"] == "store":
            first_lamp = [k for k, tt in items if tt == "lamp"][0]
            return 1 if i > first_lamp else 0
        if b["kind"] == "netloft":
            return 1 if typ in ("net_frame", "storage") else 0
        return 0

    # usable wall runs per floor: (side, start, end) along the wall, inner frame
    def runs(fl):
        Ll = D - 2 * t
        if n_st == 2:
            back = [] if fl == 1 else [("back", 0.75, max(0.75, (stair["x0"] - 0.55) - xi0))] if False else []
            # right wall inner frame runs front->back (x = y - t)
            right_end = (stair["y0"] - 0.55 - t) if fl == 0 else (stair["y0"] - 0.6 - t)
            out_ = [("left", 0.12, Ll - 0.12), ("right", 0.5 if fl == 0 else 0.12, right_end)]
            if fl == 0:
                bl = (stair["x0"] - 0.6) - xi0
                if bl > 1.2:
                    out_.insert(1, ("back", W - 2 * t - bl + 0.0, W - 2 * t - 0.7) if False else ("back", (W - 2 * t) - bl, (W - 2 * t) - 0.72))
            return out_
        return [("left", 0.3, Ll - 0.1), ("back", 0.70, W - 2 * t - 0.70), ("right", 0.1, Ll - 0.3)]

    def frame_of(side):
        """inner frame with x measured from the wall's left end as seen from INSIDE... kept as
        the outside convention; callers only need consistency."""
        M = vol.side(side) @ T(0, t, 0)
        if side in ("left", "right"):
            M = M @ T(t, 0, 0)
        return M

    cursors = {}
    placed_tables = []          # (M_item, w, d, floor, free chair slots)
    lamps = [(i, tt) for i, tt in items if tt == "lamp"]
    counters = {}

    def add_anchor(i, typ, pos, stand, face, pose, fl, extra=None):
        k = counters.get(typ, 0); counters[typ] = k + 1
        a = dict(id=f"IA_{typ}_{k}", type=typ, slot=k, layout_index=i, floor=fl, pose=pose,
                 pos=[round(v, 3) for v in pos], stand=[round(v, 3) for v in stand] if stand else None,
                 facing=[round(face[0], 3), round(face[1], 3)] if face else None)
        if extra:
            a.update(extra)
        out.anchors.append(a)
        return a

    def mesh_for(fl):
        return floor2 if fl == 1 else inter

    def zf(fl):
        return FLOOR_Z + fl * STOREY

    def place_wall(i, typ, fl):
        w, d, _, fn, pose = F.REG[typ]
        head_on = typ == "bed" and fl == 1
        ww, dd = (0.95, 1.95) if head_on else (w, d)
        for side, s0, s1 in runs(fl):
            if head_on and side != "left":
                ww, dd = w, d; ho = False
            else:
                ho = head_on
            key = (fl, side)
            c = cursors.get(key, s0)
            if c + ww <= s1 + 1e-6:
                cursors[key] = c + ww + 0.08
                M = frame_of(side) @ T(c + ww / 2, 0, zf(fl))
                m = mesh_for(fl)
                if ho:
                    with m.push(M, T(0, 0.98, 0), Rz(math.pi / 2), T(0, -0.46, 0)):
                        fn(m, rng)
                    use = _loc(M, 0, 0.95, 0.5); st = _loc(M, 0, 1.95 + F.STAND, 0)
                    face = _dir(M, 0, -1)
                else:
                    with m.push(M):
                        if typ == "stove":
                            fn(m, rng, flue_to=(n_st - fl) * STOREY + 0.2)
                        else:
                            fn(m, rng)
                    st = _loc(M, 0, dd + F.STAND, 0)
                    use = _loc(M, 0, dd / 2, 0.5) if pose == "lie" else st
                    face = _dir(M, 0, -1)
                    if pose == "lie":
                        face = _dir(M, -1, 0)
                    if pose == "sit":           # sit behind a wall desk, facing the room
                        use = _loc(M, 0, dd + 0.3, 0.0)
                extra = {}
                if typ == "stove":
                    fx = _loc(M, 0.22, 0.12, 0)
                    extra["flue"] = [round(fx[0], 3), round(fx[1], 3)]
                    # flue pokes through the roof
                    parts.stovepipe(roof, fx[0], fx[1], FLOOR_Z + n_st * STOREY + 0.15, max(0.9, zr - (FLOOR_Z + n_st * STOREY) + 0.55), rng)
                    extra["light"] = [round(v, 3) for v in _loc(M, 0, dd + 0.15, 0.45)]
                add_anchor(i, typ, use, st, face, pose, fl, extra)
                return True
        return False

    # free-standing zone per floor
    def free_zone(fl):
        y0 = yi0 + (1.15 if fl == 0 else 0.5)
        y1 = yi1 - (0.75 if not stair else 1.15)
        x0 = xi0 + (0.75 if fl == 0 else 2.2)
        x1 = xi1 - (0.75 if fl == 0 else 0.5)
        return x0, x1, y0, y1

    free_cur = {}

    def place_free(i, typ, fl, want_chairs=0):
        w, d, _, fn, pose = F.REG[typ]
        x0, x1, y0, y1 = free_zone(fl)
        cw = w + (0.95 if want_chairs else 0.25)
        ch = d + 0.5
        st = free_cur.setdefault(fl, dict(x=x0, y=y0, rowh=0.0))
        if st["x"] + cw > x1 + 1e-6 and st["x"] > x0:
            st["x"] = x0; st["y"] += st["rowh"]; st["rowh"] = 0.0
        if st["y"] + ch > y1 + 0.45 or st["x"] + cw > x1 + 0.6:
            return False
        cx, cy = st["x"] + cw / 2, st["y"] + ch / 2
        st["x"] += cw; st["rowh"] = max(st["rowh"], ch)
        # user side faces the back of the building for most things
        rot = 0.0 if typ == "stall" else math.pi
        M = T(cx, cy - (d / 2 if rot == 0 else -d / 2), zf(fl)) @ Rz(rot)
        m = mesh_for(fl)
        with m.push(M):
            fn(m, rng)
        if typ == "stall":
            stp = _loc(M, 0, -F.STAND, 0); face = _dir(M, 0, 1)
        else:
            stp = _loc(M, 0, d + F.STAND, 0); face = _dir(M, 0, -1)
        use = stp
        if pose == "sit":
            use = _loc(M, 0, d / 2, 0.45) if typ == "bench" else _loc(M, 0, d + 0.3, 0)
        add_anchor(i, typ, use, stp, face, pose, fl)
        if typ in ("table", "desk"):
            placed_tables.append(dict(M=M, w=w, d=d, fl=fl, slots=[-1, 1]))
        return True

    seats = [(i, tt) for i, tt in items if tt == "chair"]
    n_tables = max(1, sum(1 for _, tt in items if tt == "table"))
    for i, typ in items:
        mode = F.REG[typ][2]
        fl = floor_of(i, typ)
        ok = True
        if mode == "wall":
            ok = place_wall(i, typ, fl) or (n_st == 2 and place_wall(i, typ, 1 - fl))
        elif mode == "free":
            ok = place_free(i, typ, fl, want_chairs=1 if typ == "table" else 0) or (n_st == 2 and place_free(i, typ, 1 - fl))
        elif mode == "porch":
            # outdoor rack already modelled on the front; anchor in front of it
            add_anchor(i, typ, (W / 2 - 1.0, -0.95, 0), (W / 2 - 1.0, -0.95, 0), (0, 1), "stand", 0)
        if not ok:
            out.unplaced.append((i, typ))
    # chairs at table ends, else against the front wall
    for i, typ in seats:
        fl = floor_of(i, typ)
        cand = [tb for tb in placed_tables if tb["slots"] and tb["fl"] == fl] or [tb for tb in placed_tables if tb["slots"]]
        if cand:
            tb = cand[0]; sg = tb["slots"].pop(0)
            M = tb["M"] @ T(sg * (tb["w"] / 2 + 0.42), tb["d"] / 2, 0) @ Rz(sg * math.pi / 2) @ T(0, -0.19, 0)
            m = mesh_for(tb["fl"])
            with m.push(M):
                F.chair(m, rng)
            seat = _loc(M, 0, 0.19, 0.46)
            add_anchor(i, typ, seat, _loc(M, 0, 0.19, 0), _dir(M, 0, 1), "sit", tb["fl"], dict(table=True))
        else:
            # spare chair by the front wall
            k = counters.get("chair", 0)
            x = xi1 - 0.5 - 0.5 * (k % 3)
            M = T(x, yi0 + 0.02, zf(fl))
            with mesh_for(fl).push(M):
                F.chair(mesh_for(fl), rng)
            add_anchor(i, typ, _loc(M, 0, 0.19, 0.46), _loc(M, 0, 0.19, 0), (0, 1), "sit", fl)
    # lamps: one per floor first, then spread
    for k, (i, typ) in enumerate(lamps):
        fl = k % n_st
        nth = k // n_st
        cx = (xi0 + xi1) / 2 + (0 if nth == 0 else (W * 0.25 * (1 if nth % 2 else -1)))
        cy = (yi0 + yi1) / 2 - (0.3 if stair else 0) + (0 if nth == 0 else D * 0.15)
        ceil = FLOOR_Z + (fl + 1) * STOREY + (0.05 if fl == n_st - 1 else -0.06)
        m = roof if fl == n_st - 1 else floor2
        with m.push(T(cx, cy, ceil)):
            F.lamp_hanging(m, rng, drop=0.35)
        add_anchor(i, typ, (cx, cy, ceil - 0.5), None, None, None, fl)

    # ---------------- door anchor + interior walk graph
    for i, typ in items:
        if typ == "stairs_interior" and stair:
            add_anchor(i, typ, (stair["x0"] - 0.4, (stair["y0"] + stair["y1"]) / 2, FLOOR_Z), None, (1, 0), None, 0,
                       dict(top=[round(stair["x1"] - 0.05, 3), round((stair["y0"] + stair["y1"]) / 2, 3), FLOOR_Z + STOREY]))
        if typ == "door":
            add_anchor(i, "door", (0, 0, FLOOR_Z), (0, -0.9, 0), (0, 1), "stand", 0,
                       dict(node="DOOR_main", open_deg=100.0, stand_in=[0, 0.75, FLOOR_Z]))
    out.node("out", 0, -0.9, 0.0)
    out.node("in", 0, 0.75, FLOOR_Z)
    out.edge("out", "in", "doorway")
    hubs = {0: out.node("hub0", 0.0, min(D * 0.42, 1.9) if not open_front else 1.2, FLOOR_Z)}
    out.edge("in", "hub0")
    if stair:
        ys = (stair["y0"] + stair["y1"]) / 2
        out.node("stair_bot", stair["x0"] - 0.4, ys, FLOOR_Z)
        out.node("stair_top", stair["x1"] - 0.05, ys, FLOOR_Z + STOREY)
        out.node("land2", stair["x1"] - 0.45, stair["y0"] - 0.45, FLOOR_Z + STOREY)
        hubs[1] = out.node("hub1", (xi0 + xi1) / 2 + 0.9, (yi0 + stair["y0"]) / 2, FLOOR_Z + STOREY)
        out.node("pre_stair", stair["x0"] - 0.45, stair["y0"] - 0.5, FLOOR_Z)
        out.edge("hub0", "pre_stair"); out.edge("pre_stair", "stair_bot")
        out.edge("stair_bot", "stair_top", "stair")
        out.edge("stair_top", "land2"); out.edge("land2", "hub1")
    for a in out.anchors:
        if a["stand"] is None or a["type"] == "door":
            continue
        n = out.node(a["id"], *a["stand"])
        if a["type"] == "net_rack":
            out.edge("out", n)
        else:
            out.edge(hubs[a["floor"]], n)


def sidecar(out, L):
    """JSON-ready description for Godot and for filling the layout's anchor stubs.
    Positions are Godot-local (x, y up, z toward the front)."""
    from .world import building_frame
    b = out.b
    origin, yaw = building_frame(b)
    g = lambda p: [round(v, 3) for v in to_godot(p)]
    anchors = []
    for a in out.anchors:
        d = dict(a)
        d["pos"] = g(a["pos"])
        if a["stand"]: d["stand"] = g(a["stand"])
        if a["facing"]: d["facing"] = [a["facing"][0], -a["facing"][1]]      # (dx, dz)
        for k in ("stand_in", "light", "top"):
            if k in d: d[k] = g(d[k])
        d.pop("flue", None)
        anchors.append(d)
    return dict(
        schema="living-tides.building", version=1, id=b["id"], name=b["name"], kind=b["kind"],
        family=family_of(b), origin=list(origin), yaw_deg=yaw, storeys=b["storeys"],
        frame="Godot-local: +x right, +y up, +z out of the front door. Pivot = front-door threshold at terrace level.",
        groups=sorted(out.meshes), compass=compass(b), features=out.meta.get("features", []),
        door=dict(node="DOOR_main", pivot=g(out.meta["door_pivot"]), open_deg=100.0) if "door_pivot" in out.meta else None,
        anchors=anchors,
        nav=dict(nodes={k: g(v) for k, v in out.nodes.items()},
                 edges=[dict(a=a, b=c, type=t) for a, c, t in out.edges],
                 entry="out", entry_matches="door_" + b["id"]),
        unplaced=[dict(layout_index=i, type=t) for i, t in out.unplaced],
        tris=out.tri_count,
    )
