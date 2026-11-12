"""Wildlife reference sheet + GLB for Godot.

  /opt/lt/bl/bin/python blender/build_animals.py [--quick]
Writes evidence/animals/reference_sheet.png, evidence/animals/<key>.png,
evidence/animals/animals.json, godot/assets/env/animals.glb"""
import sys, os, json, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector
from livingtides import bl_io, animals

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EV = os.path.join(ROOT, "evidence", "animals"); os.makedirs(EV, exist_ok=True)
QUICK = "--quick" in sys.argv
bl_io.reset_scene(); sc = bpy.context.scene
coll = sc.collection
A = animals.build_all(coll)
for k, a in A.items():                       # cell size from the real bounding box
    a["frame"] = max(a["object"].dimensions)
# export (real size, each at origin) before arranging
bpy.ops.object.select_all(action="DESELECT")
for k, a in A.items():
    a["object"].select_set(True)
bpy.context.view_layer.objects.active = A["gull"]["object"]
os.makedirs(os.path.join(ROOT, "godot", "assets", "env"), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=os.path.join(ROOT, "godot", "assets", "env", "animals.glb"), export_format="GLB",
                          use_selection=True, export_yup=True, export_vertex_color="MATERIAL", export_apply=True)
bl_io.setup_render(sc, 1000, 760, 16 if QUICK else 48)
bl_io.sky(sc, 45, 140)
mat = bpy.data.materials.new("label"); mat.use_nodes = True
mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.06, 0.08, 0.1, 1)
# individual close renders
for k, a in A.items():
    ob = a["object"]
    for o in A.values():
        o["object"].hide_render = o["object"] is not ob
    s = a["frame"]
    ob.rotation_euler = (0, 0, math.radians(-35))
    zc = 0.15 * s
    cam = bl_io.camera(sc, (0.95 * s, -1.55 * s, 0.75 * s + zc), (0, 0, zc * 0.6), lens=50)
    bl_io.render(sc, os.path.join(EV, k + ".png"))
    bpy.data.objects.remove(cam)
for o in A.values():
    o["object"].hide_render = False
# sheet: 4 x 3 grid, each normalised to one cell, with name + real length
cols = 4
for i, (k, a) in enumerate(A.items()):
    ob = a["object"]; s = 0.82 / a["frame"]
    r, c = divmod(i, cols)
    ob.scale = (s, s, s)
    ob.location = (c * 1.15 - 1.72, 0, -r * 1.22 + 1.2)
    ob.rotation_euler = (0, 0, math.radians(-32))
    cu = bpy.data.curves.new("lbl_" + k, "FONT"); cu.body = f"{a['title']}\n{a['length_m']:.2f} m  ·  {a['tris']} tris"
    cu.size = 0.07; cu.align_x = "CENTER"
    t = bpy.data.objects.new("lbl_" + k, cu); coll.objects.link(t)
    t.location = (c * 1.15 - 1.72, -0.45, -r * 1.22 + 0.78); t.rotation_euler = (math.radians(68), 0, 0)
    t.data.materials.append(mat)
cam = bl_io.camera(sc, (0, -8, 3.4), (0, 0, 0.18), lens=50)
cam.data.type = "ORTHO"; cam.data.ortho_scale = 5.0
sc.render.resolution_x, sc.render.resolution_y = 2000, 1600
bl_io.render(sc, os.path.join(EV, "reference_sheet.png"))
json.dump({k: {kk: v for kk, v in a.items() if kk != "object"} for k, a in A.items()}, open(os.path.join(EV, "animals.json"), "w"), indent=1)
print("ANIMALS", {k: a["tris"] for k, a in A.items()})
