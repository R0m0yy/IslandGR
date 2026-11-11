# Living Tides — Godot project

Godot **4.3** (Forward+ by default; also runs with `--rendering-method gl_compatibility`).
Open `project.godot`, press Play. Main scene: `scenes/main.tscn`.

**Verified here:** headless import, 31 headless tests, 9 software-OpenGL screenshots.
**Not verified:** Forward+ on a GPU, keyboard/mouse input, frame rate, any export.

## Controls (untested by a person)
Right mouse drag orbit · wheel zoom · WASD pan · Tab follow next villager · Esc release · C cutaway (the followed villager's building, or all) · 1/2/3/4 speed ×1 ×4 ×16 ×60 · Space pause.

## How it is put together
```
autoload  GameClock    world time (1 real second = 1 game minute at ×1)
autoload  VillageDB    reads res://data (copy of /data - never edit the copy)

scenes/main.tscn → scripts/world/village.gd  (class Village) builds everything at runtime:
  Environment     assets/env/*.glb + sea plane (shaders/ocean.gdshader)
  Buildings       30 × Building  (assets/buildings/<ID>.glb + data/buildings/<ID>.json)
                    wall groups WALL_S/E/N/W, ROOF, FLOOR2  → cutaway
                    DOOR_main   → Door (hinge pivot)
                    anchors     → Bed, CookingStation, Interactable, lamps
                    interior walk graph stitched to door_<ID>
  Outdoor         FishingSpot ×4, street lamps, landmark lights
  NavGraph        village graph (122 nodes) + every interior; typed links; A*
  Simulation      fixed 0.1 s steps; advance(seconds) for tests
  Villagers       42 × Villager (PLACEHOLDER figures)
  DayNight, CameraRig, HUD   presentation only (skipped in logic tests)
```

### Villager
`scripts/villager/villager.gd` — needs (hunger, energy) → `brain.gd` scores activities (sleep, eat, cook, fish, buy_food, work, stroll, rest_home) and returns steps → `state_machine.gd` runs one `VillagerState` at a time:

| State | Class | Entered when |
|---|---|---|
| idle | `IdleState` | waiting / between steps |
| walk, climb_stairs, climb_ladder, cross_bridge | `LocomotionState` | chosen from the type of the walk-graph link being travelled |
| open_door | `OpenDoorState` | link type `doorway`: open, wait for the swing, walk through |
| sleep, cook, eat, fish, work, sit, shop | `UseObjectState` subclasses in `states/activities.gd` | plan step `use` on an Interactable |

Adding an activity = one `UseObjectState` subclass + one scoring line and one plan in `brain.gd`.

### Replacing the placeholder character
`villager_animator.gd` builds a primitive figure and an `AnimationTree` over eleven clip names (`ANIMATION_MATRIX.md`). Swap the rig and supply clips with the same names; no other script refers to the figure.

### Tests
```
godot --headless res://tests/test_runner.tscn -- --days=5 --out=/abs/path/results.json     # exit code 0 = pass
xvfb-run -s "-screen 0 1600x900x24" godot --rendering-method gl_compatibility --rendering-driver opengl3 \
    res://tests/capture.tscn -- --out=/abs/dir                                              # screenshots
```
