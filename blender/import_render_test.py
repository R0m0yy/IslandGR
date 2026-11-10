# STATUS: WRITTEN, NOT EXECUTED. Blender was not available in the session that wrote this file.
# Run when Blender (or the `bpy` wheel) exists:  blender -b -P blender/import_render_test.py
# Purpose: prove the Blender leg of the pipeline - import GLB, save .blend, re-export GLB, render with Cycles.
import bpy, os
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=os.path.join(root, 'assets/glb/lt_pipeline_test_01.glb'))
print('BLENDER', bpy.app.version_string, 'objects', len(bpy.data.objects))
sun = bpy.data.objects.new('Key', bpy.data.lights.new('Key', 'SUN')); sun.data.energy = 4; sun.rotation_euler = (0.9, 0, -0.7); bpy.context.scene.collection.objects.link(sun)
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); cam.data.type = 'ORTHO'; cam.data.ortho_scale = 24
cam.location = (40, -40, 38); cam.rotation_euler = (0.995, 0, 0.785); bpy.context.scene.collection.objects.link(cam); bpy.context.scene.camera = cam
s = bpy.context.scene; s.render.engine = 'CYCLES'; s.cycles.samples = 64; s.render.resolution_x = s.render.resolution_y = 1200
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(root, 'blender/lt_pipeline_test_01.blend'))
bpy.ops.export_scene.gltf(filepath=os.path.join(root, 'assets/glb/lt_pipeline_test_01_from_blender.glb'))
s.render.filepath = os.path.join(root, 'evidence/renders/blender_cycles_test.png'); bpy.ops.render.render(write_still=True)
