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
