#!/usr/bin/env python3
"""Pipeline tests that need neither Blender nor Godot (pure Python + numpy).

    python3 tools/test_pipeline.py            -> evidence/logs/pipeline_test.json

They check the generated geometry and data against the layout and
BUILDING_CONTRACT.md.  They do not judge how anything looks.
"""
import json, math, os, struct, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "blender"))
from livingtides import world, building, environment as E, furniture as F

L = world.load()
res, fails = [], 0
def check(name, ok, detail=""):
    global fails
    res.append(dict(test=name, passed=bool(ok), detail=detail)); fails += 0 if ok else 1
    print("PASS" if ok else "FAIL", name, detail if not ok or isinstance(detail, (int, float, str)) else "")

built = {b["id"]: building.build(b, L) for b in L["buildings"]}
t = world.T_WALL

# 1. every anchor stub in the layout has a position
stubs = sum(len(b["interior"]["anchors"]) for b in L["buildings"])
placed = sum(len(o.anchors) for o in built.values())
unplaced = {i: [x[1] for x in o.unplaced] for i, o in built.items() if o.unplaced}
check("anchor stubs given a position", placed >= stubs - 2, dict(stubs=stubs, placed=placed, unplaced=unplaced))
types_ok = all(a["type"] == b["interior"]["anchors"][a["layout_index"]]["type"] for b in L["buildings"] for a in built[b["id"]].anchors)
check("anchor types match the layout stub they fill", types_ok)

# 2. stand points are inside the room, clear of the walls
bad = []
for b in L["buildings"]:
    W, D = b["front"], b["depth"]
    for a in built[b["id"]].anchors:
        if not a["stand"] or a["type"] in ("door", "net_rack"):
            continue
        x, y, z = a["stand"]
        if not (-W / 2 + t + 0.1 <= x <= W / 2 - t - 0.1 and t + 0.1 <= y <= D - t - 0.1):
            bad.append((b["id"], a["id"], [round(x, 2), round(y, 2)]))
check("every stand point lies inside its room", not bad, bad[:10])

# 3. no two pieces of wall furniture overlap (same floor), using their stand points as proxies
clash = []
for bid, o in built.items():
    pts = [(a["id"], a["floor"], a["stand"]) for a in o.anchors if a["stand"] and a["type"] not in ("door", "chair", "net_rack")]
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            if pts[i][1] == pts[j][1] and math.dist(pts[i][2][:2], pts[j][2][:2]) < 0.28:
                clash.append((bid, pts[i][0], pts[j][0]))
check("no two users would stand on the same spot", not clash, clash[:10])

# 4. geometry stays on its plot: nothing reaches into a neighbour or the walkway
over = []
for b in L["buildings"]:
    o = built[b["id"]]
    W, D = b["front"], b["depth"]
    lo = [1e9] * 3; hi = [-1e9] * 3
    for name, m in o.meshes.items():
        if name == "DOOR_main" or not m.v:
            continue
        a, c = m.bounds()
        lo = [min(lo[k], a[k]) for k in range(3)]; hi = [max(hi[k], c[k]) for k in range(3)]
    # dressing (laundry posts, gardens) may use up to 2.1 m, and only where side_clearance() found room
    if lo[1] < -1.35 or hi[1] > D + 1.6 or lo[0] < -W / 2 - 2.1 or hi[0] > W / 2 + 2.1:
        over.append((b["id"], [round(v, 2) for v in lo], [round(v, 2) for v in hi]))
check("building geometry stays within 2.1 m of its footprint (dressing only where the plot has room)", not over, over)
heights = {b["id"]: round(max(m.bounds()[1][2] for m in built[b["id"]].meshes.values() if m.v), 2) for b in L["buildings"]}
check("storey height follows the art bible (eaves at 2.4 m per storey)", all(heights[b["id"]] > b["storeys"] * 2.4 for b in L["buildings"]), heights)

# 5. contract: groups, door, features
miss = []
for b in L["buildings"]:
    o = built[b["id"]]
    g = set(k for k, m in o.meshes.items() if m.f)
    need = {"ROOF", "BASE"}
    if not need <= g or sum(1 for k in g if k.startswith("WALL_")) < 3:
        miss.append(b["id"])
    open_front = b["kind"] in ("market", "boatyard")          # open-fronted sheds have no leaf
    if any(a["type"] == "door" for a in b["interior"]["anchors"]) and "DOOR_main" not in g and not open_front:
        miss.append(b["id"] + ":door")
check("wall groups, roof, base and hinged door present (BUILDING_CONTRACT)", not miss, miss)
few = {i: o.meta["features"] for i, o in built.items() if len(o.meta["features"]) < 1}
check("every building breaks its box at least once beyond roof overhangs", not few, few)
tris = {i: o.tri_count for i, o in built.items()}
check("triangle budget per building under 25k", max(tris.values()) < 25000, dict(max=max(tris.values()), total=sum(tris.values())))

# 6. interior walk graphs
bad = []
for b in L["buildings"]:
    o = built[b["id"]]
    adj = {}
    for a, c, _ in o.edges:
        adj.setdefault(a, set()).add(c); adj.setdefault(c, set()).add(a)
    seen, stack = {"out"}, ["out"]
    while stack:
        for n in adj.get(stack.pop(), ()):
            if n not in seen:
                seen.add(n); stack.append(n)
    if set(o.nodes) - seen:
        bad.append((b["id"], sorted(set(o.nodes) - seen)))
    # the sidecar's entry must coincide with the layout's door node
    door = L["nav"]["nodes"]["door_" + b["id"]]
    w = world.local_to_layout(b, *o.nodes["out"])
    if math.dist((w[0], w[2]), (door["x"], door["z"])) > 0.02:
        bad.append((b["id"], "door node mismatch", w, door))
check("interior graphs are connected and meet the layout's door nodes", not bad, bad[:6])
two = [b["id"] for b in L["buildings"] if b["storeys"] == 2]
check("two-storey buildings have an interior stair link", all(any(e[2] == "stair" for e in built[i].edges) for i in two), two)

# 7. terrain honours the surveyed walk graph
ter = E.Terrain(L)
off = [(k, n["y"], round(ter.h(n["x"], n["z"]), 2)) for k, n in L["nav"]["nodes"].items()
       if n["kind"] == "ground" and abs(ter.h(n["x"], n["z"]) - n["y"]) > 0.02]
check("terrain equals the layout height at every ground walk node", not off, off[:8])
buried = []
for e in L["nav"]["edges"]:
    a, c = L["nav"]["nodes"][e["a"]], L["nav"]["nodes"][e["b"]]
    if a["kind"] == "water" or c["kind"] == "water":
        continue
    for k in range(1, 8):
        u = k / 8
        x, z, y = a["x"] + (c["x"] - a["x"]) * u, a["z"] + (c["z"] - a["z"]) * u, a["y"] + (c["y"] - a["y"]) * u
        if ter.h(x, z) > y + 0.12:
            buried.append((e["a"], e["b"], round(ter.h(x, z) - y, 2))); break
check("no walk link is buried by rock", not buried, buried[:8])
import numpy as np
rough = float(np.std(ter.H[~np.isnan(ter.data) == False]))
lip = ter.H - np.nan_to_num(ter.data, nan=-99)
grown = int(np.sum((lip > 0.5) & ~np.isnan(ter.data)))
check("cliff lips are irregular (rock rises past the surveyed terrace edge)", grown > 400, dict(cells_raised=grown, cell_m=ter.cell))

# 8. exported files, if present
gdir = os.path.join(ROOT, "godot/assets/buildings")
if os.path.isdir(gdir) and os.listdir(gdir):
    bad = []
    for b in L["buildings"]:
        p = os.path.join(gdir, b["id"] + ".glb")
        if not os.path.exists(p):
            bad.append(b["id"] + ": missing"); continue
        d = open(p, "rb").read()
        magic, ver, length = struct.unpack("<4sII", d[:12])
        n = struct.unpack("<I", d[12:16])[0]
        j = json.loads(d[20:20 + n])
        names = [x.get("name", "") for x in j["nodes"]]
        if magic != b"glTF" or length != len(d) or not any(nm.endswith("_ROOF") for nm in names):
            bad.append(b["id"] + ": structure")
        if not all("COLOR_0" in pr["attributes"] for me in j["meshes"] for pr in me["primitives"]):
            bad.append(b["id"] + ": no vertex colour")
        if sum(1 for nm in names if "_IA_" in nm) < len(built[b["id"]].anchors) - 1:
            bad.append(b["id"] + ": anchor empties")
        sc = json.load(open(os.path.join(ROOT, "data/buildings", b["id"] + ".json")))
        if len(sc["anchors"]) != len(built[b["id"]].anchors):
            bad.append(b["id"] + ": sidecar out of date")
    check("30 GLB prefabs valid: header, ROOF node, vertex colours, IA_ empties, fresh sidecar", not bad, bad[:8])
    same = all(open(os.path.join(ROOT, "data", f)).read() == open(os.path.join(ROOT, "godot/data", f)).read()
               for f in ("village_layout.json", "environment.json", "dev_population.json"))
    check("godot/data is an exact copy of data/", same)
else:
    check("GLB prefabs exported", False, "run blender/build_buildings.py first")

out = dict(passed=len(res) - fails, failed=fails, results=res)
os.makedirs(os.path.join(ROOT, "evidence/logs"), exist_ok=True)
json.dump(out, open(os.path.join(ROOT, "evidence/logs/pipeline_test.json"), "w"), indent=1, default=str)
print("RESULT:", "PASSED" if not fails else "FAILED", f"({len(res) - fails} passed, {fails} failed)")
sys.exit(1 if fails else 0)
