# ASSET MANIFEST — session 3 (keyed to the 30 building IDs)

Generated from `evidence/logs/build_buildings.json` and `build_village.json`. Every file below is produced by `blender/build_buildings.py` / `blender/build_village.py` and can be regenerated; none was edited by hand.

## Building prefabs — `godot/assets/buildings/<ID>.glb` + `data/buildings/<ID>.json`
Pivot: front-door threshold at terrace level. Nodes: `<ID>_WALL_S|E|N|W`, `<ID>_ROOF`, `<ID>_BASE`, `<ID>_INTERIOR`, `<ID>_FLOOR2` (two storeys), `<ID>_DOOR_main` (pivot on the hinge), empties `<ID>_IA_<object>_<slot>`. Vertex colour `Col`; materials `LT_matte`, `LT_metal`, `LT_glass`, `LT_emit_fire`, `LT_emit_lamp`.

Prototypes reviewed in close-up: **H01** (cottage), **H02** (family house), **H04** (stilt house), **P05** (stacked store), **P01** (long-shed market). The rest are variants of the same five families.

| ID | Name | Kind | Family | Storeys | Tris | Anchors placed / stubs | GLB bytes | Box-breaking features |
|---|---|---|---|---|---|---|---|---|
| P01 | Fish market | market | long_shed | 1 | 14,292 | 7 / 7 | 1,037,080 | open front + awning |
| P02 | Boat yard | boatyard | long_shed | 1 | 9,180 | 7 / 7 | 677,788 | open front + awning |
| P03 | Warehouse | warehouse | long_shed | 1 | 17,054 | 7 / 7 | 1,251,904 | entrance porch, lean-to store (E) |
| P04 | Net loft | netloft | stacked | 2 | 14,368 | 5 / 5 | 1,090,036 | awning + sign |
| P05 | General store | store | stacked | 2 | 17,746 | 12 / 12 | 1,344,072 | awning + sign, lean-to store (N) |
| P06 | Eatery | eatery | stacked | 1 | 10,956 | 14 / 15 | 820,928 | awning + sign |
| P07 | Carpenter | carpenter | long_shed | 1 | 9,896 | 7 / 7 | 739,512 | entrance porch |
| P08 | Community hall | hall | civic | 2 | 18,038 | 10 / 10 | 1,349,012 | entrance porch, bell-cot, lean-to store (E) |
| P09 | School | school | civic | 1 | 12,090 | 8 / 8 | 903,240 | entrance porch, bell-cot, lean-to store (E) |
| P10 | First-aid house | clinic | cottage | 1 | 9,902 | 7 / 7 | 753,160 | door canopy, lean-to store (E) |
| H01 | Quay cottage | home | cottage | 1 | 10,998 | 13 / 13 | 846,448 | door canopy, lean-to store (S) |
| H02 | Harbour office house | home | family_house | 2 | 17,146 | 18 / 18 | 1,294,940 | front balcony under the gable, lean-to store (W) |
| H03 | Stilt house west | stilt_home | stilt | 1 | 9,032 | 14 / 14 | 697,360 | door canopy, net rack |
| H04 | Stilt house middle | stilt_home | stilt | 1 | 9,212 | 14 / 14 | 713,564 | door canopy, net rack |
| H05 | Stilt house east | stilt_home | stilt | 1 | 8,932 | 14 / 14 | 690,288 | door canopy, net rack |
| H06 | Terrace house 1 | home | cottage | 1 | 10,198 | 13 / 13 | 771,024 | door canopy, lean-to store (W) |
| H07 | Terrace house 2 | home | family_house | 2 | 13,984 | 18 / 18 | 1,076,760 | front balcony under the gable |
| H08 | Terrace house 3 | home | cottage | 1 | 9,560 | 13 / 13 | 721,556 | door canopy |
| H09 | Terrace house 4 | home | cottage | 1 | 10,086 | 13 / 13 | 763,296 | door canopy, lean-to store (E) |
| H10 | West lane house 1 | home | cottage | 1 | 12,278 | 13 / 13 | 925,124 | door canopy, lean-to store (N) |
| H11 | West lane house 2 | home | family_house | 2 | 16,260 | 18 / 18 | 1,234,672 | front balcony under the gable |
| H12 | West lane house 3 | home | cottage | 1 | 10,644 | 13 / 13 | 794,512 | door canopy |
| H13 | High row house 1 | home | cottage | 1 | 11,014 | 13 / 13 | 823,592 | door canopy, lean-to store (W) |
| H14 | High row house 2 | home | family_house | 2 | 14,704 | 18 / 18 | 1,116,060 | front balcony under the gable |
| H15 | High row house 3 | home | cottage | 1 | 10,282 | 13 / 13 | 768,640 | door canopy, lean-to store (E) |
| H16 | High row house 4 | home | cottage | 1 | 10,942 | 13 / 13 | 823,440 | door canopy, lean-to store (W) |
| H17 | Shelf house south | home | cottage | 1 | 10,194 | 13 / 13 | 767,340 | door canopy, lean-to store (N) |
| H18 | Shelf house north | home | cottage | 1 | 11,922 | 13 / 13 | 885,400 | door canopy, lean-to store (N) |
| H19 | Crown cottage | home | cottage | 1 | 9,954 | 13 / 13 | 749,720 | door canopy, lean-to store (E) |
| H20 | Keeper's house | home | cottage | 1 | 11,354 | 13 / 13 | 854,876 | door canopy, lean-to store (E) |

## Environment — `godot/assets/env/`
| File | Contents | Tris | Bytes |
|---|---|---|---|
| terrain.glb | Height-field island: surveyed terraces, irregular cliff lips, ledges, talus, seabed | 64,896 | 7,788,696 |
| cliffs.glb | Layered rock masses, cap stones, shore boulders, sea stacks | 34,000 | 4,080,828 |
| gate.glb | The Gate sea arch (walkable top) | 976 | 110,844 |
| structures.glb | 8 stairs, ladder, rope bridge, 5 decks with piles, ramps, paving flags | 27,972 | 2,171,344 |
| props.glb | 16 lamp posts, well, cistern, lookout, beacon, harbour clutter | 6,434 | 469,148 |
| vegetation.glb | 16 palms, 22 trees, 90 shrubs, great tree | 26,664 | 2,384,792 |
| boats.glb | 6 boats at their moorings (4 skiffs, 2 fishing boats), one node each | 8,584 | 686,128 |
| seabed_height.png | 209×157 depth map read by the sea shader | — | small |

Whole village: **531,744 triangles**. Not yet optimised (no welding, LODs or instancing).

## Not yet made
Characters (undecided), wildlife, weather effects, interior doors, signage text, damage variants, collision meshes, LODs.

---
# Session 1-2 manifest (superseded, kept for the record)

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
