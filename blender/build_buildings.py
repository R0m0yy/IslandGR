"""Build every building in data/village_layout.json.

    blender -b -P blender/build_buildings.py -- [--only H01,P05] [--render] [--no-export]
    (or)  python blender/build_buildings.py ...   with the `bpy` module installed

Writes   godot/assets/buildings/<ID>.glb      one prefab per building, pivot = door threshold
         data/buildings/<ID>.json             anchors + interior walk graph (Godot-local)
         blender/out/buildings.blend          all buildings laid out at their village positions
         evidence/renders_buildings/*.png     with --render
"""
import sys, os, json, math, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import bpy
from livingtides import world, building, bl_io, palette
from livingtides.geom import Mesh

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
only = None
for i, a in enumerate(argv):
    if a == "--only":
        only = set(argv[i + 1].split(","))
RENDER = "--render" in argv
EXPORT = "--no-export" not in argv

L = world.load()
scene = bl_io.reset_scene()
os.makedirs(os.path.join(ROOT, "godot/assets/buildings"), exist_ok=True)
os.makedirs(os.path.join(ROOT, "data/buildings"), exist_ok=True)
os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
log = []
t0 = time.time()
for b in L["buildings"]:
    if only and b["id"] not in only:
        continue
    out = building.build(b, L)
    ov = palette.building_overrides(b)
    coll = bl_io.collection("BLD_" + b["id"])
    origin, yaw = world.building_frame(b)
    root = bl_io.empty("LT_BLD_" + b["id"], coll, world.to_blender(origin), math.radians(yaw), size=0.6, kind="PLAIN_AXES")
    root["lt_id"] = b["id"]; root["lt_kind"] = b["kind"]; root["lt_family"] = building.family_of(b)
    objs = [root]
    for name, m in out.meshes.items():
        if not m.f:
            continue
        piv = out.meta.get("door_pivot") if name == "DOOR_main" else None
        if piv:
            # leaf mesh is authored at its hinge; place the hinge
            ob = bl_io.to_object(m, coll, ov, name=f"{name}")
            ob.location = piv
        else:
            ob = bl_io.to_object(m, coll, ov, name=f"{name}", ground_shade=0.22 if name.startswith(("WALL", "BASE")) else 0.0)
        ob.name = f"{b['id']}_{name}"; ob["lt_group"] = name
        ob.parent = root
        objs.append(ob)
    for a in out.anchors:
        fx = a["facing"] or (0, 1)
        e = bl_io.empty(f"{b['id']}_{a['id']}", coll, a["stand"] or a["pos"], math.atan2(fx[1], fx[0]) - math.pi / 2, parent=root, size=0.2)
        e["lt_type"] = a["type"]; e["lt_pose"] = a["pose"] or ""
        objs.append(e)
    sc = building.sidecar(out, L)
    with open(os.path.join(ROOT, "data/buildings", b["id"] + ".json"), "w") as f:
        json.dump(sc, f, indent=1)
    if EXPORT:
        # export in the local frame: pivot at the threshold, no world transform
        loc, rot = root.location.copy(), root.rotation_euler.copy()
        root.location = (0, 0, 0); root.rotation_euler = (0, 0, 0)
        bpy.context.view_layer.update()
        path = os.path.join(ROOT, "godot/assets/buildings", b["id"] + ".glb")
        bl_io.export_glb(path, objs)
        root.location, root.rotation_euler = loc, rot
        size = os.path.getsize(path)
    else:
        size = 0
    log.append(dict(id=b["id"], family=sc["family"], tris=out.tri_count, anchors=len(out.anchors),
                    stubs=len(b["interior"]["anchors"]), unplaced=len(out.unplaced), glb_bytes=size, features=sc["features"]))
    print("built", b["id"], sc["family"], out.tri_count, "tris", size, "bytes", flush=True)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "out", "buildings.blend"))
summary = dict(blender=bpy.app.version_string, seconds=round(time.time() - t0, 1), buildings=log,
               total_tris=sum(x["tris"] for x in log), anchors=sum(x["anchors"] for x in log),
               stubs=sum(x["stubs"] for x in log), unplaced=sum(x["unplaced"] for x in log))
os.makedirs(os.path.join(ROOT, "evidence/logs"), exist_ok=True)
if not only:
    with open(os.path.join(ROOT, "evidence/logs/build_buildings.json"), "w") as f:
        json.dump(summary, f, indent=1)
print("SUMMARY", json.dumps({k: v for k, v in summary.items() if k != "buildings"}))

if RENDER:
    import mathutils
    out_dir = os.path.join(ROOT, "evidence/renders_buildings"); os.makedirs(out_dir, exist_ok=True)
    bl_io.setup_render(scene, 1280, 800, 40)
    bl_io.sky(scene, 40, 150)
    gm = Mesh("ground"); gm.box(-200, -200, -0.5, 200, 200, 0.0, "ground")
    ground = bl_io.to_object(gm, scene.collection)
    for b in L["buildings"]:
        if only and b["id"] not in only:
            continue
        coll = bpy.data.collections["BLD_" + b["id"]]
        root = bpy.data.objects["LT_BLD_" + b["id"]]
        for c in bpy.data.collections:
            if c.name.startswith("BLD_"):
                c.hide_render = c.name != coll.name
        saved = root.location.copy(), root.rotation_euler.copy()
        root.location = (0, 0, 0); root.rotation_euler = (0, 0, 0)
        W, D, H = b["front"], b["depth"], b["storeys"] * 2.4 + 2
        r = max(W, D) * 1.55 + H * 0.5
        bl_io.camera(scene, (r * 0.72, -r * 0.95, H * 0.62 + 1.2), (0, D * 0.4, H * 0.36), lens=32)
        bl_io.render(scene, os.path.join(out_dir, f"{b['id']}_exterior.png"))
        # cutaway: hide roof + the two camera-facing walls (front and right in this view)
        cmp_ = world.compass(b)
        hidden = []
        for o in coll.objects:
            g = o.get("lt_group", "")
            if g in ("ROOF", "WALL_" + cmp_["front"], "WALL_" + cmp_["right"], "FLOOR2"):
                o.hide_render = True; hidden.append(o)
        bl_io.camera(scene, (r * 0.6, -r * 0.8, H * 0.9 + 2.5), (0, D * 0.45, 0.8), lens=32)
        bl_io.render(scene, os.path.join(out_dir, f"{b['id']}_cutaway.png"))
        for o in hidden:
            o.hide_render = False
        root.location, root.rotation_euler = saved
