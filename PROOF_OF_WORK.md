# PROOF OF WORK — live scorecard

Statuses: **PASSED** (executed, evidence on disk) · **FAILED** (tested, defect found) · **UNVERIFIED** · **NOT IMPLEMENTED**.
Last update: 2026-11-11, session 4. Earlier session records are preserved unchanged below.

## Session 4 — master directive: audit, visual rebuild (district), simulation systems

### Headline
- Blender (bpy 4.5.15 LTS) and Godot 4.3 (headless + software-OpenGL frames) both ran again. **Still never run:** a GPU, the Forward+ renderer, an interactive session, an exported build.
- **Nothing visual is claimed as approved or as meeting the benchmark.** A representative district was built to a higher standard and is offered for review. `ART_BIBLE.md` §0 rates it honestly against the benchmark: below on silhouette, layering and overall craft.
- **Characters are frozen.** Residents are one plain grey mannequin, hidden in every presentation frame (E-series). T-series frames show them only to prove movement and interaction.
- The benchmark pages were **blocked** this session; no new study of the reference images was possible.
- Baseline before changes: commit `df08c5c`. Full audit and ranked weaknesses: `QA_REPORT.md`.

### Evidence, by kind
| Kind | Where | What it proves | What it does not |
|---|---|---|---|
| Blender render (Cycles, CPU) | `evidence/renders_village_v04/` (V*, D* day; `_golden`, `_night`), `evidence/renders_buildings/` | The generated geometry, colour and lighting as Blender sees them. No characters | How the game looks in engine |
| Godot frame (software OpenGL) | `evidence/renders_godot_v04/` E* (environment, no figures, no UI), T* (figures + UI) | The project loads, draws, lights, runs the sea shader, shows inspectors | Forward+ quality, frame rate |
| Godot recording | `evidence/renders_godot_v04/harbour_morning.mp4` (if present) | A dozen seconds of the running simulation, software-rendered | Smoothness |
| Godot runtime test | `evidence/logs/godot_tests.json`, `godot_tests_stdout.log` | Logic: navigation, objects, AI, economy, boats, weather, save/load, generations | Anything visual |
| Source check | `evidence/logs/pipeline_test.json`, `build_village.json` (island verification), `build_buildings.json` | Generated data and geometry obey the layout and the building contract | Looks |
| Concept art / AI images | none exist | — | — |

### Scorecard
| Requirement (directive part) | Status | Evidence | Limits |
|---|---|---|---|
| Audit + baseline (4, 19) | PASSED | `QA_REPORT.md`; commit `df08c5c` | Tag could not be pushed |
| Tools verified (5) | PASSED | `QA_REPORT.md` §1 | bpy module, software GL only |
| Coastal terrain: irregular silhouette, strata, ledges, overhangs, recesses, caves, beach (6.1) | PASSED (built) / **approval pending** | `sculpt.py`; island 38,321 tris, 10 caves; ray-cast verification: 0 nodes off height, 0 links buried; renders V03, D01, D03, E05, E06 | Strata harsh in engine light; plan still stepped |
| Village composition: varied footprints, overlap, rotations, courtyards (6.2) | **FAILED / not addressed** except ≤5° rotations | — | Needs layout v0.3 |
| Five architectural families + details (6.3) | PASSED (built) / approval pending | cottage, stilt, family house, stacked shop-house, long shed, civic; `evidence/renders_buildings/` | "Larger hillside residence" family missing; one roof language; no collision proxies per building |
| Storytelling details (6.3) | PASSED (first pass) | `dressing.py`; D02, D04, E03 | Hanging laundry, barrels, lanterns, patches, pots, crates, gardens, creepers, roof loads. No drainage channels, outdoor furniture limited to benches |
| Modular production standards (6.4) | PASSED partial | Kit modules, naming, origins, manifest | `.blend` files are generated; no LODs; island has a collision mesh, buildings do not |
| Representative district (21) | **Built - awaiting approval** | Blender D01-D05 (+ golden, night); Godot E03, E04, E07 | See `ART_BIBLE.md` §0 comparison |
| Interiors + interactive furnishings (7) | PASSED partial | 367/368 anchors; doors, beds, chairs, tables, stoves, sinks, washstands drive state | Cabinets, storage, lamps not usable; walls hide rather than fade |
| Interior camera (7) | UNVERIFIED interactively | T03, T06 | Driven by script only |
| Resident data + AI (8) | PASSED partial | 5 needs, health, derived mood, traits, age, household, job, partner, parents, children, log | No skills, preferences, memories, goals |
| No idle-forever / loops / deadlocks / negative stock / spontaneous money (8) | PASSED | 7-day soak; `Ledger.audit()` clean | Walking through walls is prevented only by the walk graph; residents overlap |
| Daily life loops (9) | PASSED partial | Soak totals in `QA_REPORT.md` | No clean-up, no leisure variety, rest day is every 7th day for everyone |
| Fishing + boats (10) | PASSED (logic) | 96 trips, cargo limits, landing sales, repairs; T01 | No fuel, gear, docking manoeuvre |
| Economy (11) | PASSED (first version) | Ledger totals in `godot_tests.json` | Three-step prices; supply glut; some wages unpaid |
| Relationships, families, generations (12) | PASSED mechanics / **FAILED sustainability** | 45-year run: 7 births, 34 deaths, 7 came of age, 12 estates, books balance, no dangling links | Population 42 → 15. No rivalry, marriage, conflict |
| Animation architecture independent of character art (13) | PASSED | 11 clip names on a neutral rig; `ANIMATION_MATRIX.md` | Run, turn, carry, board, net, unload clips missing |
| Ocean, vegetation, wildlife, day/night, weather (14) | Logic PASSED; presentation UNVERIFIED on a GPU | E02, E08 (storm), E09 (golden), E10 (night) | Gulls only; no wakes, reflections, fish |
| Sound (15) | UNVERIFIED | Generated surf / wind / rain | No licensed assets reachable; never heard |
| Camera + inspectors (16) | UNVERIFIED interactively | T02-T05 | — |
| Save / load (17) | PASSED | 4 tests incl. migration and rejection of a damaged file | In-process reload |
| Performance (18) | UNVERIFIED | Headless step rate only | No frame-rate numbers exist |
| Integration tests (20) | PASSED 57 / 57 | `godot_tests.json` | — |
| Standalone build (26) | NOT IMPLEMENTED | — | No export templates |
| Final characters (3, K) | BLOCKED by owner | — | — |

### Required visual deliverables (25)
| # | Deliverable | File(s) | Kind |
|---|---|---|---|
| 1 | Village overview | `renders_village_v04/V01_overview.png`; `renders_godot_v04/E01_overview_morning.png` | Blender; Godot |
| 2-3 | Harbour overview / close-up | `V02_harbour.png`; `E02_harbour_midday.png`, `E03_district_boardwalk.png` | Blender; Godot |
| 4 | Cliffside neighbourhood | `V03_hill_west.png`, `D03_district_backstair.png` | Blender |
| 5 | Five prototypes | `renders_buildings/H01, H02, H04, P05, P01 _exterior.png` | Blender |
| 6 | Household exterior | `D04_district_cottage.png` | Blender |
| 7 | Functional interior | `renders_buildings/H01_cutaway.png`; `T03_building_cutaway_H01.png` | Blender; Godot |
| 8 | Sea arch | `V08_gate_through.png`; `E05_sea_arch.png` | Blender; Godot |
| 9 | Waterfront | `D02_district_boardwalk.png`, `D05_district_beach.png`; `E07_shoreline_beach.png` | Blender; Godot |
| 10-12 | Day / golden hour / night | `V01`, `V01_overview_golden.png`, `D02_…_golden.png`, `V02_harbour_night.png`, `D01_…_night.png`; `E09_golden_hour.png`, `E10_harbour_night.png` | Blender; Godot |
| 13 | Ocean + shoreline | `E07`, `D05` | Godot; Blender |
| 14 | Vegetation / effects | `D04`, `E04`, `E08_storm_harbour.png` | Blender; Godot |
| 15 | Navigation + interaction testing | `T01_boat_at_sea.png`, `T02_resident_inspector_stairs.png`, `T04`, `T05` | Godot |
A file listed here exists only if it is in the folder; renders that failed to complete are named in `PROGRESS.md`.

## Session 3 — Blender pipeline + Godot project (executed)

### Headline
- **Blender and Godot both ran in this session.** Blender 4.5.15 LTS as the `bpy` Python module (Python 3.11) and Godot 4.3-stable headless. Log: `evidence/logs/environment_check_session3.log`. Results below are therefore executed results, not predictions - within the limits stated in each row.
- **What did not run:** the standalone Blender application (only the `bpy` module, same code), Godot's Forward+ (Vulkan) renderer, any real GPU, any interactive play session, any export to web/desktop/mobile. Those rows stay **UNVERIFIED**.
- **The session-2 layout is the base and was not edited.** `data/village_layout.json` is byte-identical to the uploaded file; `village/test_layout.py` still passes. All 30 building IDs, the 122-node walk graph, households, businesses and anchor stubs are consumed as-is.
- **M1 is still not claimed as approved.** Art direction, layout and the five prototypes need owner review. The buildings are parametric family variants generated by code, not individually hand-modelled.
- Written scripts are not offered as proof. Every PASSED row names a log or image produced by running something.

### Scorecard
| Requirement | Status | Evidence | Limits / problems | Next action |
|---|---|---|---|---|
| Blender runs here | **PASSED** (bpy 4.5.15 LTS) | `evidence/logs/environment_check_session3.log` | Module, not the application binary; no GPU; download.blender.org still blocked | Run the same scripts once in the desktop app |
| Godot runs here | **PASSED** (4.3-stable, headless) | same log; `evidence/logs/godot_tests_stdout.log` | Headless + software OpenGL only | Open the project on a machine with a GPU |
| Blender Python modelling pipeline | **PASSED** | `blender/livingtides/*.py`, `blender/build_buildings.py`, `blender/build_village.py`; logs `build_buildings.json` (30 buildings, 362,218 tris, 4.0 s), `build_village.json` (531,744 tris incl. environment) | Procedural; `.blend` outputs are regenerated, not hand-edited (git-ignored in `blender/out/`) | Hand-finish hero assets on top of generated bases |
| GLB export from Blender | **PASSED** | 30 files in `godot/assets/buildings/`, 7 in `godot/assets/env/`; checked by `tools/test_pipeline.py` (header, node names, vertex colours, anchor empties) | Unmerged vertices: terrain.glb is 7.8 MB for 65k tris | Weld + optimise before shipping |
| Cycles renders from Blender | **PASSED** | `evidence/renders_village_v03/V01…V08`, `evidence/renders_buildings/*` (CPU, 40-48 samples, 40-65 s each) | CPU only | — |
| Five architectural prototypes | **PASSED (built + rendered) / approval pending** | H01 cottage, H02 family house, H04 stilt house, P05 stacked store, P01 long-shed market: `evidence/renders_buildings/<ID>_exterior.png`, `_cutaway.png` | Families share one kit of parts; differences are form, roof, porch/balcony/awning, colour. No hand sculpting, no textures (art bible: vertex colour only) | Owner review; then per-building art passes |
| All 30 buildings as real models | **PASSED (family-derived)** | `ASSET_MANIFEST.md`, `evidence/logs/build_buildings.json` | Not individually art-directed; rows still face S or E only (layout weakness 2 untouched - buildings may not move outside `village/layout.py`) | Layout revision with the owner |
| Interiors + anchors | **PASSED** 367 of 368 stubs placed | `data/buildings/<ID>.json`; pipeline test "anchor stubs given a position" | 1 unplaced (third table in the eatery P06: no room). Positions live in sidecars; the layout JSON stubs are still null by design | Decide whether to write positions back via `village/layout.py` |
| Building contract (wall groups, roof, hinged door, cutaway) | **PASSED** | pipeline test + Godot tests "every prefab has ROOF, BASE, wall groups and a hinged door node", "cutaway hides roof + camera-facing walls"; `evidence/renders_godot/G05_cutaway_H01.png` | Cutaway is a hide, not a fade | Fade shader |
| Irregular cliffs over the surveyed terraces | **PASSED (first pass)** | `blender/livingtides/environment.py`; tests "terrain equals the layout height at every ground walk node", "no walk link is buried by rock", "cliff lips are irregular"; renders V01, V03, V04 | Height-field + rock masses: no caves or true undercuts except The Gate; terrace plan is still L-shaped | Sculpt hero cliffs; revise terrace polygons |
| The Gate sea arch | **PASSED** | `evidence/renders_village_v03/V08_gate_through.png` (harbour visible through the opening) | Lofted mesh, simple silhouette | Art pass |
| Stairs, ladder, rope bridge, piers, boats, lamps, landmarks | **PASSED (generated from the walk graph)** | `structures.glb`, `boats.glb`, `props.glb`; renders V02, V05 | Boats are static; bridge deck sag is visual only | Boat system |
| Godot project foundation | **PASSED** | `godot/` (project.godot, scenes, 20 scripts, shader); headless import clean except one LOD warning | — | — |
| Layout connected to Godot (IDs, paths, households, anchors) | **PASSED** | Godot tests 1-9: 30 prefabs, 435/435 door pairs, every interior anchor reachable, beds ↔ fishing spots | Kinematic walk graph; no physics, collision or navmesh | Navmesh comparison |
| One functional house (door, bed, cooking station, lighting, object states) | **PASSED (logic) / PASSED (software-GL frame)** | H01: Godot tests "door cycles…", "door leaf node rotates ~100 deg", "stove cold>lit>cooking>cold…", "cooking moves stock", "bed is reserved for its owner only", "interior lighting follows building state"; `G05_cutaway_H01.png` | The same systems are live in all 30 buildings, only H01 is asserted in detail. Door swing not watched by a person | Play it |
| Autonomous villagers (temporary characters) | **PASSED** 5 game days, 42 placeholder villagers | `evidence/logs/godot_tests.json`: 320 sleeps, 627 meals cooked, 646 eaten, 403 fish caught, 482 work blocks, 1,564 door openings, 2,539 stair climbs, 196 ladder climbs, 173 bridge crossings, 0 route failures, 0 failed uses, 0 minutes at maximum hunger; fish ledger balances | First run FAILED: one villager looped sleep/wake while starving; fixed (hungry villagers no longer sleep, market buying added). Needs and scores are untuned first values. Placeholder capsule people | Tuning, more needs, failure tests A-G from VILLAGER_AI.md |
| Reusable animation + interaction state machines | **PASSED** | `godot/scripts/villager/state_machine.gd`, `states/`, `villager_animator.gd`; tests "placeholder rig exposes all 11 animation clips", "animation state machine travels idle -> walk"; `ANIMATION_MATRIX.md`, `INTERACTION_MATRIX.md` | Clips are code-keyed transforms on a primitive rig. No skeleton, no IK | Replace rig when character art is decided |
| In-engine frames | **PASSED (software OpenGL, Compatibility renderer)** | `evidence/renders_godot/G01…G09` (Mesa llvmpipe under Xvfb, 1600×900) | Not the Forward+ renderer; no SSAO; frame rate meaningless | Capture on a GPU |
| Day / night, lamps, lit windows | **PASSED (software-GL frames)** | `G07_overview_sunset.png`, `G08_harbour_night.png`; lights follow occupancy per building (known issue 18 resolved) | Lighting values untuned on real hardware | Tune on a GPU |
| Sea shader | **PASSED (compiles and draws) / look UNVERIFIED** | `godot/shaders/ocean.gdshader`; G01, G02 | First version read the depth buffer and drew a white sea under software GL; replaced with a baked depth map. A PNG colour-management error then made the whole sea pale; fixed with a raw PNG writer | Judge on a GPU |
| Forward+ / Vulkan rendering | **UNVERIFIED** | — | No GPU | Owner machine |
| Interactive play (camera, HUD, input, speed keys) | **UNVERIFIED** | Code in `scripts/camera`, `scripts/ui`; they load and run in the capture scene | Nobody has pressed a key | Owner machine |
| Performance | **UNVERIFIED** | Headless sim: 72,000 steps in ~13 s for 42 villagers | No real frame timing | Measure on desktop + phone |
| Web / desktop / mobile export | **NOT IMPLEMENTED** | — | No export templates | Later milestone |
| Boats sailing, weather, relationships, family/aging, save/load, audio | **NOT IMPLEMENTED** | — | — | Later milestones |
| Final character art | **NOT STARTED (by instruction)** | — | Placeholder figures only | Owner decision |

### Tests executed this session
| Suite | Command | Result | Log |
|---|---|---|---|
| Layout (session 2, unchanged) | `python3 village/test_layout.py` | PASSED, 0 failures | stdout |
| Pipeline (pure Python) | `python3 tools/test_pipeline.py` | First run **FAILED 4 of 16** (two beds sharing a stand spot in H07; carpenter P07 had no box-breaking feature; slipway ramp buried 0.23 m by the quay edge; test wrongly demanded a door leaf on the open-fronted boat yard). Fixed. Now **PASSED 16 / 16** | `evidence/logs/pipeline_test.json` |
| Godot headless | `godot --headless res://tests/test_runner.tscn -- --days=5 --out=…` | First complete run **FAILED 1 of 30** (starving villager). Now **PASSED 31 / 31** | `evidence/logs/godot_tests.json`, `godot_tests_stdout.log` |

### Defects found by looking at the renders (fixed unless noted)
1. Stilt-house mono-pitch roofs were built with mismatched wedge walls - replaced with low gables.
2. A cliff rock sat on the Harbour Stair - stair, ladder and bridge corridors are now keep-out zones.
3. Render sky was black above the horizon - camera rays now see a flat sky colour.
4. Godot captures were taken from the south-west; the layout's camera is south-east - default and captures corrected, cutaway now picks the walls facing the camera.
5. Godot daylight over-exposed and fogged - sun, ambient and fog reduced. Still untuned on real hardware.
6. **Open:** headless Godot prints ~295 `Parameter "m" is null` renderer messages at shutdown (dummy renderer, after the result line). Harmless to results; cause not investigated.
7. **Open:** fishing-boat wheelhouse is a plain box; trees can stand close enough to a house to block a close-up; vegetation ignores canopy radius.
8. **Open:** shutters and window boxes are generated per window with no check against neighbouring roofs or lean-tos.

### Evidence package (session 3)
- **A. Source:** `blender/livingtides/` (geometry kit, parts, furniture, building generator, environment, Blender bridge), `blender/build_buildings.py`, `blender/build_village.py`, `tools/gen_population.py`, `tools/sync_godot_data.py`, `tools/test_pipeline.py`, `tools/package.sh`, `godot/`.
- **B. Visual:** `evidence/renders_village_v03/` (Blender Cycles), `evidence/renders_buildings/` (five prototypes, exterior + cutaway), `evidence/renders_godot/` (in-engine, software GL).
- **C. Technical:** `evidence/logs/environment_check_session3.log`, `build_buildings.json`, `build_village.json`, `pipeline_test.json`, `godot_capture.log`.
- **D. Functional:** `evidence/logs/godot_tests.json`, `godot_tests_stdout.log`.
- **E. Limitations:** every row above marked UNVERIFIED, NOT IMPLEMENTED or "approval pending", and the open defects.

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
