"""Build the four hero villagers (v2), animate them and render their evidence.

  /opt/lt/bl/bin/python blender/build_characters.py [A B C D] [--quick] [--no-anim-renders]

Per character, in evidence/characters/<key>/:
  hero.png            Cycles hero render (idle pose)
  turntable.png       8 angles, 45 deg steps
  faces.png           neutral / smile / blink / talk / frown / brows up
  hands.png, feet.png close-ups
  parts.png           every clothing piece and accessory on its own
  wireframe.png       hero mesh wireframe
  anim_<clip>.png     4 phases of every clip; anim_extreme.png clothing check
  tris.json           triangle counts per part (hero and game versions), clips
Exports:
  godot/assets/characters/<key>.glb   game version (decimated), rig, shape keys, all clips
  blender/out/characters/<key>.blend  hero source scene (with baked clips)
and evidence/characters/comparison.png (all four, same light)."""
import sys, os, json, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector
from livingtides import bl_io
from livingtides.characters import hero, cast, anim
from livingtides.characters import garments as G
from livingtides.characters import crowd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EV = os.path.join(ROOT, "evidence", "characters")
QUICK = "--quick" in sys.argv
ANIM_RENDERS = "--no-anim-renders" not in sys.argv
KEYS = [a for a in sys.argv[1:] if a in cast.SPECS or a in crowd.VARIANTS] or list(cast.SPECS)
if "--crowd" in sys.argv:
    # `--crowd` alone rebuilds every variant; `--crowd V02 V09` rebuilds just those (lineup tiles patched)
    KEYS = [a for a in sys.argv[1:] if a in crowd.VARIANTS] or list(crowd.VARIANTS)
GAME_TRIS_CROWD = 9000


def build_any(key):
    c = cast.build(key) if key in cast.SPECS else crowd.build_variant(key)
    return c
S_HERO = 12 if QUICK else 48
S_SMALL = 8 if QUICK else 16
GAME_TRIS = 13000


def montage(out, cols, files, bg=(0.72, 0.78, 0.84), remove=True):
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
    if remove:
        for f in files:
            os.remove(f)


def stage(sc, w, h, samples):
    bl_io.setup_render(sc, w, h, samples)
    bl_io.sky(sc, 38, 135)
    bpy.ops.mesh.primitive_circle_add(vertices=64, radius=2.6, fill_type="NGON", location=(0, 0, 0))
    g = bpy.context.object; g.name = "ground"
    m = bpy.data.materials.new("ground"); m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.78, 0.66, 0.46, 1)
    m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.95
    g.data.materials.append(m)
    L = bpy.data.lights.new("fill", "AREA"); L.energy = 70; L.size = 3
    lo = bpy.data.objects.new("fill", L); sc.collection.objects.link(lo)
    lo.location = (-2.5, -2.0, 2.0); lo.rotation_euler = (Vector((0, 0, 1)) - lo.location).to_track_quat("-Z", "Y").to_euler()
    R = bpy.data.lights.new("rim", "AREA"); R.energy = 90; R.size = 2
    ro = bpy.data.objects.new("rim", R); sc.collection.objects.link(ro)
    ro.location = (1.5, 2.5, 2.4); ro.rotation_euler = (Vector((0, 0, 1)) - ro.location).to_track_quat("-Z", "Y").to_euler()
    return g


def cam(sc, loc, tgt, lens):
    old = sc.camera
    c = bl_io.camera(sc, tuple(loc), tuple(tgt), lens=lens)
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


def eval_points(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    e = ob.evaluated_get(dg); me = e.to_mesh()
    P = np.array([(ob.matrix_world @ v.co)[:] for v in me.vertices]) if len(me.vertices) else np.zeros((0, 3))
    e.to_mesh_clear()
    return P


def frame_points(sc, P, lens=60, dirn=(0.35, -1.0, 0.25), pad=1.25):
    lo, hi = P.min(0), P.max(0); ctr = (lo + hi) / 2
    size = max(np.linalg.norm(hi - lo), 0.05) * pad
    d = np.array(dirn, float); d /= np.linalg.norm(d)
    dist = size / (2 * math.tan(math.atan(18 / lens)))
    return cam(sc, ctr + d * dist, ctr, lens)


def wire_overlay(c):
    mat = bpy.data.materials.new("wire"); mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.02, 0.02, 0.03, 1)
    made = []
    for n, (ob, cat) in c.parts.items():
        w = ob.copy(); w.data = ob.data.copy(); w.name = ob.name + "_wire"
        c.coll.objects.link(w)
        wm = w.modifiers.new("wire", "WIREFRAME"); wm.thickness = 0.0009; wm.use_replace = True
        w.data.materials.clear(); w.data.materials.append(mat)
        made.append(w)
    return made


def make_game_lod(c, target):
    """Decimate every part toward `target` triangles in total (face and hands keep
    proportionally more); shape keys are rebuilt from the stored expression deltas."""
    for n, (ob, cat) in c.parts.items():
        for m in ob.modifiers:
            if m.type == "ARMATURE":
                m.show_viewport = False
    tr = c.tris(); total = sum(tr.values())
    ratio = target / total
    for n, (ob, cat) in c.parts.items():
        t = tr[n]
        if t < 200:
            continue
        r = ratio * (1.25 if n == "body" else (0.6 if n in c.patterns else 1.0))
        r = min(1.0, max(r, 250 / t))
        if r >= 0.98:
            continue
        had = ob.data.shape_keys is not None
        if had:
            ob.shape_key_clear()
        hero.decimate(ob, r, sym=False)
        if had:
            hero.add_shape_keys(ob)
        if n in c.patterns:            # stripes / checks: re-slice and repaint crisp per-face colour after decimation
            cuts = c.pattern_cuts.get(n, [])
            if len(cuts) == 1:         # stripes: cheap to re-slice; two-way checks would double the triangles
                G.plane_cuts(ob, *cuts[0])
            G.paint_faces_v2(ob, c.patterns[n], smooth=True, sharp_angle=1.0)
        G.shade(ob, True, 1.0)
    for n, (ob, cat) in c.parts.items():
        for m in ob.modifiers:
            if m.type == "ARMATURE":
                m.show_viewport = True
    return c.tris()


def export_glb(c, path):
    for t in c.rig.animation_data.nla_tracks:
        t.mute = True
    c.rig.animation_data.action = None
    c._poser.reset() if getattr(c, "_poser", None) else c.rest()
    bpy.ops.object.select_all(action="DESELECT")
    objs = [c.rig] + [ob for ob, cat in c.parts.values()]
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = c.rig
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_yup=True,
                              export_skins=True, export_morph=True, export_morph_normal=False,
                              export_animations=True, export_animation_mode="NLA_TRACKS",
                              export_vertex_color="MATERIAL", export_apply=False)


def export_only(key, portrait=None):
    """Rebuild, bake and export the game GLB without renders (fast path).
    `portrait`: also render one small Cycles portrait for the crowd lineup."""
    bl_io.reset_scene()
    c = build_any(key)
    crowd.tag_tint_channel(c)
    anim.bake(c)
    anim.show(c, "idle", 0.0)
    if portrait:
        sc = bpy.context.scene
        stage(sc, 420, 760, S_SMALL * 2)
        H = c.spec["height_m"]
        cam(sc, (0.9 * H, -2.4 * H, 0.6 * H), (0, 0, 0.5 * H), 50)
        bl_io.render(sc, portrait)
    hero_tris = sum(c.tris().values())
    game_tris = make_game_lod(c, GAME_TRIS if key in cast.SPECS else GAME_TRIS_CROWD)
    gdir = os.path.join(ROOT, "godot", "assets", "characters"); os.makedirs(gdir, exist_ok=True)
    export_glb(c, os.path.join(gdir, key + ".glb"))
    tj = os.path.join(EV, key, "tris.json")
    if os.path.exists(tj):
        info = json.load(open(tj)); info["game_total_tris"] = sum(game_tris.values()); info["game_parts"] = game_tris
        json.dump(info, open(tj, "w"), indent=1)
    else:
        os.makedirs(os.path.dirname(tj), exist_ok=True)
        v = crowd.VARIANTS.get(key, {})
        json.dump({"key": key, "variant": v, "hero_total_tris": hero_tris, "game_total_tris": sum(game_tris.values()),
                   "clips": anim.clips_for(key), "height_m": c.spec["height_m"]}, open(tj, "w"), indent=1, default=str)
    print("EXPORTED", key, hero_tris, sum(game_tris.values()), flush=True)


def build_one(key):
    t0 = time.time()
    bl_io.reset_scene()
    sc = bpy.context.scene
    c = cast.build(key)
    clips = anim.bake(c)
    out = os.path.join(EV, key); os.makedirs(out, exist_ok=True)
    for f in os.listdir(out):
        os.remove(os.path.join(out, f))
    H = c.spec["height_m"]
    hero_tris = c.tris()
    anim.show(c, "idle", 0.0)
    stage(sc, 1100, 1500, S_HERO)
    # hero
    cam(sc, (1.05 * H, -2.25 * H, 0.62 * H), (0, 0, 0.52 * H), 50)
    bl_io.render(sc, os.path.join(out, "hero.png"))
    sc.cycles.samples = S_SMALL * 2
    # turntable
    sc.render.resolution_x, sc.render.resolution_y = 440, 640
    files = []
    for i in range(8):
        a = math.radians(45 * i); d = 2.5 * H
        cam(sc, (math.sin(a) * d, -math.cos(a) * d, 0.55 * H), (0, 0, 0.5 * H), 50)
        f = os.path.join(out, f"_turn_{i}.png"); bl_io.render(sc, f); files.append(f)
    montage(os.path.join(out, "turntable.png"), 4, files)
    # faces
    hc = np.array(c.pose_head()) if hasattr(c, "pose_head") else None
    hb = c.rig.pose.bones["head"]
    hc = np.array(c.rig.matrix_world @ (hb.head + (hb.tail - hb.head) * 0.42))
    sc.render.resolution_x, sc.render.resolution_y = 620, 680
    sc.cycles.samples = S_SMALL * 3
    ff = []
    for name, keys in (("neutral", {}), ("smile", {"smile": 1.0}), ("blink", {"blink": 1.0}), ("talk", {"mouth_open": 0.8, "brows_up": 0.5}),
                       ("frown", {"frown": 1.0, "brows_down": 0.6}), ("oo", {"mouth_oo": 1.0})):
        set_keys(c, **keys)
        cam(sc, hc + np.array([0.17, -0.55, 0.02]) * c.k, hc + np.array([0, 0, -0.01]) * c.k, 60)
        f = os.path.join(out, f"_face_{name}.png"); bl_io.render(sc, f); ff.append(f)
    set_keys(c)
    montage(os.path.join(out, "faces.png"), 3, ff)
    # hands and feet
    hands = []
    for s in ("l", "r"):
        P = eval_points(c.body)
        hb_ = c.rig.pose.bones[f"hand_{s}"]
        hp = np.array(c.rig.matrix_world @ hb_.tail)
        m = np.linalg.norm(P - hp, axis=1) < 0.13 * c.k
        frame_points(sc, P[m], lens=60, dirn=(1.0 if s == "l" else -1.0, -1.0, 0.3), pad=1.5)
        f = os.path.join(out, f"_hand_{s}.png"); bl_io.render(sc, f); hands.append(f)
    montage(os.path.join(out, "hands.png"), 2, hands)
    P = np.vstack([eval_points(ob) for n, (ob, cat) in c.parts.items() if cat in ("footwear", "body")])
    P = P[P[:, 2] < 0.16 * H]
    frame_points(sc, P, lens=55, dirn=(0.5, -1.0, 0.45), pad=1.15)
    sc.render.resolution_x, sc.render.resolution_y = 1000, 620
    bl_io.render(sc, os.path.join(out, "feet.png"))
    # every garment / accessory on its own
    sc.render.resolution_x, sc.render.resolution_y = 420, 420
    sc.cycles.samples = S_SMALL
    groups = {}
    for n, (ob, cat) in c.parts.items():
        if cat in ("body", "face") or n.startswith(("eye",)):
            continue
        base = n.split("_hem")[0].split("_edge")[0].split("_rim")[0]
        groups.setdefault(base, []).append(ob)
    pf = []
    allobs = [ob for ob, cat in c.parts.values()]
    for base, obs in groups.items():
        for o in allobs:
            o.hide_render = o not in obs
        P = np.vstack([eval_points(o) for o in obs])
        if len(P) == 0:
            continue
        frame_points(sc, P, lens=60, dirn=(0.4, -1.0, 0.35), pad=1.2)
        f = os.path.join(out, f"_part_{base}.png"); bl_io.render(sc, f); pf.append(f)
    for o in allobs:
        o.hide_render = False
    cols = 5 if len(pf) > 12 else 4
    montage(os.path.join(out, "parts.png"), cols, pf)
    # wireframe
    sc.render.resolution_x, sc.render.resolution_y = 1100, 1500
    sc.cycles.samples = S_SMALL * 2
    wires = wire_overlay(c)
    cam(sc, (0.9 * H, -2.35 * H, 0.6 * H), (0, 0, 0.5 * H), 50)
    bl_io.render(sc, os.path.join(out, "wireframe.png"))
    hb = c.rig.pose.bones["head"]; hc = np.array(c.rig.matrix_world @ (hb.head + (hb.tail - hb.head) * 0.42))
    sc.render.resolution_x, sc.render.resolution_y = 900, 900
    cam(sc, hc + np.array([0.25, -0.62, 0.02]) * c.k, hc + np.array([0, 0, -0.02]) * c.k, 60)
    bl_io.render(sc, os.path.join(out, "wireframe_face.png"))
    for w in wires:
        bpy.data.objects.remove(w)
    # animation frames
    if ANIM_RENDERS:
        sc.render.resolution_x, sc.render.resolution_y = 380, 520
        sc.cycles.samples = S_SMALL
        for clip in clips:
            fr = []
            for ph in (0.0, 0.25, 0.5, 0.75):
                anim.show(c, clip, ph)
                cam(sc, (1.9 * H, -2.2 * H, 0.7 * H), (0, 0, 0.45 * H), 42)
                f = os.path.join(out, f"_a_{clip}_{int(ph * 100)}.png"); bl_io.render(sc, f); fr.append(f)
            montage(os.path.join(out, f"anim_{clip}.png"), 4, fr)
        # extreme poses, closer, to check clothing
        ex = []
        for clip, ph in (("run", 0.25), ("climb_ladder", 0.0), ("sit", 0.0), (anim.JOB[key], 0.25)):
            anim.show(c, clip, ph)
            P = np.vstack([eval_points(ob) for ob, cat in c.parts.values() if cat != "held"])
            sc.render.resolution_x, sc.render.resolution_y = 520, 640
            frame_points(sc, P, lens=50, dirn=(1.0, -0.8, 0.3), pad=1.1)
            f = os.path.join(out, f"_x_{clip}.png"); bl_io.render(sc, f); ex.append(f)
        montage(os.path.join(out, "anim_extreme.png"), 4, ex)
    anim.show(c, "idle", 0.0)
    # save hero source, then the game version + export
    os.makedirs(os.path.join(ROOT, "blender", "out", "characters"), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "blender", "out", "characters", key + ".blend"))
    game_tris = make_game_lod(c, GAME_TRIS)
    gdir = os.path.join(ROOT, "godot", "assets", "characters"); os.makedirs(gdir, exist_ok=True)
    export_glb(c, os.path.join(gdir, key + ".glb"))
    info = {"key": key, "title": c.spec["title"], "height_m": H,
            "hero_total_tris": sum(hero_tris.values()), "hero_parts": hero_tris,
            "game_total_tris": sum(game_tris.values()), "game_parts": game_tris,
            "body_faces_removed_under_clothing": c.removed_faces,
            "shape_keys": [kb.name for kb in c.body.data.shape_keys.key_blocks[1:]] if c.body.data.shape_keys else [],
            "bones": len(c.rig.data.bones), "clips": clips, "missing_targets": c.info["missing_targets"],
            "seconds": round(time.time() - t0, 1)}
    json.dump(info, open(os.path.join(out, "tris.json"), "w"), indent=1)
    print("BUILT", json.dumps({k: info[k] for k in ("key", "hero_total_tris", "game_total_tris", "seconds")}), flush=True)
    return info


if __name__ == "__main__":
    os.makedirs(EV, exist_ok=True)
    if "--export-only" in sys.argv or "--crowd" in sys.argv:
        ports = []
        for k in KEYS:
            pth = os.path.join(EV, "crowd", f"_p_{k}.png") if "--crowd" in sys.argv else None
            if pth:
                os.makedirs(os.path.dirname(pth), exist_ok=True)
            export_only(k, pth)
            if pth:
                ports.append(pth)
        allp = [os.path.join(EV, "crowd", f"_p_{k}.png") for k in crowd.VARIANTS]
        if ports and all(os.path.exists(f) for f in allp):
            montage(os.path.join(EV, "crowd", "lineup.png"), 7, allp, remove=False)   # portraits kept (git-ignored)
        sys.exit(0)
    only_cmp = "--comparison-only" in sys.argv
    infos = [] if only_cmp else [build_one(k) for k in KEYS]
    if only_cmp:
        infos = [json.load(open(os.path.join(EV, k, "tris.json"))) for k in cast.SPECS]
    if set(KEYS) == set(cast.SPECS) or only_cmp:
        bl_io.reset_scene(); sc = bpy.context.scene
        xs = {"A": -1.35, "B": -0.45, "C": 0.45, "D": 1.3}
        for k in KEYS:
            c = cast.build(k)
            c.rig.location.x = xs[k]
        stage(sc, 2200, 1200, S_HERO)
        cam(sc, (0.6, -5.6, 1.15), (0, 0, 0.82), 42)
        bl_io.render(sc, os.path.join(EV, "comparison.png"))
        json.dump(infos, open(os.path.join(EV, "summary.json"), "w"), indent=1)
