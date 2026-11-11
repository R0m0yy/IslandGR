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

from livingtides import sculpt
sculpt_log = {}
island = sculpt.build_island(L, ter, sculpt_log)
groups["island"] = [island]; stats["LT_ISLAND"] = len(island.data.polygons)
add("seabed", sculpt.seabed(L), "TERRAIN")
print("ISLAND", json.dumps(sculpt_log)[:1500])
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
    # terrain height as a small texture: the Godot sea shader reads water depth
    # from it (works in every renderer; no depth-buffer tricks needed)
    import numpy as np
    lo, hi = -3.0, 1.0
    Hn = np.clip((ter.H - lo) / (hi - lo), 0, 1)[::-1]            # image rows bottom-up
    # written with a tiny PNG encoder so no colour management touches the values
    import zlib, struct
    g8 = (Hn * 255.0 + 0.5).astype(np.uint8)[::-1]                # PNG rows run top-down: north first
    raw = b"".join(b"\x00" + g8[r].tobytes() for r in range(g8.shape[0]))
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    with open(os.path.join(env_dir, "seabed_height.png"), "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", g8.shape[1], g8.shape[0], 8, 0, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))
    info_height = dict(file="seabed_height.png", x=[float(ter.xs[0]), float(ter.xs[-1])], z=[float(ter.zs[0]), float(ter.zs[-1])], h=[lo, hi])
    for name, objs in groups.items():
        bl_io.export_glb(os.path.join(env_dir, name + ".glb"), objs)
    info["boats"] = boat_info
    info["seabed_height"] = info_height
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
    root = bl_io.empty("LT_BLD_" + b["id"], coll, world.to_blender(origin), math.radians(yaw + building.visual_yaw(b, L)), size=0.6, kind="PLAIN_AXES")
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
summary = dict(island=sculpt_log.get("island"), blender=bpy.app.version_string, seconds=round(time.time() - t0, 1), tris=stats, total_tris=sum(stats.values()),
               glb_bytes={n + ".glb": os.path.getsize(os.path.join(env_dir, n + ".glb")) for n in sorted(groups) if os.path.exists(os.path.join(env_dir, n + ".glb"))})
with open(os.path.join(ROOT, "evidence/logs/build_village.json"), "w") as f:
    json.dump(summary, f, indent=1)
print("SUMMARY", json.dumps(summary))

if RENDER:
    out_dir = os.path.join(ROOT, "evidence/renders_village_v04"); os.makedirs(out_dir, exist_ok=True)
    if "--quick" in argv:
        bl_io.setup_render(scene, 960, 600, 14)
    else:
        bl_io.setup_render(scene, 1600, 1000, 36)
    TIME = "day"
    for i, a_ in enumerate(argv):
        if a_ == "--time":
            TIME = argv[i + 1]
    if TIME == "golden":
        bl_io.sky(scene, 9, 235, strength=1.25)
    elif TIME == "night":
        bl_io.sky(scene, 35, 200, night=True)
        # practicals: lit windows, street lamps, stove glow carry the image
        g = bpy.data.materials.get("LT_glass")
        if g:
            bs = g.node_tree.nodes["Principled BSDF"]
            bs.inputs["Emission Color"].default_value = (1.0, 0.72, 0.36, 1.0); bs.inputs["Emission Strength"].default_value = 4.0
        for lp in info["lamps"] + [dict(pos=x["light"]) for x in info["landmarks"] if "light" in x]:
            ld = bpy.data.lights.new("lamp", "POINT"); ld.energy = 260; ld.color = (1.0, 0.75, 0.45); ld.shadow_soft_size = 0.15
            lo = bpy.data.objects.new("lamp", ld); scene.collection.objects.link(lo); lo.location = world.to_blender(lp["pos"])
    else:
        bl_io.sky(scene, 44, 150, strength=1.15)
    suffix = "" if TIME == "day" else "_" + TIME
    B = world.to_blender
    VIEWS = {   # name: (camera, target, lens) in layout coords
        "V01_overview": ((62, 52, 78), (-6, 6, -2), 30),
        "V02_harbour": ((26, 9, 34), (2, 2.5, 6), 30),
        "V03_hill_west": ((14, 24, 30), (-22, 9, -6), 32),
        "V04_gate": ((58, 10, 30), (34, 6, 6), 35),
        "V08_gate_through": ((62, 5.5, 10), (35, 4.5, 8.5), 28),
        # representative district: west quay, stilt houses, Back Stair, working beach
        "D01_district_overview": ((16, 17, 44), (-7, 3, 17), 32),
        "D02_district_boardwalk": ((10.5, 5.0, 29.5), (-1, 2.4, 18), 30),
        "D03_district_backstair": ((2.5, 7.5, 21), (-12.5, 4.0, 14), 32),
        "D04_district_cottage": ((-2.5, 4.2, 30.5), (-9.5, 2.2, 23.5), 35),
        "D05_district_beach": ((14, 3.2, 31.5), (4, 1.0, 25.5), 30),
        "V05_plaza_stair": ((4, 12, 14), (-14, 5, -4), 30),
        "V06_crown": ((-2, 30, -2), (-26, 16, -24), 32),
        "V07_reverse_north": ((-60, 46, -70), (-6, 6, -2), 30),
    }
    for name, (c, t, lens) in VIEWS.items():
        if views and not any(v in name for v in views):
            continue
        bl_io.camera(scene, B(c), B(t), lens=lens)
        bl_io.render(scene, os.path.join(out_dir, name + suffix + ".png"))
