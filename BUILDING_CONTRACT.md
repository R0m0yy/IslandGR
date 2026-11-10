# BUILDING CONTRACT — how every building plugs into the living world

Status: **design + data stubs.** The fields exist for all 30 buildings in `data/village_layout.json`; nothing behind them is implemented.

A building is not approved as a production asset unless it satisfies every row below. This is the guard against a pretty village that has to be rebuilt for residents.

| Connection | In the data now | In the Blender asset (when modelled) | In Godot (when built) |
|---|---|---|---|
| Interior rooms | `interior.rooms` list per building, from a template per building type | Real floor, inner wall faces, room dividers; walls split into named groups `WALL_S`, `WALL_E`, `WALL_N`, `WALL_W`, `ROOF` so any side can fade | Cutaway controller fades the camera-facing groups and lifts the roof |
| Walkable navigation | `door` position, `access_node` into the walk graph; tested for reachability | Door opening ≥ 0.9 m; floor at threshold height; interior floor is a navigation surface; interior stairs for two-storey homes | Navigation region per building joined to the terrace region at the door |
| Furniture interaction points | `interior.anchors[]` — 368 stubs in total (bed, stove, sink, table, chair, cabinet, storage, lamp…) with `pos` and `facing` still null | One empty per slot named `IA_<object>_<slot>`: where the villager stands and which way they face; object pivots at hinges | Markers read on import; each becomes a reservable interaction slot |
| Household ownership | `household {id, capacity, shared_money, pantry, members}` on every home | — | Household record in the simulation; building holds only the ID |
| Resident schedules | Not in the data. Schedules belong to villagers and come from needs + job hours, not from buildings | — | Simulation |
| Jobs | `business {owner, jobs[role, holder], hours, inventory, till}` on 10 buildings; `job` on 6 boats. 24 job slots against 70 beds — intended: children, elders and home-keepers do not hold jobs, but the ratio needs tuning | Work stations are anchors like any other | Job board in the simulation |
| Resource inventories | `pantry` per household, `inventory` and `till` per business, `cargo` per boat — all empty | Storage objects have an anchor | All movement through the single ledger function |
| Persistent world state | `state {condition, lights_on, door_open}` per building; `condition` per boat | Damage states as swappable mesh variants later | Saved with the world; lamps and windows read `lights_on` |

## Rules that follow
- Building exteriors are modelled around their interior footprint, not the other way round. Minimum clear interior: 3.2 × 3.0 m for a one-room home.
- Wall thickness 0.15 m; door swing clear; one window per room on a camera-facing wall so interiors read at night.
- No building may be placed, moved or resized in Blender alone. The change is made in `village/layout.py`, the tests are re-run, and Blender follows the data.
- Lamps and lit windows in the current night render are a render-time switch on all windows at once. In the game they will follow `state.lights_on` per building.
