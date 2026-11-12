"""Build the four hero villagers and their evidence set.

  /opt/lt/bl/bin/python blender/build_characters.py [A B C D] [--quick]

Writes per character:
  evidence/characters/<key>/hero.png            Cycles hero render
  evidence/characters/<key>/turntable.png       8 angles (45 deg steps) in one sheet
  evidence/characters/<key>/face_*.png          neutral / smile / blink close-ups + sheet
  evidence/characters/<key>/wireframe.png       wireframe over flat colour
  evidence/characters/<key>/tris.json           triangle counts per part
  godot/assets/characters/<key>.glb             rigged, shape keys, game version
  blender/out/characters/<key>.blend            source scene
and evidence/characters/comparison.png with all four side by side."""
import sys, os, json, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector
from livingtides import bl_io
from livingtides.characters import hero, cast

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EV = os.path.join(ROOT, "evidence", "characters")
QUICK = "--quick" in sys.argv
KEYS = [a for a in sys.argv[1:] if a in cast.SPECS] or list(cast.SPECS)
SAMPLES = 16 if QUICK else 40


def montage(out, cols, files, bg=(0.72, 0.78, 0.84)):
    ims = []
    for f in files:
        im = bpy.data.images.load(f); w, h = im.size
        ims.append(np.array(im.pixels[:]).reshape(h, w, 4)); bpy.data.images.remove(im)
    H = max(a.shape[0] for a in ims); W = max(a.shape[1] for a in ims)
    rows = (len(ims) + cols - 1) // cols
    cv = np.ones((rows * H, cols * W, 4)); cv[..., :3] = bg
    for i, a in enumerate(ims):
        r = rows - 1 - i // cols; c = i % cols
        cv[r * H:r * H + a.shape[0], c * W:c * W + a.shape[1]] = a
    img = bpy.data.images.new("montage", cols * W, rows * H, alpha=True)
    img.pixels[:] = cv.ravel(); img.filepath_raw = out; img.file_format = "PNG"; img.save()
    bpy.data.images.remove(img)


def stage(sc, w, h):
    bl_io.setup_render(sc, w, h, SAMPLES)
    sc.render.film_transparent = False
    bl_io.sky(sc, 38, 135)
    # sand-coloured ground disc so the figure is grounded
    bpy.ops.mesh.primitive_circle_add(vertices=48, radius=2.2, fill_type="NGON", location=(0, 0, 0))
    g = bpy.context.object; g.name = "ground"
    m = bpy.data.materials.new("ground"); m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.78, 0.66, 0.46, 1)
    m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.95
    g.data.materials.append(m)
    # soft fill from the shadow side
    L = bpy.data.lights.new("fill", "AREA"); L.energy = 60; L.size = 3
    lo = bpy.data.objects.new("fill", L); sc.collection.objects.link(lo)
    lo.location = (-2.5, -2.0, 2.0); lo.rotation_euler = (Vector((0, 0, 1)) - lo.location).to_track_quat("-Z", "Y").to_euler()


def cam(sc, loc, tgt, lens):
    old = sc.camera
    c = bl_io.camera(sc, loc, tgt, lens=lens)
    if old is not None and old != c:
        bpy.data.objects.remove(old)
    return c


def set_keys(c, **vals):
    for n, (ob, cat) in c.parts.items():
        sk = ob.data.shape_keys if ob.type == "MESH" else None
        if not sk:
            continue
        for kb in sk.key_blocks[1:]:
            kb.value = vals.get(kb.name, 0.0)


def wire_overlay(c):
    mat = bpy.data.materials.new("wire"); mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.02, 0.02, 0.03, 1)
    made = []
    for n, (ob, cat) in c.parts.items():
        w = ob.copy(); w.data = ob.data.copy(); w.name = ob.name + "_wire"
        c.coll.objects.link(w)
        wm = w.modifiers.new("wire", "WIREFRAME"); wm.thickness = 0.0016; wm.use_replace = True
        w.data.materials.clear(); w.data.materials.append(mat)
        made.append(w)
    return made


def build_one(key):
    t0 = time.time()
    bl_io.reset_scene()
    sc = bpy.context.scene
    c = cast.build(key)
    out = os.path.join(EV, key); os.makedirs(out, exist_ok=True)
    H = c.spec["height_m"]
    tris = c.tris()
    total = sum(tris.values())
    # crowd LOD estimate: decimate everything to ~4k as one pass (evaluated only, for the count)
    lod = 0
    dg = bpy.context.evaluated_depsgraph_get()
    ratio = min(1.0, 4000 / total)
    for n, (ob, cat) in c.parts.items():
        m = ob.modifiers.new("lod", "DECIMATE"); m.ratio = ratio
        dg = bpy.context.evaluated_depsgraph_get(); me = ob.evaluated_get(dg).to_mesh()
        lod += sum(len(p.vertices) - 2 for p in me.polygons); ob.evaluated_get(dg).to_mesh_clear()
        ob.modifiers.remove(m)
    info = {"key": key, "title": c.spec["title"], "height_m": H, "total_tris": total, "parts": tris,
            "crowd_lod_tris_estimate": lod, "body_faces_removed_under_clothing": c.removed_faces,
            "shape_keys": [kb.name for kb in c.body.data.shape_keys.key_blocks[1:]],
            "bones": len(c.rig.data.bones), "missing_targets": c.info["missing_targets"]}
    json.dump(info, open(os.path.join(out, "tris.json"), "w"), indent=1)
    stage(sc, 1000, 1400)
    # hero
    cam(sc, (1.1 * H, -2.3 * H, 0.62 * H), (0, 0, 0.5 * H), 50)
    bl_io.render(sc, os.path.join(out, "hero.png"))
    # turntable: rotate the rig (all parts follow)
    sc.render.resolution_x, sc.render.resolution_y = 420, 620
    files = []
    for i in range(8):
        a = math.radians(45 * i)
        d = 2.6 * H
        cam(sc, (math.sin(a) * d, -math.cos(a) * d, 0.55 * H), (0, 0, 0.5 * H), 50)
        f = os.path.join(out, f"turn_{i * 45:03d}.png"); bl_io.render(sc, f); files.append(f)
    montage(os.path.join(out, "turntable.png"), 4, files)
    for f in files:
        os.remove(f)
    # faces
    hc = c.info["head_c"]
    sc.render.resolution_x, sc.render.resolution_y = 640, 640
    ff = []
    for name, keys in (("neutral", {}), ("smile", {"smile": 1.0}), ("blink", {"blink": 1.0}), ("talk", {"mouth_open": 0.8, "brows_up": 0.6})):
        set_keys(c, **keys)
        cam(sc, tuple(hc + np.array([0.2, -0.62, 0.02])), tuple(hc + np.array([0, 0, -0.03])), 60)
        f = os.path.join(out, f"face_{name}.png"); bl_io.render(sc, f); ff.append(f)
    set_keys(c)
    montage(os.path.join(out, "faces.png"), 4, ff)
    # wireframe
    sc.render.resolution_x, sc.render.resolution_y = 1000, 1400
    wires = wire_overlay(c)
    cam(sc, (0.9 * H, -2.4 * H, 0.6 * H), (0, 0, 0.5 * H), 50)
    bl_io.render(sc, os.path.join(out, "wireframe.png"))
    for w in wires:
        bpy.data.objects.remove(w)
    # save + export
    os.makedirs(os.path.join(ROOT, "blender", "out", "characters"), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "blender", "out", "characters", key + ".blend"))
    gdir = os.path.join(ROOT, "godot", "assets", "characters"); os.makedirs(gdir, exist_ok=True)
    c.rest()
    objs = [c.rig] + [ob for ob, cat in c.parts.values()]
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = c.rig
    bpy.ops.export_scene.gltf(filepath=os.path.join(gdir, key + ".glb"), export_format="GLB", use_selection=True,
                              export_yup=True, export_skins=True, export_morph=True, export_animations=False,
                              export_vertex_color="MATERIAL", export_apply=False)
    info["seconds"] = round(time.time() - t0, 1)
    print("BUILT", json.dumps({k: info[k] for k in ("key", "total_tris", "crowd_lod_tris_estimate", "seconds")}))
    return info


if __name__ == "__main__":
    os.makedirs(EV, exist_ok=True)
    infos = [build_one(k) for k in KEYS]
    if set(KEYS) == set(cast.SPECS):
        # comparison: all four side by side in one scene, same light and camera
        bl_io.reset_scene(); sc = bpy.context.scene
        xs = {"A": -1.35, "B": -0.45, "C": 0.45, "D": 1.3}
        for k in KEYS:
            c = cast.build(k)
            c.rig.location.x = xs[k]
        stage(sc, 2000, 1100)
        cam(sc, (0.6, -5.6, 1.15), (0, 0, 0.82), 42)
        bl_io.render(sc, os.path.join(EV, "comparison.png"))
    json.dump(infos, open(os.path.join(EV, "summary.json"), "w"), indent=1)
