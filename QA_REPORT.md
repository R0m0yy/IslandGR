# QA REPORT — session 4 audit (2026-11-11)

Baseline before this session's changes: commit `df08c5c` (local tag `baseline-session3`; the tag could not be pushed - the remote rejected tag pushes - so use the commit hash).
Statuses: **PASSED** executed and met the requirement · **FAILED** executed and did not · **UNVERIFIED** exists, not properly tested · **NOT IMPLEMENTED**.
Evidence types are kept apart: *Blender render* (Cycles, CPU), *Godot runtime* (headless logic), *Godot frame* (software OpenGL, Compatibility renderer), *source check* (pure Python). There is no concept art and no AI-generated imagery anywhere in this project.

## 1. Tools actually available
| Tool | Result |
|---|---|
| Blender | **Runs** as the `bpy` 4.5.15 LTS module (Python 3.11, CPU Cycles). The desktop application was not run. |
| Godot | **Runs**: 4.3-stable headless, and windowed under Xvfb with Mesa llvmpipe (software OpenGL, Compatibility renderer). |
| GPU / Forward+ / Vulkan | **Not available.** Every Godot frame in the evidence is software-rendered. |
| Interactive play | **Not possible here.** No key or mouse event has ever been sent by a person. |
| Export templates | Not installed: no standalone build. |
| Reference sites (ArtStation, Behance, 80.lv) | **Blocked** (DNS). The benchmark was studied from the session-1 written analysis in `REFERENCE_RESEARCH.md`, not from the images this session. |
| Audio assets | None could be downloaded; ambience is generated in code. |

## 2. Audit of what existed at the start of this session
| Area | Found | Verdict |
|---|---|---|
| Layout data (30 buildings, walk graph, households, businesses) | Real, tested | Preserve unchanged |
| Building generator, parts kit, furniture | Real, runs in Blender | Keep; needed a storytelling pass |
| Terrain | Height field + rock blobs: no undercuts, caves or overhangs | **Rebuild** (done: `sculpt.py`) |
| Godot world assembly, walk graph, doors, beds, stoves | Real, tested | Keep |
| Villager AI | Hunger + energy only; fish created on a counter with no money anywhere | Extend (done) |
| Economy | A single integer `market_stock` | **Replace** with a ledger (done) |
| Boats | Static props | **Implement** (done, logic) |
| Weather, relationships, family, aging, save/load, inspectors, audio | Documented only | Implement first versions (done; see limits) |
| Placeholder characters | Coloured figures with large heads | Replaced by one neutral mannequin; hidden in presentation frames |
| Session 1-2 files (`assets/glb`, `engine/`, `tools/preview`) | Superseded but harmless | Kept untouched |

## 3. Ranked visual weaknesses (worst first) and what was done
| # | Weakness | Action this session | Status now |
|---|---|---|---|
| 1 | Cliffs were a stepped height field: no carved feel, no caves, no undercut | Island rebuilt with voxel fusion, boolean caves (10), strata ledges, overhanging lips, eroded base; walkable tops snapped to survey and verified by ray casting | Improved; a first version read as a striped layer cake in engine and was softened. **Awaiting approval** |
| 2 | Buildings were clean boxes with roofs: no story | Gutters + rain barrels, door lanterns, patch planks, laundry, crab pots, crates, kitchen gardens, creepers, roof loads, bare boards, small rotations | Improved. **Awaiting approval** |
| 3 | Rows and right angles | Each building rotated up to 5° about its door (walk graph unaffected) | Minor gain. Real fix needs a layout revision |
| 4 | Terrace edges bare | Rope-and-post railings, plants spilling over lips, grass tufts and flowers | Improved |
| 5 | Waterfront empty | Working beach on the spit: upturned skiff, drying racks, driftwood, floats | Improved |
| 6 | Sea flat and uniform | Depth tint + shore foam from a baked depth map, sea state follows the wind | Software-GL only; look **UNVERIFIED** on a GPU |
| 7 | One family of roof; little silhouette variety between homes | Not addressed | **Open** |
| 8 | Houses do not overlap or cantilever past the rock like the benchmark | Not addressed (needs layout + stilted platforms) | **Open** |
| 9 | No textures, flat materials | By art-bible rule; not revisited | Open question for the owner |

## 4. Test results (all executed this session)
| Suite | What it is | Result |
|---|---|---|
| `python3 village/test_layout.py` | Source check of the layout | PASSED, 0 failures |
| `python3 tools/test_pipeline.py` | Source check of generated geometry and data, 16 checks | PASSED 16 / 16 (one check widened for dressing, see PROOF_OF_WORK) |
| Island verification inside Blender | Ray casts from every ground walk node and along every link | PASSED: 0 nodes off height, 0 links buried (first run: 2 nodes 6 cm low, slipway ramp and ladder buried; fixed) |
| `godot --headless res://tests/test_runner.tscn -- --days=7 --gen-days=45` | Godot runtime | **PASSED 57 / 57** |

Seven-day unattended run, 45 residents, 5130 plans: 476 sleeps, 843 meals cooked, 854 eaten, 1207 fish caught, 96 boat trips (1130 fish landed, 1 trip(s) aborted by weather), 468 work blocks, 417 wages paid / 51 unpaid, 499 drinks, 162 washes, 2312 door openings, 3531 stair climbs, 0 route failures, 0 failed uses, 0 minutes at maximum hunger, ledger audit clean.

### Required integration tests
| Requirement | Status | Evidence / limit |
|---|---|---|
| Navigation: homes, workplaces, market, docks, boats, stairs, bridge, interiors | PASSED | 435/435 door pairs; every interior anchor; boats boarded 96 times; 0 route failures in 7 days |
| Collision problems / walking through walls | **UNVERIFIED** | Movement is kinematic on the walk graph; residents cannot leave it, but they pass through each other and nothing checks them against meshes |
| Household: food consumed, meals prepared, sleep restores energy, inventories consistent | PASSED | Soak totals + ledger audit |
| Fishing: assignment, boarding, navigation, catch, cargo limit, return, unloading, market delivery, payment | PASSED (logic) | Tests "boats: crews board…", "landed fish is sold…", "cargo never exceeds…" |
| Economy: income, purchases, transfers, stock, pricing, scarcity, consistency | PASSED with limits | Prices have three steps only; 51 wages went unpaid; fish supply far exceeds demand |
| Persistence: save mid-activity, rebuild world, load, continue | PASSED | In-process rebuild, not an OS-level quit and relaunch. Activities restart from the last walk node |
| Seven-day soak: deadlocks, starvation, repetition, negative money/stock, broken routines, save data, exceptions | PASSED | No script errors in the log |
| Weather interruption recovery | PASSED | Storm forced mid-trip: boat turned, moored, crew chose another activity; no departures in a storm |
| Relationship / family state validity | PASSED | No dangling partners, homes, beds or member counts after 45 simulated years |
| Population sustains itself over generations | **FAILED** | 42 → 15 residents in 45 years (7 births, 34 deaths). Homes hold too few beds for children and pairing is slow |

## 5. Subsystem status
| Subsystem | Status | Notes |
|---|---|---|
| Blender asset pipeline | PASSED | 30 buildings + island + environment rebuilt in ~25 s |
| Representative district (west quay, stilt houses, Back Stair, beach) | Built - **awaiting owner approval** | `evidence/renders_village_v04/D0*.png`, `evidence/renders_godot_v04/E03, E04, E07` |
| Interiors + anchors | PASSED (367/368) | Furniture is functional but plain |
| Interior camera (select building → focus → cutaway → return) | UNVERIFIED interactively | Exercised by the capture script only; walls hide, they do not fade |
| Doors, beds, stoves, chairs, sinks, washstands | PASSED | Tied to state and ledger |
| Cabinets, storage, lamps as usable objects | NOT IMPLEMENTED | Modelled and anchored; lamps follow occupancy; storage has no inventory UI |
| Resident data (needs, traits, age, household, job, relationships, history) | PASSED partial | No skills, preferences, personal goals or memories yet |
| Daily routine | PASSED partial | Wake, wash, drink, cook, eat, work, shop, eat out, stroll, sleep; rest day every 7th. No "clean up", no leisure variety |
| Boats | PASSED (logic) | No fuel, no docking animation, boats pass through each other, gear is not gathered |
| Economy | PASSED (first version) | See limits above |
| Relationships and families | PASSED (first version) | Friendship from proximity only; no rivalry, no marriage ceremony, no conflict |
| Aging, death, inheritance | PASSED | Pace set by `Society.days_per_year` |
| Weather | PASSED (logic) / frames software-GL | Affects boats and outdoor choices; no shelter-seeking mid-walk |
| Wildlife | UNVERIFIED | Seven gulls on circuits; no crabs, no fish |
| Vegetation wind | UNVERIFIED | Shader compiles; not seen in motion |
| Audio | UNVERIFIED | Generated surf / wind / rain noise; never heard. No footsteps, doors, market, birds |
| Camera, selection, inspectors | UNVERIFIED interactively | Frames T02-T05 show the panels |
| Save / load | PASSED | Version 2, migration from 1 tested |
| Performance | UNVERIFIED | Headless: 100,800 simulation steps in 33 s. No frame-rate measurement is possible here |
| Standalone build | NOT IMPLEMENTED | No export templates |
| Final characters | **BLOCKED by owner** | Neutral mannequins only |

## 6. Defects found and fixed this session
1. Island: two walk nodes 6 cm low after decimation → second snap pass.
2. Island: slipway ramp and ladder buried by the quay / terrace lip → clearance cut-outs.
3. Island: the ladder cut-out removed the ground at the ladder top → shortened.
4. Boat hulls and the beach skiff rendered magenta (missing colour role).
5. Pipeline test failed after dressing (laundry posts beyond 1.5 m) → placement already requires clearance; bound widened to 2.1 m.
6. Wages: 242 of 465 unpaid → levy and wage rebalanced (51 of 468 unpaid now).
7. Generations: 42 → 9 residents → children may share a parent's bed, young adults found homes in empty houses, pairing threshold lowered (42 → 15; still FAILED).
8. Capture and HUD scripts had type-inference errors that only show with a display.

## 7. Open defects
See `KNOWN_ISSUES.md` (session 4 table).
