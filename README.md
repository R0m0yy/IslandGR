# LIVING TIDES

Autonomous coastal-village life simulation. Working title. New production project.

**Read `PROOF_OF_WORK.md` first.** It separates what exists and was executed from what is only planned.

## Status at a glance (session 4)
See `QA_REPORT.md` for the audit and `PROOF_OF_WORK.md` for evidence. The environment is **not approved**; characters are **frozen** (neutral mannequins).

### Session 3 summary
A Blender 4.x asset pipeline and a Godot 4 project now exist and **have been executed** (Blender 4.5.15 LTS via `bpy`, Godot 4.3 headless + software-GL captures). The whole 30-building village is generated from `data/village_layout.json`, loads in Godot, and 42 placeholder villagers live in it autonomously in the headless tests. Never run: a GPU, the Forward+ renderer, an interactive session. See `PROOF_OF_WORK.md`.

## Layout
| Path | Contents |
|---|---|
| `data/village_layout.json` | **Single source of truth** (session 2, unchanged): terraces, 30 buildings, households, businesses, walk graph |
| `data/buildings/<ID>.json` | Generated: interaction anchors + interior walk graph per building |
| `data/environment.json`, `data/dev_population.json` | Generated lamp / boat / landmark placements; PLACEHOLDER villagers |
| `village/` | Layout source (`layout.py`), layout tests, session-2 massing generator |
| `blender/livingtides/` | Asset pipeline (pure Python + one Blender bridge module) |
| `blender/build_buildings.py`, `build_village.py` | Entry scripts: build, export GLB, save `.blend`, render |
| `godot/` | Godot 4.3 project: `scenes/`, `scripts/`, `shaders/`, `assets/`, `data/` (copy), `tests/` |
| `tools/` | `test_pipeline.py`, `gen_population.py`, `sync_godot_data.py`, `package.sh`; session 1-2 tools |
| `assets/glb/`, `engine/`, `tools/preview/` | Session 1-2 outputs and viewers (kept) |
| `evidence/` | Renders and logs backing each claim |
| `*.md` | Project documents; start with `PROOF_OF_WORK.md` and `PROGRESS.md` |

## Rebuild everything
```
# one-time: Blender as a Python module (needs Python 3.11)
uv venv -p python3.11 .venv && uv pip install -p .venv/bin/python "bpy>=4.2,<5" numpy

python3 village/test_layout.py                      # layout + route tests
.venv/bin/python blender/build_buildings.py         # 30 building GLBs + anchor sidecars
.venv/bin/python blender/build_village.py --render  # environment GLBs + village_master.blend + renders
python3 tools/gen_population.py                     # placeholder villagers
python3 tools/sync_godot_data.py                    # copy data into the Godot project
python3 tools/test_pipeline.py                      # 16 checks, no Blender needed

cd godot
godot --headless --import                           # first time only
godot --headless res://tests/test_runner.tscn -- --days=5 --out=$PWD/../evidence/logs/godot_tests.json
godot                                               # open / play (UNVERIFIED: never run with a GPU)
bash ../tools/package.sh                            # dist/living-tides-<date>.zip
```

## Sessions 1-2 (kept)
### Reproduce the session-1 evidence
```
python3 tools/gen_test_vignette.py assets/glb/lt_pipeline_test_01.glb
python3 tools/verify_glb.py assets/glb/lt_pipeline_test_01.glb
python3 tools/capture.py        # needs Chrome + playwright; writes evidence/renders/*.png
```

### Village massing (session 2)
```
python3 village/test_layout.py      # layout + route tests, exit 1 on failure
python3 village/gen_massing.py      # writes data/village_layout.json and the two village GLBs
python3 tools/capture_village.py    # writes evidence/renders_village/*.png
```
