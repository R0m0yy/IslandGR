# HOW TO TEST LIVING TIDES

## 1. Play the village (needs Godot 4.3, any desktop, ideally a GPU)
1. Unzip, open **`godot/project.godot`** in Godot 4.3 (Forward+ is the default; if your machine has no Vulkan, run with `--rendering-method gl_compatibility`).
2. Press Play. The village loads from `godot/data/` and `godot/assets/` (all included).
3. Controls: RMB orbit · wheel zoom · WASD pan · Q/E rotate · LMB select resident/boat/building · Tab next resident · G follow household · B boat · N wildlife · K cinematic · T timeline · F family tree · J journal · I village inspector · C cutaway · V show/hide the grey placeholder figures · H hide UI · 1-4 speed (x1 x4 x16 x60) · Space pause · F5 save / F9 load.
4. **None of this has been operated by a person yet** (see PROOF_OF_WORK.md). Please report anything that looks wrong or feels dead.

### iPad / touch controls
Drag with one finger to move the map · pinch to zoom · twist two fingers to rotate · slide two fingers up/down to tilt · tap a resident, boat or building to select it (tap empty ground to release). A button bar appears at the bottom on touch devices (pause, speed, village, journal, follow modes, save/load, hide UI). Test: `godot/tests/touch_test.tscn` (21 checks, log in `evidence/logs/touch_test.log`).

## 2. Run the automated tests (headless)
```
cd godot
godot --headless --import
godot --headless res://tests/test_runner.tscn -- --days=7 --gen-days=45
godot --headless res://tests/living_world_test.tscn -- --only=A,B,C,D,E,F,G
godot --headless res://tests/living_world_test.tscn -- --only=Y          # one year
godot --headless res://tests/living_world_test.tscn -- --only=P --years=90
```
Last recorded results: scenarios A-G 47/47, one year 9/9, 90 years 5/5, regression 56/57. Logs: `evidence/logs/`.

## 3. Look at the evidence without running anything
`evidence/renders_godot_v05/` (in-engine frames + 12 s clip), `evidence/renders_village_v04/` and `evidence/renders_buildings/` (Blender Cycles).

## 4. Rebuild the assets (optional; Blender as a Python module)
```
uv venv -p python3.11 .venv && uv pip install -p .venv/bin/python "bpy>=4.2,<5" numpy
.venv/bin/python blender/build_buildings.py
.venv/bin/python blender/build_village.py
python3 tools/sync_godot_data.py && python3 tools/test_pipeline.py
```

## 5. Hero villagers (session 6) - FIRST PASS, AWAITING APPROVAL
Four characters built: A fisher captain, B market vendor, C elder net-mender, D harbour child.
Rebuild everything (renders, GLBs, .blend):
```
/opt/lt/bl/bin/python blender/build_characters.py          # all four, ~10 min on 2 CPUs
/opt/lt/bl/bin/python blender/build_characters.py A --quick # one character, low samples
/opt/lt/bl/bin/python blender/build_animals.py               # wildlife sheet + animals.glb
```
Look at `evidence/characters/comparison.png`, then each `evidence/characters/<A-D>/` (hero, turntable, faces, wireframe, tris.json) and `evidence/animals/reference_sheet.png`.
Not yet done: animations, Godot placement, per-garment close-ups, the crowd LOD export. The game still shows the grey placeholder residents.
