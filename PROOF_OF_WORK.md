# PROOF OF WORK — live scorecard

Statuses: **PASSED** (executed, evidence on disk) · **FAILED** (tested, defect found) · **UNVERIFIED** · **NOT IMPLEMENTED**.
Last update: 2026-11-09, session 2. Session 1 record is preserved unchanged below the line.

## Session 2 — corrective directive

### Headline
- **M1 is NOT approved and is not claimed.** What exists is a **temporary massing model** of the whole village plus the layout data and tests behind it. Every building is a box with a slab roof.
- **Blender and Godot still cannot run here.** Re-checked: PyPI, GitHub and blender.org are all blocked from this session (`evidence/logs/environment_check_session2.log`). See `ENVIRONMENT_REQUIREMENTS.md` for exactly what is needed.
- **Engine decision changed to Godot 4** (`ENGINE_EVALUATION.md` v2). Not yet executed.
- Session-1 files are untouched: `lt_pipeline_test_01.glb`, its scripts, renders and logs.

### Scorecard for this deliverable
| Requirement | Status | Evidence | Problems | Next action |
|---|---|---|---|---|
| Operational Blender pipeline | **FAILED** | `evidence/logs/environment_check_session2.log` | Network policy blocks every install route | Owner enables installs; new chat |
| Engine running | NOT IMPLEMENTED | — | Godot not installable here | Same |
| Engine decision | PASSED (document) | `ENGINE_EVALUATION.md` v2 | Desk evaluation only | First Godot spike |
| Village layout as data | PASSED | `village/layout.py`, `data/village_layout.json` (30 buildings, 8 land levels, 122 nav nodes, 126 links) | Regular stepped terraces; tidy rows | Owner review; break up rows and cliff edges |
| Layout + navigation tests | PASSED (after 2 fixes) | `evidence/logs/layout_test.json`; first failing run kept as `layout_test_run1_FAILED.json` | Run 1 FAILED (mooring under a deck); a zero-length link found next; both fixed, test added | Re-run on every layout change |
| All doors mutually reachable | PASSED | 435 of 435 door pairs routed; mean 48.2 m, longest 119.3 m | Graph-level only: no collision, navmesh or character | Bake navmesh in Godot and compare |
| Route redundancy | PASSED with 1 exception | same log | Crown Stair is the only way to the crown cottage | Design decision pending |
| Full-village model on disk | PASSED (as **temporary massing**) | `assets/glb/village_massing_v02.glb` — 3,087,828 bytes, 141 named objects, 27,720 triangles, 0 degenerate; `evidence/logs/verify_village_glb.log` | Scripted boxes; not Blender; no UVs/collision | Replace with modelled assets, hero buildings first |
| 1. Overview with all districts | PASSED (massing) | `evidence/renders_village/V01_overview_day.png` | — | — |
| 2. Residential hillside close-up | PASSED (massing) | `V04_residential_hillside_day.png` | — | — |
| 3. Fishing harbour close-up | PASSED (massing) | `V05_harbour_day.png`, `V09_harbour_night.png` | Stray white block on one boat (misplaced cabin) | Fix |
| 4. Complete route network | PASSED | `V06_route_network.png`, `V07_route_network_plan.png` (yellow walk, red stair, magenta ladder, cyan bridge, green ramp, blue boat boarding, blue dots doors) | Diagram overlay drawn on top of everything | — |
| 5–7. Day, sunset, night | PASSED (static presets) | `V01`, `V02_overview_sunset.png`, `V03_overview_night.png` | Presets, not a time-of-day system; all windows lit at once | M7 |
| Landmark arch | PASSED (massing) | `V08_gate_arch_and_bridge_day.png` | First render showed the arch filled solid (generator bug); fixed and re-rendered | Hand-model in Blender |
| Capture integrity | PASSED | `evidence/logs/capture_village_log.json` — 9 views, 0 GL errors, 0 console errors | Software WebGL preview renderer, **not the game engine** | In-engine captures from Godot |
| Visual quality vs reference | **FAILED** (below reference, as expected for massing) | See below | — | Production modelling after approvals |
| Living-world hooks per building | PASSED (data stubs) | `BUILDING_CONTRACT.md`; households, businesses, jobs, 368 interaction-anchor stubs, state fields in the JSON | All anchor positions null; no simulation reads them | Fill during M3 |
| Interiors, AI, animation, fishing, economy, relationships, weather, save/load, performance | NOT IMPLEMENTED / UNVERIFIED | — | Unchanged from session 1 | Later milestones |

### Massing vs reference — where it stands
| Category | Rating | Note |
|---|---|---|
| Overall composition | Approaching | Village mass, harbour and landmark read at a glance; tile is uniform and under-dramatic |
| Village silhouette | Below | Stepped pyramid; needs a leaning, undercut profile |
| House architecture | Below | Boxes |
| Roof geometry | Below | Flat slabs, two types |
| Colour harmony | Approaching | Palette holds together across 30 buildings; terrace tops too pale and dominant |
| Cliff modelling / rock formations | Below | Extruded steps with strata bands; arch is a slab on two blocks |
| Harbour design | Approaching | Piers, slip, stilt row, spit, moorings in sensible relation |
| Ocean appearance | Below | Static facets |
| Architectural layering | Approaching | Five levels, visible overlap from the default camera |
| Walkways and stairs | Approaching | Complete, tested network; forms are placeholders |
| Vegetation, details, materials, atmosphere | Below | Sparse placeholders |
| Lighting / shadows | Approaching | Same preview lighting as session 1; night reads well as a lamp-lit village |
| Visual depth, camera framing | Approaching | Good stacking; subject fills the frame |

Nothing is comparable to the reference. This is a layout for approval, not art for approval.

### Evidence package (session 2)
- **A. Source:** `village/lt_mesh.py`, `village/layout.py`, `village/gen_massing.py`, `village/test_layout.py`, `tools/preview/viewer2.html`, `tools/capture_village.py`, `data/village_layout.json`, `assets/glb/village_massing_v02.glb`, `assets/glb/village_nav_overlay_v02.glb`.
- **B. Visual:** `evidence/renders_village/V01`–`V09` (1200×1200).
- **C. Technical:** `evidence/logs/environment_check_session2.log`, `layout_test.json`, `layout_test_run1_FAILED.json`, `layout_test_stdout.log`, `verify_village_glb.log`, `capture_village_log.json`.
- **D. Functional:** layout and route tests only. No gameplay exists.
- **E. Limitations:** all of the above marked FAILED, UNVERIFIED or NOT IMPLEMENTED; `KNOWN_ISSUES.md`.
- Reproduce: `python3 village/test_layout.py && python3 village/gen_massing.py && python3 tools/capture_village.py`

---

# Session 1 record (unchanged)

Statuses: **PASSED** (executed, evidence on disk) · **FAILED** (tested, defect found) · **UNVERIFIED** · **NOT IMPLEMENTED**.
Last update: 2026-11-09, session 1.

## The headline
- **Blender has not been used. It cannot run in this session** (not installed; package installs are refused by the session's network settings). No `.blend` file exists. Nothing here is a Blender render.
- **No game engine has been run.** Godot, Unity and three.js are all absent and cannot be installed here.
- What does exist: one small 3D test scene written to a real `.glb` by a Python script, re-opened and validated, and rendered through real WebGL2 in headless Chrome. It is a **pipeline test, not village art and not submitted for visual approval**.
- No simulation, AI, animation, navigation, interiors, economy, audio or save/load code exists.

## Milestone M0 — research and feasibility
| Requirement | Status | Evidence | Problems | Next action |
|---|---|---|---|---|
| Original-artwork research | PASSED (partial) | `REFERENCE_RESEARCH.md` | Behance, ArtStation and Dribbble pages could not be opened directly; findings come from the 80 Level article (read in full) and search-result excerpts of the others | Re-read the three pages when reachable; Dribbble palette values still unread |
| Reference image analysis | PASSED | `REFERENCE_RESEARCH.md` §3, `ART_BIBLE.md` | Analysis of the one attached image only | — |
| Blender feasibility | **FAILED** | `evidence/logs/environment_check.log` | `blender` not found, `bpy` not importable, `pip download bpy` refused | Allow package installs in network settings, start a new chat, run `blender/import_render_test.py` |
| Engine recommendation | PASSED (document) | `ENGINE_EVALUATION.md` | No engine was executed, so the comparison is desk research | Owner approval of engine |
| Art bible | PASSED (document) | `ART_BIBLE.md` | Awaiting approval | Owner approval of direction |
| Village layout | PASSED (document) | `WORLD_LAYOUT.md` | Not yet blocked out in 3D | Blockout after approval |
| Technical architecture + sim spec | PASSED (document) | `ARCHITECTURE.md`, `VILLAGER_AI.md` | No code | Implement at M4 |
| Asset inventory | PASSED (first pass) | `ASSET_MANIFEST.md` | Hero set only; per-room interiors not itemised yet | Extend before M3 |
| Schedule + risk register | PASSED (document) | `MILESTONES.md` | — | — |

## System scorecard
| Requirement | Status | Evidence | Problems | Next action |
|---|---|---|---|---|
| Blender environment | FAILED | `evidence/logs/environment_check.log` | Not installable here | See above |
| Editable 3D geometry on disk | PASSED | `assets/glb/lt_pipeline_test_01.glb` (639,336 bytes, 60 named objects, 5,546 triangles, 0 degenerate), `evidence/logs/verify_glb.log` | Authored by script, not in Blender; no UVs, no collision meshes, pivots at world origin | Import into Blender, set pivots, save `.blend` |
| File re-opens | PASSED | `tools/verify_glb.py` (independent parser) and the WebGL viewer both load it from disk | Not yet opened in Blender or a glTF validator | Open in Blender |
| Real renders captured | PASSED | `evidence/renders/01`–`07`, `evidence/logs/capture_log.json` (0 GL errors, 0 shader errors) | Software rasteriser; one harmless 404 for a favicon | — |
| Visual reference comparison | **FAILED** (below reference) | `ART_BIBLE.md` §8 | One cottage on one rock versus a ~22-building village; see itemised gaps | Build M1 properly after approvals |
| Editable buildings | UNVERIFIED | One cottage exists as 19 named parts | Never opened in a DCC tool | — |
| Functional interiors | NOT IMPLEMENTED | — | Cottage has a floor and four walls, nothing inside | M3 |
| Navigation | NOT IMPLEMENTED | — | Test ladder visibly clips through the cliff | M2 |
| Autonomous AI | NOT IMPLEMENTED | — | Specification only | M4 |
| Character animation | NOT IMPLEMENTED | — | No characters, rigs or clips | M4/M9 |
| Fishing | NOT IMPLEMENTED | — | — | M5 |
| Economy | NOT IMPLEMENTED | — | — | M5 |
| Relationships | NOT IMPLEMENTED | — | — | M6 |
| Weather | NOT IMPLEMENTED | — | — | M7 |
| Day/night | NOT IMPLEMENTED | Three **static** lighting presets were rendered (day, sunset, night) | No continuous transition, no time system; lamps are a render-time switch, not simulation state | M7 |
| Environmental animation | NOT IMPLEMENTED | — | Everything is static; water, palms and birds do not move | M7 |
| Save/load | NOT IMPLEMENTED | — | — | M4 |
| Performance | UNVERIFIED | — | The viewer's timing readout (0.1–0.3 ms/frame) is not credible: the software GL does not block on `finish()`. No frame rate or memory figure is claimed | Measure on a real phone |
| Runs in a real engine | NOT IMPLEMENTED | — | `engine/viewer.html` is a 150-line test renderer written for this check, not a game engine | Stand up chosen engine |

## Defects found in the test scene (all open)
1. Ladder passes through the cliff; only its top pokes out above the ledge.
2. Daytime water is over-bright and the pale shoreline band reads as a flat white patch.
3. Night preset is too bright overall; lamp light pools are weak.
4. Cliff is a lathe-like lump with no caves, overhangs or strata. Far below the reference rock.
5. Seabirds are static two-triangle shapes resting at odd heights.
6. Boat hull is a single-sided skin with no thickness.
7. Window shutters intersect the frame slightly on the side window.

## Evidence package
- **A. Source files:** `tools/gen_test_vignette.py`, `tools/verify_glb.py`, `tools/capture.py`, `engine/viewer.html`, `assets/glb/lt_pipeline_test_01.glb`. Written but **never executed**: `blender/import_render_test.py`.
- **B. Visual:** `evidence/renders/01_overview_day.png` … `07_cottage_closeup_night.png` (1400×1400, WebGL2 via ANGLE/SwiftShader).
- **C. Technical:** `evidence/logs/environment_check.log`, `verify_glb.log`, `capture_log.json`.
- **D. Functional:** none. Nothing functional exists.
- **E. Limitations:** everything in the tables above marked FAILED, UNVERIFIED or NOT IMPLEMENTED.
