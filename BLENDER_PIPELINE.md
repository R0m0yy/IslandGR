# BLENDER PIPELINE

## Session 3 status: OPERATIONAL (executed with bpy 4.5.15 LTS, Python 3.11, CPU)
```
uv venv -p python3.11 .venv && uv pip install -p .venv/bin/python "bpy>=4.2,<5" numpy
.venv/bin/python blender/build_buildings.py [--only H01,P05] [--render]   # 30 GLBs + sidecars + buildings.blend
.venv/bin/python blender/build_village.py   [--render] [--quick] [--views V01,V02]   # env GLBs + village_master.blend
python3 tools/sync_godot_data.py && python3 tools/test_pipeline.py
```
The same scripts are written to run as `blender -b -P blender/build_village.py -- --render` in the Blender application; **that invocation is UNVERIFIED** (no application binary here).

### Structure
| Module | Role | Needs bpy |
|---|---|---|
| `livingtides/geom.py` | Mesh builder: transform stack, boxes, beams, prisms, lathes, displaced icospheres, per-face tint | no |
| `livingtides/parts.py` | Kit of parts: walls with true openings, plank cladding, tin / tile roofs (gable, hip, shed), windows, shutters, doors, balconies, stairs, floors, awnings, pergola, footings | no |
| `livingtides/furniture.py` | One model per anchor type in the layout (28 types) | no |
| `livingtides/building.py` | Layout record → building: family choice, openings, wall groups, roof, features, interior placement, anchors, interior walk graph, sidecar JSON | no |
| `livingtides/environment.py` | Terrain, cliffs, The Gate, stairs, ladder, bridge, decks, paving, boats, lamps, landmarks, vegetation | no |
| `livingtides/world.py`, `palette.py` | Layout access, axis conventions, colour roles (art-bible palette) | no |
| `livingtides/bl_io.py` | Mesh → Blender object with `Col` vertex colours and shared materials; collections; GLB export; Cycles setup | **yes** |

Because only `bl_io.py` and the two entry scripts import `bpy`, the generators are unit-tested without Blender (`tools/test_pipeline.py`).

### Rules the generators follow
- Data first: nothing is placed, moved or resized in Blender. Footprints, doors, colours, storeys and anchor lists come from `data/village_layout.json`.
- Walkable ground is sacred: inside keep-out zones (walk links, plots, decks, stair corridors) the terrain equals the surveyed height. Irregularity is added only outside them.
- Conventions from the section below are applied: metres, `LT_` names, collections `TERRAIN`, `CLIFFS`, `BLD_<id>`, `STAIR`, `BOAT`, `VEG`, `DECO`; anchors as empties `IA_<object>_<slot>`; door pivot at the hinge; building pivot at the front-door threshold; vertex colour attribute `Col`.
- Deviations: modifiers (Array/Mirror) are not used - geometry is emitted directly; no UVs (no textures); no `UCX_` collision meshes yet.

---
## Earlier record (sessions 1-2)

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
