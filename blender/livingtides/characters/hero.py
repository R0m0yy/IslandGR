"""Hero villager builder: MakeHuman CC0 body -> stylised, faceted, rigged game
character with facial shape keys, modelled clothing, hair clumps and props.

Everything here is our own code working on the CC0 MakeHuman data read by mh.py.
Coordinates are Blender metres, Z up, character faces -Y. Character left = +X.

Data flow
  spec -> morph full-res body (macro + detail targets) -> stylise (bigger head,
  hands) -> per-vertex attributes (bone weights, expression deltas, region masks)
  -> decimate (Blender keeps attributes and vertex groups) -> clothes are shells
  cut from the decimated body, so they inherit weights and stay fitted ->
  body faces under clothing are deleted -> props / hair -> one armature from the
  shared game_engine rig definition (the child's is the same rig at child joints).
"""
from __future__ import annotations
import math
import numpy as np
import bpy, bmesh
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from . import mh
from .. import palette

BONES = list(mh.weights().keys())
BI = {b: i for i, b in enumerate(BONES)}

# shape key name -> list of (expression unit, weight)
EXPRESSIONS = {
    "blink":      [("eye-left-closure", 1.0), ("eye-right-closure", 1.0)],
    "blink_L":    [("eye-left-closure", 1.0)],
    "blink_R":    [("eye-right-closure", 1.0)],
    "smile":      [("mouth-corner-puller", 1.0), ("mouth-elevation", 0.25), ("eye-left-slit", 0.25), ("eye-right-slit", 0.25)],
    "frown":      [("mouth-depression", 0.9), ("eyebrows-left-down", 0.6), ("eyebrows-right-down", 0.6)],
    "brows_up":   [("eyebrows-left-up", 1.0), ("eyebrows-right-up", 1.0)],
    "brows_down": [("eyebrows-left-down", 1.0), ("eyebrows-right-down", 1.0)],
    "mouth_open": [("mouth-open", 0.8)],         # talking: A / jaw
    "mouth_oo":   [("mouth-pursing", 0.8), ("mouth-protusion", 0.5)],
    "mouth_ee":   [("mouth-retraction", 0.8), ("mouth-open", 0.15)],
    "mouth_mbp":  [("mouth-compression", 1.0)],
    "mouth_fv":   [("mouth-eversion", 0.6), ("mouth-open", 0.1)],
}

REGION_TARGETS = {
    "lips": ["mouth/mouth-upperlip-volume-incr", "mouth/mouth-lowerlip-volume-incr"],
    "lip_upper": ["mouth/mouth-upperlip-volume-incr"],
    "nose": ["nose/nose-volume-incr"],
    "nostrils": ["nose/nose-flaring-incr"],
    "brows": ["eyebrows/eyebrows-trans-up"],
    "cheeks": ["cheek/l-cheek-volume-incr", "cheek/r-cheek-volume-incr"],
    "eyebags": ["eyes/l-eye-bag-incr", "eyes/r-eye-bag-incr"],
    "lids": ["expression/units/caucasian/eye-left-closure", "expression/units/caucasian/eye-right-closure"],
    "ears": ["ears/l-ear-scale-incr", "ears/r-ear-scale-incr"],
    "chin": ["chin/chin-prominent-incr"],
    "jaw": ["chin/chin-width-incr"],
    "laugh": ["mouth/mouth-laugh-lines-in"],
    "forehead": ["head/head-age-incr"],
}

KEEP_GROUPS = {"body", "helper-upper-teeth", "helper-lower-teeth", "helper-tongue",
               "helper-l-eyelashes-2", "helper-r-eyelashes-2"}   # upper lashes only


# ------------------------------------------------------------------ colours
def rgb(h):
    if isinstance(h, (tuple, list)):
        return tuple(h)
    h = palette.BIBLE.get(h, h)
    return palette.hex_to_srgb(h)


def jitter(c, rng, amt=0.04):
    f = 1.0 + rng.uniform(-amt, amt)
    return tuple(min(1.0, max(0.0, v * f)) for v in c)


def mix(a, b, t):
    return tuple(x * (1 - t) + y * t for x, y in zip(a, b))


# ------------------------------------------------------------------ morph
def morph(spec):
    """Full-resolution body in Blender space plus expression deltas and joints."""
    V0, F, FG, VG = mh.base()
    W = mh.macro_targets(spec)
    for k, v in spec.get("detail", {}).items():
        W[k] = W.get(k, 0.0) + v
    miss = []
    V = mh.apply_targets(V0, W, miss)
    expr = {}
    for key, units in EXPRESSIONS.items():
        D = np.zeros_like(V)
        for u, w in units:
            D += mh.expression_delta(u, spec["race"], len(V)) * w
        expr[key] = D
    Vb = mh.to_blender(V)
    exprb = {k: mh.to_blender(V + d) - Vb for k, d in expr.items()}
    return Vb, F, FG, VG, exprb, miss


def dense_weights(n):
    W = np.zeros((n, len(BONES)))
    for j, b in enumerate(BONES):
        for i, w in mh.weights()[b]:
            if i < n:
                W[i, j] = w
    s = W.sum(1, keepdims=True)
    return W / np.maximum(s, 1e-9)


def stylise(Vb, exprb, Wd, spec):
    """Enlarge head (5-head adult, 4-head child), hands and feet a little, then
    scale to the requested height. Applied as a per-vertex similarity so the
    expression deltas scale with their region."""
    J = mh.joint_positions(Vb)
    k = np.ones(len(Vb))
    piv = np.zeros_like(Vb)
    out = Vb.copy()

    def grow(bones, pivot, s):
        w = sum(Wd[:, BI[b]] for b in bones)
        w = np.clip(w, 0, 1)
        f = 1 + (s - 1) * w
        return w, f

    # head (neck half-weighted so the neck widens smoothly into the jaw)
    neck = J["joint-neck"]
    wh = np.clip(Wd[:, BI["head"]] + 0.55 * Wd[:, BI["neck_01"]], 0, 1)
    fh = 1 + (spec["head_scale"] - 1) * wh
    out = neck + (out - neck) * fh[:, None]
    scale_expr = fh.copy()
    for side in ("l", "r"):
        hb = [f"hand_{side}"] + [f"{f}_{n:02d}_{side}" for f in ("thumb", "index", "middle", "ring", "pinky") for n in (1, 2, 3)]
        w = np.clip(sum(Wd[:, BI[b]] for b in hb), 0, 1)
        p = J[f"joint-{side}-hand"]
        f = 1 + (spec.get("hand_scale", 1.12) - 1) * w
        out = p + (out - p) * f[:, None]
        scale_expr *= f
        fb = [f"foot_{side}", f"ball_{side}"]
        w = np.clip(sum(Wd[:, BI[b]] for b in fb), 0, 1)
        p = J[f"joint-{side}-ankle"]
        f = 1 + (spec.get("foot_scale", 1.06) - 1) * w
        out = p + (out - p) * f[:, None]
    # overall height
    body_idx = np.unique(np.concatenate([np.array(f) for f, g in zip(mh.base()[1], mh.base()[2]) if g == "body"]))
    zmin, zmax = out[body_idx, 2].min(), out[body_idx, 2].max()
    s = spec["height_m"] / (zmax - zmin)
    out = (out - np.array([0, 0, zmin])) * s
    ex = {k2: d * (scale_expr[:, None] * s) for k2, d in exprb.items()}
    return out, ex, s


# ------------------------------------------------------------------ blender mesh helpers
def mesh_from(name, V, F, coll):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in V], [], [tuple(f) for f in F])
    me.update()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


def get_co(me):
    a = np.zeros(len(me.vertices) * 3)
    me.vertices.foreach_get("co", a)
    return a.reshape(-1, 3)


def set_co(me, V):
    me.vertices.foreach_set("co", np.asarray(V, dtype=np.float64).ravel())
    me.update()


def put_vec_attr(me, name, arr):
    a = me.attributes.new(name, "FLOAT_VECTOR", "POINT")
    a.data.foreach_set("vector", np.asarray(arr, dtype=np.float64).ravel())


def get_vec_attr(me, name):
    a = np.zeros(len(me.vertices) * 3)
    me.attributes[name].data.foreach_get("vector", a)
    return a.reshape(-1, 3)


def put_float_attr(me, name, arr):
    a = me.attributes.new(name, "FLOAT", "POINT")
    a.data.foreach_set("value", np.asarray(arr, dtype=np.float64).ravel())


def get_float_attr(me, name):
    a = np.zeros(len(me.vertices))
    me.attributes[name].data.foreach_get("value", a)
    return a


def set_groups(ob, Wd, thresh=0.01):
    """Write a dense (n, bones) weight array as vertex groups (top 4 per vertex)."""
    ob.vertex_groups.clear()
    vgs = [ob.vertex_groups.new(name=b) for b in BONES]
    top = np.argsort(-Wd, axis=1)[:, :4]
    for i in range(len(Wd)):
        row = Wd[i, top[i]]
        s = row.sum()
        if s <= 0:
            continue
        for j, w in zip(top[i], row / s):
            if w > thresh:
                vgs[j].add([i], float(w), "REPLACE")


def read_groups(ob):
    n = len(ob.data.vertices)
    W = np.zeros((n, len(BONES)))
    names = {g.index: g.name for g in ob.vertex_groups}
    for v in ob.data.vertices:
        for g in v.groups:
            b = names.get(g.group)
            if b in BI:
                W[v.index, BI[b]] = g.weight
    s = W.sum(1, keepdims=True)
    return W / np.maximum(s, 1e-9)


def decimate(ob, ratio, vgroup=None, factor=1.0, sym=True, invert=False):
    m = ob.modifiers.new("dec", "DECIMATE")
    m.ratio = ratio
    m.use_collapse_triangulate = True
    m.use_symmetry = sym
    m.symmetry_axis = "X"
    if vgroup:
        m.vertex_group = vgroup
        m.vertex_group_factor = factor
        m.invert_vertex_group = invert
    dg = bpy.context.evaluated_depsgraph_get()
    nm = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    ob.modifiers.remove(m)
    old = ob.data
    ob.data = nm
    bpy.data.meshes.remove(old)
    # vertex groups survive on the mesh; object group names are unchanged
    return ob


def tri_count(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


# ------------------------------------------------------------------ body
def build_body(spec, coll):
    Vb, F, FG, VG, exprb, miss = morph(spec)
    n = len(Vb)
    Wd = dense_weights(n)
    Vs, ex, s = stylise(Vb, exprb, Wd, spec)
    J = {k: v for k, v in mh.joint_positions(Vs).items()}
    keepF = [f for f, g in zip(F, FG) if g in KEEP_GROUPS]
    fgroup = [g for g in FG if g in KEEP_GROUPS]
    used = np.unique(np.concatenate([np.array(f) for f in keepF]))
    remap = -np.ones(n, dtype=np.int64)
    remap[used] = np.arange(len(used))
    F2 = [tuple(remap[list(f)]) for f in keepF]
    ob = mesh_from(spec["name"] + "_body", Vs[used], F2, coll)
    me = ob.data
    # per-face part tag for colouring (body / teeth / tongue) as a face attribute
    tag = me.attributes.new("part", "INT", "FACE")
    tag.data.foreach_set("value", [0 if g == "body" else (1 if "teeth" in g else (3 if "eyelash" in g else 2)) for g in fgroup])
    for k, d in ex.items():
        put_vec_attr(me, "ex_" + k, d[used])
    put_vec_attr(me, "rest", Vs[used])
    set_groups(ob, Wd[used])
    # density: keep the face (and hands) much denser than the body
    face_w = np.clip(Wd[used, BI["head"]] * 1.0, 0, 1)
    hand_w = np.clip(sum(Wd[used, BI[b]] for b in BONES if any(b.startswith(f) for f in ("thumb", "index", "middle", "ring", "pinky", "hand"))), 0, 1)
    dens = ob.vertex_groups.new(name="_density")
    for i in range(len(used)):
        dens.add([i], float(spec.get("body_density", 0.3) + (1 - spec.get("body_density", 0.3)) * max(face_w[i], 0.8 * hand_w[i])), "REPLACE")
    # soft region masks taken from the MakeHuman detail targets (which vertices each target moves)
    masks = {}
    for name, rels in REGION_TARGETS.items():
        m = np.zeros(n)
        for rel in rels:
            t = mh.target(rel)
            if t is None:
                continue
            idx, d = t
            mag = np.linalg.norm(d, axis=1)
            if mag.max() > 0:
                m[idx] = np.maximum(m[idx], mag / mag.max())
        masks[name] = m[used]
        put_float_attr(me, "mask_" + name, m[used])
    eyes = {}
    for side in ("l", "r"):
        idx = VG[f"helper-{side}-eye"]
        c = Vs[idx].mean(axis=0)
        eyes[side] = (c, float(np.linalg.norm(Vs[idx] - c, axis=1).mean()))
    head_idx = used[Wd[used, BI["head"]] > 0.95]
    hc = Vs[head_idx].mean(axis=0)
    info = {"joints": J, "scale": s, "missing_targets": miss, "full_res_tris": sum(len(f) - 2 for f in F2),
            "V_full": Vs, "used": used, "masks": masks, "bones": mh.bone_positions(Vs), "eyes": eyes, "head_c": hc,
            "head_r": float(np.percentile(np.linalg.norm(Vs[head_idx] - hc, axis=1), 90)),
            "mouth": Vs[VG["joint-mouth"]].mean(axis=0) if "joint-mouth" in VG else J.get("joint-mouth")}
    return ob, info


def lod_body(ob, head_tris=3200, body_tris=4600):
    """Two decimation passes with explicit budgets. Blender's decimate treats a
    vertex-group weight of 1 as 'collapse first' and 0 as 'keep', so pass 1
    reduces the body while the head is protected, pass 2 the reverse."""
    W = read_groups(ob)
    headv = (W[:, BI["head"]] + 0.5 * W[:, BI["neck_01"]]) > 0.5
    g = ob.vertex_groups["_density"]

    def counts():
        Wn = read_groups(ob)
        hv = (Wn[:, BI["head"]] + 0.5 * Wn[:, BI["neck_01"]]) > 0.5
        h = sum(len(p.vertices) - 2 for p in ob.data.polygons if hv[list(p.vertices)].mean() > 0.5)
        return h, tri_count(ob) - h

    h0, b0 = counts()
    for i in range(len(W)):
        g.add([i], 0.0 if headv[i] else 1.0, "REPLACE")
    decimate(ob, min(1.0, (h0 + body_tris) / (h0 + b0)), vgroup="_density", factor=1.0, invert=False)
    h1, b1 = counts()
    g = ob.vertex_groups["_density"]
    W = read_groups(ob)
    headv = (W[:, BI["head"]] + 0.5 * W[:, BI["neck_01"]]) > 0.5
    for i in range(len(W)):
        g.add([i], 1.0 if headv[i] else 0.0, "REPLACE")
    decimate(ob, min(1.0, (head_tris + b1) / (h1 + b1)), vgroup="_density", factor=1.0, invert=False)
    ob.vertex_groups.remove(ob.vertex_groups["_density"])
    return counts()


def body_arrays(ob):
    me = ob.data
    P = get_co(me)
    W = read_groups(ob)
    return P, W


# ------------------------------------------------------------------ shape keys
def add_shape_keys(ob, keys=EXPRESSIONS.keys(), source=None):
    """Turn ex_* attributes into shape keys. `source` (ob, map) lets clothing or
    beards copy deltas from their nearest skin vertex."""
    me = ob.data
    if me.shape_keys is None:
        ob.shape_key_add(name="Basis", from_mix=False)
    P = get_co(me)
    for k in keys:
        if source is None:
            if "ex_" + k not in me.attributes:
                continue
            D = get_vec_attr(me, "ex_" + k)
        else:
            sP, sD = source
            D = sD[k][nearest_idx(sP, P)]
        if np.abs(D).max() < 1e-6:
            continue
        sk = ob.shape_key_add(name=k, from_mix=False)
        sk.data.foreach_set("co", (P + D).ravel())
    return ob


def nearest_idx(src, pts):
    from mathutils.kdtree import KDTree
    kd = KDTree(len(src))
    for i, p in enumerate(src):
        kd.insert(p, i)
    kd.balance()
    return np.array([kd.find(Vector(p))[1] for p in pts], dtype=np.int64)


# ------------------------------------------------------------------ armature
def build_armature(name, J_body_mesh_full, coll):
    """J_body_mesh_full: the stylised full-res vertex array (for bone_positions)."""
    bp = mh.bone_positions(J_body_mesh_full)
    arm = bpy.data.armatures.new(name + "_rig")
    ob = bpy.data.objects.new(name + "_rig", arm)
    coll.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.edit_bones
    for bname, (h, t, roll, parent) in bp.items():
        b = eb.new(bname)
        b.head = Vector(h); b.tail = Vector(t)
        if (b.tail - b.head).length < 1e-4:
            b.tail = b.head + Vector((0, 0, 0.02))
        b.roll = roll
    for bname, (h, t, roll, parent) in bp.items():
        if parent:
            eb[bname].parent = eb[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    arm.display_type = "STICK"
    return ob


def bind(ob, rig):
    ob.parent = rig
    m = ob.modifiers.new("rig", "ARMATURE")
    m.object = rig
    return ob


def attach_to_bone(ob, rig, bone):
    """Rigidly attach a prop to a bone (keeps its current world transform)."""
    mw = ob.matrix_world.copy()
    ob.parent = rig
    ob.parent_type = "BONE"
    ob.parent_bone = bone
    bpy.context.view_layer.update()
    ob.matrix_world = mw
    return ob


# ------------------------------------------------------------------ vertex colours
def paint(ob, face_colours):
    """face_colours: list of rgb per polygon -> corner colour attribute 'Col'."""
    me = ob.data
    if len(me.polygons) == 0:
        return ob
    if "Col" in me.color_attributes:
        me.color_attributes.remove(me.color_attributes["Col"])
    ca = me.color_attributes.new("Col", "FLOAT_COLOR", "CORNER")
    cols = np.zeros((len(me.loops), 4))
    for p in me.polygons:
        c = face_colours[p.index]
        lin = palette.srgb_to_linear(c)
        for li in p.loop_indices:
            cols[li] = (*c, 1.0)
    ca.data.foreach_set("color_srgb", cols.ravel()) if hasattr(ca.data[0], "color_srgb") else ca.data.foreach_set("color", cols.ravel())
    me.color_attributes.active_color = ca
    for p in me.polygons:
        p.use_smooth = False
    return ob


def face_centres(ob):
    me = ob.data
    c = np.zeros(len(me.polygons) * 3)
    me.polygons.foreach_get("center", c)
    return c.reshape(-1, 3)


def face_normals(ob):
    me = ob.data
    c = np.zeros(len(me.polygons) * 3)
    me.polygons.foreach_get("normal", c)
    return c.reshape(-1, 3)


def face_vert_mean(ob, arr):
    me = ob.data
    return np.array([arr[list(p.vertices)].mean(axis=0) for p in me.polygons])


# ------------------------------------------------------------------ material
def char_material():
    m = bpy.data.materials.get("LT_char")
    if m:
        return m
    m = bpy.data.materials.new("LT_char")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    vc = nt.nodes.new("ShaderNodeVertexColor"); vc.layer_name = "Col"
    nt.links.new(vc.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.78
    try:
        bsdf.inputs["Specular IOR Level"].default_value = 0.25
    except KeyError:
        pass
    return m


def char_material_gloss():
    m = bpy.data.materials.get("LT_char_gloss")
    if m:
        return m
    m = char_material().copy(); m.name = "LT_char_gloss"
    m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.22
    return m


def char_material_metal():
    m = bpy.data.materials.get("LT_char_metal")
    if m:
        return m
    m = char_material().copy(); m.name = "LT_char_metal"
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.3; b.inputs["Metallic"].default_value = 0.9
    return m


def assign(ob, mat=None):
    ob.data.materials.clear()
    ob.data.materials.append(mat or char_material())
    return ob
