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


## Session 4 update
- The rig is now a single **neutral grey mannequin** for every resident (no faces, hair, outfits or colours). It can be hidden (`Village.set_figures_visible(false)`, key V); the simulation is unaffected. Character art is frozen.
- New villager states and the clips they reuse: `fish_trip` (sit → fish → sit → work), `drink` (eat), `wash` (cook), `shop` (idle). They need their own clips when a real rig exists.

| Required by the directive | Clip exists | Notes |
|---|---|---|
| idle, walk, climb stairs, climb ladder, open door, sit, sleep, cook, eat, work at a table, cast / hold a line | yes | placeholder keys |
| run, turn, stop, stand up, wake up, close door | **no** | walk covers all movement; doors close by themselves |
| board / disembark boat, carry, unload boat, carry crates, handle nets, pull lines | **no** | boarding is a teleport onto the boat; nothing is carried visibly |
| drink, clean, wash, use storage | **no** (reused clips) | — |
| market stall, exchange goods, repair boat, construction | **no** (generic `work`) | — |

Objects do not yet attach to hands, so nothing is shown being carried - the simulation moves goods through the ledger without a visible prop. That mismatch is a known gap, not a claim.
