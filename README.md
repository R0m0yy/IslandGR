# LIVING TIDES

Autonomous coastal-village life simulation. Working title. New production project.

**Read `PROOF_OF_WORK.md` first.** It separates what exists and was executed from what is only planned.

## Layout
| Path | Contents |
|---|---|
| `assets/glb/` | Exported geometry (glTF binary) |
| `blender/` | Blender scripts and (once Blender runs) `.blend` sources |
| `engine/` | Session-1 test viewer (kept). The game engine will be Godot 4; no Godot project exists yet |
| `village/` | Layout data, tests and the temporary massing generator |
| `data/` | `village_layout.json` — the layout contract for Blender and Godot |
| `tools/preview/` | Preview renderer for massing captures (not the game engine) |
| `tools/` | Generators, capture and verification scripts |
| `evidence/renders/` | Genuine captures from the 3D scene |
| `evidence/logs/` | Command output backing each claim |
| `tests/` | Empty. No simulation exists yet |
| `*.md` | Project documents (see `PROGRESS.md` for which are written) |

## Reproduce the current evidence
```
python3 tools/gen_test_vignette.py assets/glb/lt_pipeline_test_01.glb
python3 tools/verify_glb.py assets/glb/lt_pipeline_test_01.glb
python3 tools/capture.py        # needs Chrome + playwright; writes evidence/renders/*.png
```

## Village massing (session 2)
```
python3 village/test_layout.py      # layout + route tests, exit 1 on failure
python3 village/gen_massing.py      # writes data/village_layout.json and the two village GLBs
python3 tools/capture_village.py    # writes evidence/renders_village/*.png
```
