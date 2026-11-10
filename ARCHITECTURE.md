# TECHNICAL ARCHITECTURE — specification (no code exists yet)

## Principle
Two programs that share only data: a **simulation core** that knows nothing about graphics, and a **presentation layer** that draws whatever the core says is true. The core runs alone in tests.

```
 sim core (TypeScript, headless, deterministic, fixed tick)
   time · weather · world objects · villagers · needs · decisions · behaviours(logical)
   households · relationships · family/aging · economy · fishing · boats(logical) · wildlife(logical)
   events · save/load
        │  snapshots + event stream            ▲ player commands (pause, speed, select)
        ▼                                      │
 presentation (engine)
   rendering · animation · navigation paths→motion · camera/director · audio · UI
```

## Core rules
- Fixed tick (1 sim-minute); seeded random; identical seed + commands ⇒ identical history. Tests assert on this.
- Entities are plain data keyed by ID. Systems are functions over that data, run in a fixed order.
- All changes to money, inventory and stock go through one ledger function taking a source and a destination, so nothing is created or destroyed silently. An invariant test totals the world each tick.
- Every interaction is a state machine on an object: `free → reserved → in_use → free`, with timeout release.
- Events are records `{id, tick, type, actors, cause, effects}` appended to history; effects are the same ledger/state operations as anything else.

## Module list and interfaces
| # | Module | Owns | Talks to |
|---|---|---|---|
| 1 | World Simulation | tick loop, system order | all |
| 2 | Villager Data | identity, traits, skills, memories | 3–5, 9–11 |
| 3 | Needs | hunger, thirst, energy, hygiene, social, safety, mood | 4 |
| 4 | Decision AI | utility scoring, goal choice | 3, 5, 9–13, 16 |
| 5 | Behaviour Execution | step sequences, reservation, recovery | 6, 8 |
| 6 | Navigation | walk graph, path queries, travel time | 5, 14 |
| 7 | Animation | clip state machine, IK (presentation only) | 5 via step events |
| 8 | Interaction Framework | object definitions and states | 5, 22 |
| 9 | Household | shared money, pantry, chores | 12 |
| 10 | Relationships | pair scores, reputation | 4, 23 |
| 11 | Family & Aging | births, life stages, death, inheritance | 9, 10 |
| 12 | Economy | ledger, prices, businesses | 9, 13 |
| 13 | Fishing | stocks, catch resolution | 12, 14, 16 |
| 14 | Boat Navigation | sea lanes, boat state, damage | 6, 13, 16 |
| 15 | Wildlife | flock/crab/fish agents | 16, 17 |
| 16 | Weather | state machine, sea state, wind | 4, 13–15 |
| 17 | Time | clock, calendar, seasons | all |
| 18 | Audio | event-driven emitters (presentation) | 23 |
| 19 | Rendering | scene, lights, water, LOD | snapshots |
| 20 | Camera | modes, director | 23 |
| 21 | UI | inspectors, time controls | snapshots, commands |
| 22 | Save/Load | versioned schema, validation, migration | core state |
| 23 | Event History | append-only log, queries | all |
| 24 | Debug & Test | scenario runner, invariants, soak tests | core |

## Level of detail for simulation
One logical simulation for everyone, always. Presentation chooses how much to show: on-screen villagers get paths and animation; off-screen ones are not drawn. A behaviour step has a duration and an outcome that do not depend on being watched; when a villager comes into view mid-step, presentation starts the clip at the matching time offset.

## Navigation
Authored walk graph exported from Blender (nodes on paths, stairs, ladders, doors, dock edges, boat boarding points), with edge types `walk | stair | ladder | door | board`. The core uses it for reachability and travel time; presentation uses the same graph for motion. A test walks every door-to-door pair.

## Interaction object definition
`{id, type, slots:[{standPos, facing, anim}], states, transitions, requires, produces, duration, interruptible, audio, vfx}` — one JSON entry per object type; instances carry state and reservation.

## Save format
JSON, `{schemaVersion, seed, tick, ...}`; validated against the schema on load; rejected with a clear error on failure, never partially applied; migrations per version step. Mid-activity saves store the behaviour step index and elapsed time.

## Performance plan
Budgets are placeholders until measured on real devices: target 60 fps desktop / 30 fps phone, sim tick under 2 ms for 60 villagers. Instancing for repeated props, merged static geometry per terrace, shadow map over the visible area only, animation updates throttled by screen size.
