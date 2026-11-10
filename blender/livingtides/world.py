"""Read-only access to data/village_layout.json (the single source of truth)
plus the coordinate conventions shared by Blender, Godot and the tests.

Layout / Godot axes : +x east, +y up,   +z south
Blender axes        : +x east, +y north, +z up      =>  blender = (x, -z, y)
"""
from __future__ import annotations
import json, math, os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LAYOUT_PATH = os.path.join(ROOT, "data", "village_layout.json")

STOREY = 2.4          # ART_BIBLE §3
T_WALL = 0.15         # BUILDING_CONTRACT
FLOOR_Z = 0.20        # ground-floor walking surface above terrace level
DOOR_W, DOOR_H = 0.9, 1.9


def load(path=LAYOUT_PATH):
    with open(path) as f:
        return json.load(f)


def to_blender(p):
    x, y, z = p
    return (x, -z, y)


def to_godot(p):
    x, y, z = p
    return (x, z, -y)


def pt_in_poly(x, z, poly):
    inside = False
    n = len(poly)
    for i in range(n):
        x1, z1 = poly[i]; x2, z2 = poly[(i + 1) % n]
        if (z1 > z) != (z2 > z) and x < (x2 - x1) * (z - z1) / (z2 - z1) + x1:
            inside = not inside
    return inside


def ground_h(L, x, z):
    """Data ground height: highest land polygon containing the point, else None (sea)."""
    h = None
    for l in L["land"]:
        if pt_in_poly(x, z, l["poly"]):
            h = l["h"] if h is None else max(h, l["h"])
    return h


def seg_dist(px, pz, ax, az, bx, bz):
    vx, vz = bx - ax, bz - az
    L2 = vx * vx + vz * vz
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * vx + (pz - az) * vz) / L2))
    return math.hypot(px - (ax + t * vx), pz - (az + t * vz))


def building_frame(b):
    """Origin (layout coords) at the front-door threshold and yaw (deg, about +y,
    Godot convention = Blender Z rotation).  Local front is Godot +Z / Blender -Y."""
    x0, x1, z0, z1 = b["footprint"]
    if b["facing"] == "S":
        return (b["cx"], b["y"], z1), 0.0
    if b["facing"] == "E":
        return (x1, b["y"], b["cz"]), 90.0
    raise ValueError(b["facing"])


def local_to_layout(b, lx, ly, lz):
    """Blender-local building point (x right, y into building, z up) -> layout xyz."""
    (ox, oy, oz), yaw = building_frame(b)
    a = math.radians(yaw); c, s = math.cos(a), math.sin(a)
    bx, by = lx * c - ly * s, lx * s + ly * c          # blender world offset
    return (ox + bx, oy + lz, oz - by)


def compass(b):
    """local side -> compass letter."""
    if b["facing"] == "S":
        return {"front": "S", "right": "E", "back": "N", "left": "W"}
    return {"front": "E", "right": "N", "back": "W", "left": "S"}


def side_clearance(L, b, side, reach=1.4):
    """Free metres beside a building wall (0 if anything is in the way within
    `reach`): other footprints, terrace edge, walk-graph links."""
    W, D = b["front"], b["depth"]
    pts = []
    for k in (0.15, 0.5, 0.85):
        for r in (0.5, reach):
            if side == "right": pts.append((W / 2 + r, D * k))
            elif side == "left": pts.append((-W / 2 - r, D * k))
            elif side == "back": pts.append((-W / 2 + W * k, D + r))
    nodes = L["nav"]["nodes"]
    for lx, ly in pts:
        x, _, z = local_to_layout(b, lx, ly, 0)
        if b["level"] == "DECK":
            return 0.0
        if ground_h(L, x, z) != b["y"]:
            return 0.0
        for o in L["buildings"]:
            if o is b: continue
            x0, x1, z0, z1 = o["footprint"]
            if x0 - 0.4 <= x <= x1 + 0.4 and z0 - 0.4 <= z <= z1 + 0.4:
                return 0.0
        for e in L["nav"]["edges"]:
            a, c = nodes[e["a"]], nodes[e["b"]]
            if abs(a["y"] - b["y"]) < 3 and seg_dist(x, z, a["x"], a["z"], c["x"], c["z"]) < 0.9:
                return 0.0
    return reach
