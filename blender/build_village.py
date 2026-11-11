"""Build the whole village: environment + all 30 buildings, in place.

    blender -b -P blender/build_village.py -- [--render] [--views overview,harbour] [--no-export]
    (or)  python blender/build_village.py ...   with the `bpy` module installed

Writes   godot/assets/env/{terrain,cliffs,gate,structures,props,vegetation,boats}.glb
         data/environment.json                 lamp / boat / landmark placements for Godot
         blender/out/village_master.blend
         evidence/renders_village_v03/*.png    with --render
Buildings are (re)built here for the master scene; their GLBs and sidecars come
from build_buildings.py.
"""
import sys, os, json, math, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import bpy
from livingtides import world, building, bl_io, palette, environment as E

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
RENDER = "--render" in argv
EXPORT = "--no-export" not in argv
views = None
for i, a in enumerate(argv):
    if a == "--views":
        views = argv[i + 1].split(",")

t0 = time.time()
L = world.load()
scene = bl_io.reset_scene()
env_dir = os.path.join(ROOT, "godot/assets/env"); os.makedirs(env_dir, exist_ok=True)
os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
stats = {}

ter = E.Terrain(L)
groups = {}
def add(name, mesh, coll):
    ob = bl_io.to_object(mesh, bl_io.collection(coll), name=mesh.name)
    groups.setdefault(name, []).append(ob); stats[mesh.name] = mesh.tri_count
    return ob

add("terrain", ter.mesh(), "TERRAIN")
add("cliffs", E.cliffs(L, ter), "CLIFFS")
add("gate", E.gate(L, ter), "CLIFFS")
add("structures", E.structures(L, ter), "STAIR")
pm, veg, info = E.props(L, ter)
add("props", pm, "DECO"); add("vegetation", veg, "VEG")
boat_meshes, boat_info = E.boats(L)
for bi in boat_info:
    m = boat_meshes[bi["id"]]
    ob = bl_io.to_object(m, bl_io.collection("BOAT"), name=bi["id"])
    ob.location = world.to_blender(bi["pos"]); ob.rotation_euler = (0, 0, math.radians(bi["yaw_deg"]))
    groups.setdefault("boats", []).append(ob); stats[bi["id"]] = m.tri_count
sea = bl_io.to_object(E.sea_preview(L), bl_io.collection("PREVIEW_ONLY"), name="LT_SEA_PREVIEW")

if EXPORT:
    for name, objs in groups.items():
        bl_io.export_glb(os.path.join(env_dir, name + ".glb"), objs)
    info["boats"] = boat_info
    info["schema"] = "living-tides.environment"; info["version"] = 1
    info["axes"] = "+x east, +y up, +z south (same as village_layout.json)"
    with open(os.path.join(ROOT, "data/environment.json"), "w") as f:
        json.dump(info, f, indent=1)

# ---- buildings in place
bt = 0
for b in L["buildings"]:
    out = building.build(b, L)
    ov = palette.building_overrides(b)
    coll = bl_io.collection("BLD_" + b["id"])
    origin, yaw = world.building_frame(b)
    root = bl_io.empty("LT_BLD_" + b["id"], coll, world.to_blender(origin), math.radians(yaw), size=0.6, kind="PLAIN_AXES")
    for name, m in out.meshes.items():
        if not m.f:
            continue
        ob = bl_io.to_object(m, coll, ov, name=f"{b['id']}_{name}", ground_shade=0.22 if name.startswith(("WALL", "BASE")) else 0.0)
        if name == "DOOR_main":
            ob.location = out.meta["door_pivot"]
        ob["lt_group"] = name
        ob.parent = root
    bt += out.tri_count
stats["buildings_total"] = bt
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "out", "village_master.blend"))
summary = dict(blender=bpy.app.version_string, seconds=round(time.time() - t0, 1), tris=stats, total_tris=sum(stats.values()),
               glb_bytes={f: os.path.getsize(os.path.join(env_dir, f)) for f in sorted(os.listdir(env_dir)) if f.endswith(".glb")})
with open(os.path.join(ROOT, "evidence/logs/build_village.json"), "w") as f:
    json.dump(summary, f, indent=1)
print("SUMMARY", json.dumps(summary))

if RENDER:
    out_dir = os.path.join(ROOT, "evidence/renders_village_v03"); os.makedirs(out_dir, exist_ok=True)
    if "--quick" in argv:
        bl_io.setup_render(scene, 960, 600, 14)
    else:
        bl_io.setup_render(scene, 1600, 1000, 48)
    bl_io.sky(scene, 44, 150, strength=1.15)
    B = world.to_blender
    VIEWS = {   # name: (camera, target, lens) in layout coords
        "V01_overview": ((62, 52, 78), (-6, 6, -2), 30),
        "V02_harbour": ((26, 9, 34), (2, 2.5, 6), 30),
        "V03_hill_west": ((14, 24, 30), (-22, 9, -6), 32),
        "V04_gate": ((58, 10, 30), (34, 6, 6), 35),
        "V08_gate_through": ((62, 5.5, 10), (35, 4.5, 8.5), 28),
        "V05_plaza_stair": ((4, 12, 14), (-14, 5, -4), 30),
        "V06_crown": ((-2, 30, -2), (-26, 16, -24), 32),
        "V07_reverse_north": ((-60, 46, -70), (-6, 6, -2), 30),
    }
    for name, (c, t, lens) in VIEWS.items():
        if views and not any(v in name for v in views):
            continue
        bl_io.camera(scene, B(c), B(t), lens=lens)
        bl_io.render(scene, os.path.join(out_dir, name + ".png"))
