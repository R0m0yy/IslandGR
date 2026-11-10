# ASSET MANIFEST — first pass (hero set for M1–M3)

Source for all: custom, project-owned. Format: `.blend` source → `.glb`. Status of all rows: **NOT STARTED** unless stated. Poly budgets are targets, not measurements.

| ID | Name | Category | Location | Importance | Approach | Tris | Collision | Animation | Interaction |
|---|---|---|---|---|---|---|---|---|---|
| TER-01 | Western horn cliffs | Cliffs | whole west | Hero | Hand-shaped, faceted | 12k | Simplified hull per terrace | — | — |
| TER-02 | Eastern reef spit | Terrain | east | High | Hand-shaped | 3k | Yes | — | — |
| TER-03 | The Comb (3 fins + bridge) | Landmark | spit tip | Hero | Hand-shaped + Array bridge | 4k | Yes | Bridge sway | Walkable |
| TER-04 | Sea floor + beach | Terrain | lagoon | Medium | Hand-shaped | 2k | — | — | — |
| WAT-01 | Sea surface | Water | tile | Hero | Grid + shader | 4k | — | Vertex waves | Boat buoyancy sample |
| BLD-H01 | Quay cottage | Home | T1 | Hero | Modular kit + hand detail | 3k | Walls, floor | Door, shutters | Cutaway, 1 room |
| BLD-H02 | Stacked store-house | Home/shop | T2 | Hero | Kit + hand detail | 5k | Yes | Door, awning | Cutaway, 2 floors |
| BLD-H03 | Hillside family house | Home | T3 | Hero | Kit + hand detail | 5k | Yes | Doors | Cutaway, 3 rooms |
| BLD-P01 | Fish market | Public | T1 | Hero | Hand | 4k | Yes | Awning, scales | Stalls, counter |
| BLD-P02 | Boat yard shed + slip | Public | T1 | High | Kit | 3k | Yes | — | Repair stations |
| NAV-01 | Harbour Stair | Stair | T1→T2 | Hero | Array + hand breakup | 1.5k | Ramp proxy | — | Walk edge |
| NAV-02 | Pier A | Dock | T0 | High | Array | 1.5k | Yes | — | Boarding points |
| KIT-RF | Roof sheets, ridge, patches | Roof kit | all | High | Array | 150/sheet | — | — | — |
| KIT-WL | Plank wall panels (5 widths, door/window cut-outs) | Wall kit | all | High | Array | 200/panel | — | Fade for cutaway | — |
| KIT-DW | Doors ×3, windows ×4, shutters | Openings | all | High | Mirror | 150 each | Door blocker | Hinge | Open/close |
| BOT-01 | Rowing skiff | Boat | T0 | Hero | Hand, Mirror | 800 | Hull proxy | Bob, oars | Board, row, cargo |
| BOT-02 | Small sail/motor fishing boat | Boat | T0 | High | Hand, Mirror | 1.5k | Hull proxy | Bob, sail | Board, steer, cargo, nets |
| VEG-01 | Coconut palm ×3 variants | Vegetation | all | High | Hand | 500 | Trunk | Wind weights | — |
| VEG-02 | Shade tree, shrubs, vines, garden plants | Vegetation | all | Medium | Hand + scatter | 100–900 | Trunk | Wind | Garden plots |
| FRN-01 | Bed, table, chair, stove, sink, cabinet, lamp, storage chest | Furniture | interiors | High | Hand | 100–400 | Simple | Lids, doors, flame | Full framework |
| PRP-01 | Crates, barrels, baskets, sacks, pots, buckets | Props | all | Medium | Hand | 50–250 | Large only | — | Some carryable |
| PRP-02 | Nets, traps, rods, buoys, drying racks, fish | Fishing | T0–T1 | High | Hand | 50–400 | — | Net, rod | Tools, catch |
| PRP-03 | Laundry lines, lanterns, signs, awnings, benches | Decoration | all | Medium | Hand | 50–300 | — | Cloth sway, lamp | Lamps, benches |
| WLD-01 | Gull, crab, fish school, chicken, cat | Wildlife | all | Medium | Hand | 60–300 | — | Rigged or vertex anim | — |
| CHR-TMP | Temporary test villager (clearly placeholder) | Character | — | — | Simple rig | 800 | Capsule | Full test set | — |

Existing test asset (not part of the manifest proper): `assets/glb/lt_pipeline_test_01.glb` — DONE as a pipeline test only.
Interiors will be itemised room by room before M3.
