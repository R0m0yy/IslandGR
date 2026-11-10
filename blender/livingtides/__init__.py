"""Living Tides asset pipeline.

Pure-Python modules (geom, field, parts, archetypes, environment) never import
bpy, so they are unit-testable anywhere.  Only `bl_io` and the entry scripts
in blender/ touch Blender.
"""
__version__ = "0.1.0"
