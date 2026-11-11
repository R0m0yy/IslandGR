# PROGRESS — development handoff

## Session 1 (2026-11-09)
**Completed and executed**
- Environment probe: no Blender, no `bpy`, no Godot, no three.js, no GPU; installs refused. 2 CPU cores, 8 GB RAM. Headless Chrome with WebGL2 (software) works.
- Research: 80 Level interview read in full; Behance/Dribbble/ArtStation only via search excerpts.
- Pipeline test: Python generator → `.glb` → independent re-open → 7 WebGL captures.
- Documents written: README, PROOF_OF_WORK, PROGRESS, REFERENCE_RESEARCH, ART_BIBLE, BLENDER_PIPELINE, ENGINE_EVALUATION, WORLD_LAYOUT, ARCHITECTURE, VILLAGER_AI, ASSET_MANIFEST, MILESTONES, KNOWN_ISSUES, LICENSES.

**Not written yet** (no content to put in them honestly): ANIMATION_MATRIX, INTERACTION_MATRIX, FISHING_SYSTEM, ECONOMY_SYSTEM, FAMILY_SYSTEM, CAMERA_SYSTEM, PERFORMANCE_BUDGET, QA_REPORT. Their outline specs live in ARCHITECTURE.md until their milestones start.

**Blocked on the owner**
1. Enable package installs (network settings), then start a new chat — needed for Blender and any engine.
2. Approve or change the engine recommendation (`ENGINE_EVALUATION.md`).
3. Approve or change the art direction and village layout (`ART_BIBLE.md`, `WORLD_LAYOUT.md`).

**Exact next steps once unblocked**
1. `pip install bpy` (or install Blender); run `blender -b -P blender/import_render_test.py`; record version, `.blend` path, export warnings, Cycles render.
2. Install the approved engine; load the same GLB; capture in-engine frames; measure frame time on a phone.
3. Start M1: cliff massing blockout in Blender per `WORLD_LAYOUT.md`, then hero buildings H01–H03, then lighting. Stop at the M1 approval gate.

## Session 2 (2026-11-09) — corrective directive
**Owner decisions received:** M1 not approved. Cottage kept as pipeline test. Target is a 20–30 building interconnected village. Prefer Godot 4. No character design yet.

**Completed and executed**
- Environment re-check: still no Blender/Godot; PyPI, GitHub, blender.org blocked. Found Python 3.11 and `uv` on the machine (useful for the `bpy` route later).
- Engine decision revised to Godot 4 (`ENGINE_EVALUATION.md` v2); v1 moved to `docs/`.
- `ENVIRONMENT_REQUIREMENTS.md`: exact requirement for a working Blender + Godot setup.
- Village layout v0.2 as data: 30 buildings on 5 terraces + headland + stack + spit, sea arch, 8 stairs, ladder, 19 m bridge, piers, boardwalk, 6 boats; households, businesses, jobs, interior and anchor stubs per building.
- `village/test_layout.py`: run 1 failed (1 defect), fixed; second defect found and fixed; now 0 failures.
- Temporary massing GLB + navigation overlay GLB generated, re-opened, rendered (9 views).
- `BUILDING_CONTRACT.md`, `WORLD_LAYOUT.md` v0.2, scorecard updated.

**Not done**
- No Blender, no Godot, no production art, no simulation code.
- Art bible not yet revised for the v0.2 layout (still describes the v0.1 crescent and "Comb" landmark in section 2; palette and rules still apply).
- ASSET_MANIFEST not yet re-keyed to the 30 building IDs.

**Blocked on the owner**
1. Enable package installs / network access, then start a new chat.
2. Layout review: approve, or say what to change (see the five weaknesses listed in `WORLD_LAYOUT.md`).

**Exact next steps**
1. New chat with installs enabled → Blender `bpy` under Python 3.11 → run `blender/import_render_test.py` on the massing → Godot binary + web templates → import, export, capture.
2. Revise layout for owner feedback; break the terraces and rows; re-run tests.
3. Model in Blender in this order: cliffs and The Gate → Harbour Stair and quay → hero buildings H02, P01, H11 with interiors → the rest by family.
4. Godot spike: navmesh bake vs walk graph; placeholder character on stairs and through a door.


## Session 3 (2026-11-10 / 11) — development continues in Claude
**Owner decisions received:** keep developing here; preserve everything; Blender 4.x + Godot 4.x; five prototypes; one functional house; autonomous villagers with temporary characters; label unexecuted results UNVERIFIED; ZIP after each milestone.

**Environment:** installs now work. Blender 4.5.15 LTS (`bpy` wheel, Python 3.11) and Godot 4.3-stable (headless; software OpenGL under Xvfb for captures) both run. So this session's Blender and Godot results are executed, with the limits listed in `PROOF_OF_WORK.md`.

**Completed and executed**
- Uploaded project imported verbatim as the first commit; layout JSON untouched; session-2 layout test still passes.
- Blender pipeline (`blender/livingtides/`): geometry kit, parts (walls with real openings, plank cladding, corrugated tin and tile roofs, windows, shutters, doors, balconies, stairs, awnings, pergola…), furniture for all 28 anchor types, parametric building generator for five families, environment generators.
- All 30 buildings built from their layout records → 30 GLB prefabs + anchor sidecars (`data/buildings/`). 367 of 368 anchor stubs placed.
- Environment: terrain with irregular cliff lips and ledges over the surveyed terraces, The Gate, 8 stairs, ladder, rope bridge, decks, paving, 6 boats, 16 lamps, well, cistern, lookout, beacon, great tree, vegetation.
- Cycles renders of the village (8 views) and the five prototypes (exterior + cutaway).
- Godot 4 project: data autoloads, typed walk graph + A*, Building prefab wrapper, interactables (door, bed, stove, fishing spot, generic stations), villager (needs, utility brain, reusable state machine, placeholder animated rig), fixed-step simulation, day/night, sea shader, orbit camera, HUD, cutaway.
- Tests: pipeline 16/16, Godot 31/31 (5 simulated days, 42 placeholder villagers), layout 0 failures. Failing first runs are recorded in `PROOF_OF_WORK.md`.
- In-engine captures (software GL): 9 frames.
- Documents: this file, PROOF_OF_WORK, README, BLENDER_PIPELINE, KNOWN_ISSUES, ASSET_MANIFEST (re-keyed to the 30 IDs), new ANIMATION_MATRIX, INTERACTION_MATRIX, `godot/README.md`.

**Decisions taken without the owner (please confirm or reverse)**
1. Simulation written in GDScript inside Godot rather than the TypeScript core in `ARCHITECTURE.md`. It keeps the rule that logic runs without graphics (the tests prove it), but it is not the two-program design.
2. Buildings follow the art bible literally: painted planks, coloured tin roofs, vertex colour, no textures, nothing bevelled.
3. Stilt houses got low gable roofs (the mono-pitch attempt was broken).
4. Placeholder population: two adults per household, jobs dealt at random (`data/dev_population.json`). Not part of the layout.
5. A minimal fish market (working fishers land every second fish at P01; households with an empty pantry buy) was added to stop starvation. It is a stand-in for the economy module.
6. Anchor positions are stored in sidecars, not written back into `village_layout.json`.

**Not done**
- No hand modelling or sculpting; no caves or undercuts; terraces and building rows still follow the session-2 plan.
- No collision, physics or navmesh; no boats under way; no weather, relationships, family, save/load, audio.
- No GPU run, no interactive session, no export, no performance numbers.
- ART_BIBLE §2 still describes the v0.1 crescent.

**Blocked on the owner**
1. Open `godot/project.godot` in Godot 4.3+ on a real machine and report what you see (first Forward+ run, input, frame rate).
2. Review the five prototypes and the overall look (`evidence/renders_buildings/`, `evidence/renders_village_v03/`).
3. Layout review carried over from session 2 (rows, terrace shapes, The Gate position, crown access).
4. Confirm or reverse the six decisions above.

**Exact next steps**
1. Owner feedback on look → per-family art passes (silhouette variety, a sixth "civic" language, props at doors).
2. Layout v0.3 in `village/layout.py`: rotate and stagger houses, uneven terrace heights; rebuild everything from data (one command each).
3. Villager tests A-G from `VILLAGER_AI.md`; thirst/hygiene/social needs; shop hours; work output.
4. Boats: boarding at `board` links, sea lanes, fishing grounds.
5. Collision + navmesh spike in Godot; compare with the walk graph.
6. Save/load of world state.


## Session 4 (2026-11-11) — master directive
**Owner decisions received:** full-project scope; visual standard non-negotiable and unapproved; characters frozen; perfect one district before multiplying; keep everything working; honest status labels.

**Completed and executed**
- Baseline `df08c5c`; audit and ranked weaknesses (`QA_REPORT.md`).
- Island rebuilt in Blender with real sculpting tools (`blender/livingtides/sculpt.py`): voxel fusion, 10 boolean caves, strata ledges, overhanging lips, eroded waterline, beach; verified against the walk graph by ray casting.
- Storytelling pass on all buildings (`dressing.py`) and the village (rope railings, lip plants, ground cover, working beach); ≤5° rotation per building.
- Representative district defined (west quay, stilt row, Back Stair, spit beach) with five dedicated camera views, day / golden hour / night.
- Characters: one neutral mannequin, hideable; all presentation frames exclude it.
- Godot systems: Ledger + Economy (wages, levy, market prices, eatery, boat repairs), Boats (trips along sea lanes, cargo, landing sales), Weather (state machine; storms turn boats back), thirst / hygiene / social needs with drink / wash / eat-out / shop states, Society (friendships, partnerships, births, aging, retirement, death, estates, event history), SaveGame (versioned, migration, validation), selection camera + resident / building / village inspectors, atmosphere (rain, sea state, boat bobbing, gulls, foliage sway, generated ambience).
- Tests: layout 0 failures; pipeline 16/16; Godot **57 / 57** including the 7-day soak, storm interruption, save/load and a 45-year generational run.

**Failed or unverified (details in `QA_REPORT.md`)**
- FAILED: population sustainability (42 → 15 in 45 years); village composition (rows, no overlap).
- UNVERIFIED: everything that needs a GPU, ears or hands - Forward+ look, lighting, sea, rain, sway, audio, camera, inspectors, input, performance.
- NOT IMPLEMENTED: standalone build, skills / preferences / memories, storage inventories, fuel, most wildlife, licensed audio, layout v0.3.

**Decisions taken without the owner (confirm or reverse)**
1. The kit improvements (dressing, rotations, sculpted island) were applied to the whole village, not only the district, because they are generated by rule and the village has to stay consistent to remain testable. The *approval sample* is the district.
2. Economy shape: council funded by a household levy pays non-trading workplaces; market and eatery pay their own staff.
3. Young children share a parent's bed (homes have two beds); adults of 18 may found a home in an empty house.
4. Placeholder couples: two adults sharing a home start as partners.
5. `Society.days_per_year` defaults to 28; tests use 1.

**Blocked on the owner**
1. **District review** - approve, or say what is wrong (`evidence/renders_village_v04/D0*`, `evidence/renders_godot_v04/E03, E04, E07`).
2. Open the project on a GPU machine: look, input, sound, frame rate.
3. Layout v0.3 direction (overlap, cantilevers, uneven terraces).
4. Textures: the art bible forbids them; the benchmark does not obviously need them. Confirm.
5. Character concepts: say when you want options to compare.

**Next steps:** `DEVELOPMENT_ROADMAP.md`.
