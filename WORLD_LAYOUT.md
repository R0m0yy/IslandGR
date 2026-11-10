# WORLD LAYOUT — "Saltcrown" v0.2 (TEMPORARY MASSING — awaiting approval)

Source of truth: `village/layout.py` → `data/village_layout.json`. Everything in this document is generated from or checked against that data. v0.1 is kept in `docs/`.

Original design. Sea tile 100 × 77 m. Camera looks from the south-east.

## Shape
A stepped western hill of five terraces wraps the north and west sides of a harbour. A low spit closes the south. On the east, a 9 m headland reaches south through **The Gate** — a sea arch with a 9 m wide, ~6 m high opening that boats sail through to the reef grounds — to a stack carrying the beacon. A 19 m rope bridge joins the residential hill to the headland high above the east quay.

## Districts
| Level | Height | District | Buildings |
|---|---|---|---|
| Water | 0 | Harbour | Piers A and B, slipway, boardwalk, 6 moorings, 3 stilt houses (H03–H05) |
| T1 | +1.5 m | Quay | Fish market, boat yard, warehouse, net loft, quay cottage, harbour office house |
| T2 | +5.5 m | Plaza terrace | Plaza with well; general store, eatery, carpenter; 4 terrace houses |
| T3 | +10 m | Upper homes | West lane (3 houses), high row (4 houses) |
| T4 | +14.5 m | Civic shelf | Community hall, school, first-aid house, 2 shelf houses |
| T5 | +19 m | Crown | Cistern, lookout, crown cottage, great tree |
| Headland | +9 m | Lookout | Keeper's house, The Gate, beacon stack |

**30 buildings**: 10 public or commercial, 20 homes (21 households — the store has a flat above). 6 boats.

## Circulation (all generated from the walk graph)
| Link | Joins | Type |
|---|---|---|
| Harbour Stair | Quay → Plaza | Stone stair, 2.6 m wide |
| Back Stair | West quay → Plaza terrace | Timber stair |
| Quay ladder | North quay → terrace houses | Ladder shortcut |
| Plaza Stair | Plaza → High row | Timber stair |
| Store Steps | Plaza terrace → West lane | Timber stair |
| Hall Stair | High row → Civic shelf | Timber stair |
| Shelf Steps | West lane → Civic shelf | Timber stair |
| Crown Stair | Civic shelf → Crown | Timber stair |
| Lookout Stair | East quay → Headland | Timber stair |
| High Bridge | High row → Headland | Rope bridge, 19 m |
| Gate walk | Headland → Beacon stack | Path over the arch |
| Piers, boardwalk, slipway, spit path | Harbour | Decks and ramps |

Every level from T1 to T4 and the headland has two independent ways on and off. The Crown has one (see test result).

## Test results (`village/test_layout.py`, log in `evidence/logs/layout_test.json`)
- First run **FAILED**: one mooring sat under the stilt deck. Fixed. A zero-length door link was then found while building the overlay; fixed and a test added. Current run: **PASSED, 0 failures**.
- 30 buildings each fully on their own level, none overlapping.
- 122 walk-graph nodes, 126 links; 8 stairs, 1 ladder, 1 bridge.
- All 435 door-to-door pairs have a route. Mean 48 m; longest 119 m (warehouse ↔ crown cottage).
- No walking link crosses a building or leaves its terrace; all stairs between 25° and 45°.
- Removing any single stair, ladder or bridge isolates nothing except the Crown Stair, which cuts off the crown cottage. Accepted for now; a second crown route is an open design question.

What these tests do **not** show: that a character can physically walk it. There is no collision, no navigation mesh and no character yet.

## Known weaknesses of this layout (to resolve before production modelling)
1. The terraces are regular L-shaped steps. From the overview it reads as a ziggurat more than a wild cliff. Production cliffs need broken edges, overhangs, a gully or two, and uneven terrace heights.
2. Buildings sit in tidy rows facing two directions only. The reference's charm is overlap and rotation; rows need breaking up, with some houses turned, stacked or cantilevered.
3. The Gate stands at the front right and hides part of the east quay and warehouse from the default camera.
4. Only two building depths and one roof family for homes. Variety is colour only.
5. The hill has no caves, undercuts or boat shed under rock.
