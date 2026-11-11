"""The only module that talks to Blender.  Converts geom.Mesh objects into
Blender objects (vertex colour attribute `Col`, a handful of shared
materials), manages collections, and exports GLB."""
from __future__ import annotations
import bpy
import bmesh
import numpy as np
from . import palette


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.unit_settings.system = "METRIC"
    return s


def collection(name, parent=None):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(c)
    return c


def material(name):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    col = nt.nodes.new("ShaderNodeVertexColor"); col.layer_name = "Col"
    nt.links.new(col.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.9
    if name == "LT_metal":
        bsdf.inputs["Roughness"].default_value = 0.58
        bsdf.inputs["Metallic"].default_value = 0.25
    elif name == "LT_glass":
        bsdf.inputs["Roughness"].default_value = 0.12
        bsdf.inputs["Metallic"].default_value = 0.1
    elif name == "LT_water":
        bsdf.inputs["Roughness"].default_value = 0.08
    elif name.startswith("LT_emit_"):
        nt.links.new(col.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = 6.0 if name.endswith("fire") else 8.0
    return m


def to_object(mesh, coll, overrides=None, name=None, origin=None, ground_shade=0.0):
    """geom.Mesh -> bpy object.  origin: subtract this point so it becomes the
    object's pivot.  ground_shade: darken vertex colour toward local z=0."""
    name = name or mesh.name
    V = np.asarray(mesh.v, dtype=np.float64).reshape(-1, 3)
    if origin is not None:
        V = V - np.asarray(origin, dtype=np.float64)
    me = bpy.data.meshes.new(name)
    me.from_pydata(V.tolist(), [], mesh.f)
    me.update()
    # consistent outward normals per closed island
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    mats, mat_index = [], {}
    cache = {}
    attr = me.color_attributes.new("Col", "FLOAT_COLOR", "CORNER")
    cols = np.empty((len(me.loops), 4), dtype=np.float32)
    zs = V[:, 2]
    li = 0
    for poly, role, tint in zip(me.polygons, mesh.fm, mesh.ft):
        mn = palette.material_of(role)
        if mn not in mat_index:
            mat_index[mn] = len(mats); mats.append(mn); me.materials.append(material(mn))
        poly.material_index = mat_index[mn]
        if role not in cache:
            cache[role] = palette.resolve(role, overrides)
        r, g, b = (min(1.0, c * tint) for c in cache[role])
        lr, lg, lb = palette.srgb_to_linear((r, g, b))
        for vi in poly.vertices:
            k = 1.0
            if ground_shade:
                k = 1.0 - ground_shade * max(0.0, 1.0 - zs[vi] / 0.9) ** 1.5
            cols[li] = (lr * k, lg * k, lb * k, 1.0); li += 1
    attr.data.foreach_set("color", cols.ravel())
    me.color_attributes.active_color = attr
    me.color_attributes.render_color_index = 0
    ob = bpy.data.objects.new(name, me)
    if origin is not None:
        ob.location = origin
    coll.objects.link(ob)
    return ob


def empty(name, coll, loc, rot_z=0.0, size=0.25, parent=None, kind="ARROWS"):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = kind; e.empty_display_size = size
    e.location = loc; e.rotation_euler = (0, 0, rot_z)
    coll.objects.link(e)
    if parent is not None:
        e.parent = parent
    return e


def export_glb(path, objects):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_apply=True,
                              export_yup=True, export_extras=True, export_vertex_color="MATERIAL",
                              export_materials="EXPORT", export_cameras=False, export_lights=False)


# ------------------------------------------------------------------ rendering
def setup_render(scene, w=1280, h=720, samples=48):
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 4
    scene.render.resolution_x, scene.render.resolution_y = w, h
    scene.render.threads_mode = "AUTO"
    scene.view_settings.view_transform = "AgX" if "AgX" in [i.identifier for i in bpy.types.ColorManagedViewSettings.bl_rna.properties["view_transform"].enum_items] else "Filmic"
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass


def sky(scene, sun_elev_deg=42, sun_rot_deg=140, strength=1.0, night=False):
    import math
    w = bpy.data.worlds.new("LT_sky"); scene.world = w; w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes["Background"]
    if night:
        bg.inputs["Color"].default_value = (0.012, 0.02, 0.05, 1); bg.inputs["Strength"].default_value = 1.0
    else:
        tex = nt.nodes.new("ShaderNodeTexSky")
        try:
            tex.sky_type = "NISHITA"
            tex.sun_elevation = math.radians(sun_elev_deg); tex.sun_rotation = math.radians(sun_rot_deg)
            tex.sun_disc = False
            bg.inputs["Strength"].default_value = 0.22 * strength
        except Exception:
            bg.inputs["Strength"].default_value = 1.0
        # camera sees a calm flat sky; lighting still comes from the sky model
        mix = nt.nodes.new("ShaderNodeMixRGB"); lp = nt.nodes.new("ShaderNodeLightPath")
        mix.inputs["Color2"].default_value = (2.6, 3.6, 4.6, 1.0)
        nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs["Fac"])
        nt.links.new(tex.outputs["Color"], mix.inputs["Color1"])
        nt.links.new(mix.outputs["Color"], bg.inputs["Color"])
    sun = bpy.data.lights.new("LT_sun", "SUN")
    sun.energy = 0.25 if night else 4.2 * strength
    sun.color = (0.55, 0.65, 1.0) if night else ((1.0, 0.93, 0.82) if sun_elev_deg > 20 else (1.0, 0.62, 0.36))
    sun.angle = math.radians(3.0)
    so = bpy.data.objects.new("LT_sun", sun); scene.collection.objects.link(so)
    # sun_rot: compass direction the light comes FROM, measured like the sky texture
    az = math.radians(sun_rot_deg); el = math.radians(sun_elev_deg)
    d = (math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el))     # toward the sun
    import mathutils
    so.rotation_euler = mathutils.Vector(d).to_track_quat("Z", "Y").to_euler()
    return so


def camera(scene, loc, target, lens=35, name="LT_cam"):
    import mathutils
    cam = bpy.data.cameras.new(name); cam.lens = lens; cam.clip_end = 2000
    ob = bpy.data.objects.new(name, cam); scene.collection.objects.link(ob)
    ob.location = loc
    d = mathutils.Vector(target) - mathutils.Vector(loc)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    scene.camera = ob
    return ob


def render(scene, path):
    scene.render.filepath = path
    scene.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)
