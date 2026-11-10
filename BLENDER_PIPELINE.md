# BLENDER PIPELINE

## Feasibility result — session 1: FAILED (tool unavailable)
| Check | Result |
|---|---|
| Blender installed | No (`blender: NOT FOUND`) |
| Version | n/a |
| Background rendering | Not tested |
| Blender Python | `import bpy` → ModuleNotFoundError |
| GLB export from Blender | Not tested |
| Install attempt | `pip download bpy` refused: session network settings block package installs |
| CPU / GPU | 2 cores, 8 GB RAM, no GPU |

Log: `evidence/logs/environment_check.log`.

## Route to a working Blender leg
The `bpy` Python wheel is Blender as a module and runs headless with Cycles on CPU. With installs allowed: `pip install bpy`, then `blender/import_render_test.py` (written, **not executed**) imports the test GLB, saves a `.blend`, re-exports GLB and renders a Cycles still. Whether the wheel matches this machine's Python 3.13 is unverified. With 2 CPU cores and no GPU, expect Cycles stills to take minutes each; EEVEE needs a GL context and may not work headless here.

## Stop-gap used in session 1
`tools/gen_test_vignette.py` writes glTF binary directly with numpy. Output is ordinary mesh data that Blender's glTF importer accepts in principle (not yet tried). It lacks modifiers, collections, UVs and pivots, and it is the wrong tool for sculptural forms like cliffs.

## Intended production conventions (to apply once Blender runs)
- Units metres, Y-forward/Z-up in Blender, +Y up in glTF. Apply transforms before export.
- Collections: `TERRAIN`, `CLIFFS`, `BLD_<id>`, `ROOF`, `DOOR`, `WINDOW`, `STAIR`, `LADDER`, `BRIDGE`, `DOCK`, `BOAT`, `FISHING`, `FURN`, `VEG`, `WILDLIFE`, `LIGHT`, `DECO`, `INTERACT`, `COL` (collision), `NAV`.
- Naming: `LT_<category>_<name>_<variant>`; collision `UCX_` prefix; interaction anchors as empties `IA_<object>_<slot>` carrying stand position and facing.
- Pivots: doors at hinge, shutters at hinge, lids at hinge, boats at waterline centre, buildings at front-door threshold.
- Modules built with Array (planks, roof sheets, stairs, railings) and Mirror; Geometry Nodes only for scatter (foliage, pebbles). Cliffs and hero buildings are shaped by hand.
- One `.blend` per building family plus `village_master.blend` linking them. One GLB per prefab.
- Vertex colour attribute `Col`; second attribute for wind weight on foliage.
