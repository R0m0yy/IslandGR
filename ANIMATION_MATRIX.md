# ANIMATION MATRIX — contract + placeholder implementation

Status: **implemented on a TEMPORARY primitive rig** (`godot/scripts/villager/villager_animator.gd`). Final character art is undecided; nothing below depends on it. The clip names are the contract: a real character supplies an `AnimationPlayer` with these names and the rest of the game is unchanged.

| Clip | Loop | Used by state | Trigger | Placeholder motion | Verified |
|---|---|---|---|---|---|
| `idle` | yes | `idle`, `shop` | waiting, between steps | arm sway, breathing bob | clip exists (Godot test) |
| `walk` | yes | `walk`, `cross_bridge`, `open_door` (second half) | link type walk / door / ramp / archwalk / interior / bridge | leg + arm swing, bob | exists; state machine travel tested |
| `climb_stairs` | yes | `climb_stairs` | link type `stair` | higher knee lift, forward lean, slower | exists; 2,539 uses in the 5-day run |
| `climb_ladder` | yes | `climb_ladder` | link type `ladder` | arms overhead alternating, legs alternating | exists; 196 uses |
| `open_door` | no (held) | `open_door` | link type `doorway` | right arm reaches, lean | exists; 1,564 uses |
| `cook` | yes | `cook` | using a stove | stirring arm, lean | exists |
| `eat` | yes | `eat` | using a chair / table with a meal | seated, hand to mouth | exists |
| `sit` | yes | `sit` | resting at home | seated | exists |
| `sleep` | yes | `sleep` | using a bed | lying, slow breathing | exists |
| `fish` | yes | `fish` | using a fishing spot | arms forward, rod shown | exists; visible in `G04_pier_fishing.png` |
| `work` | yes | `work` | using a work station | hammering arm | exists |

Blending: `AnimationTree` → `AnimationNodeStateMachine`, one node per clip, cross-fade 0.18 s between every pair. Every clip keys every track so blends never leave a limb behind.

**Not verified:** how any of this looks in motion (no one has watched it run). **Not implemented:** carrying, rowing, talking, child/elder variants, IK foot placement on stairs, facial animation.
