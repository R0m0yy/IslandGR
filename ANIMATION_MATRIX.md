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


## Session 5 update
- New clip `wave` (greeting): played when two friends (bond ≥ 30) meet, once per pair per day, from `Society._mingle`. That is a real event with a cause, not a random idle.
- `shoo` reuses `work`: played by whoever is at the stall or the boat when a gull raids.
- Boat crews now stand on the boat as it rides the shared wave surface (`Ocean.height`). Boats pitch and roll to the wave slope in `atmosphere.gd`.
- Animals are animated from simulation state (wing beats by species, folded wings when perched or diving, a dolphin breach arc, turtle surfacing, crab burrow retreat). They are placeholders, not final art.
- Still missing: carrying (nothing is visibly carried even though the ledger moves goods), boarding / disembarking, net handling, unloading crates, run, turn, stop.


## Session 7 update — hero villagers have real clips
The four hero villagers (A captain, B vendor, C elder, D child) now carry baked
keyframe animation on the shared 53-bone game rig (`blender/livingtides/characters/anim.py`,
24 fps, one glTF animation per clip, exported in `godot/assets/characters/<key>.glb`).
In Godot `HeroVillager` (`scripts/villager/hero_villager.gd`) plays them with the same
`play(clip)` contract as the placeholder, loops the cyclic ones, blinks every 2–6 s
and smiles while waving or offering fruit.

| Clip | Length | Loop | Motion |
|---|---|---|---|
| idle | 3.0 s | yes | breathing, weight shift, head looks around |
| walk | 1.0 s | yes | stride, knee flex in swing, pelvis bob/yaw/roll, counter-swinging arms |
| run | 0.66 s | yes | longer stride, high knees, pumping arms, forward lean |
| climb_stairs | 1.1 s | yes | knee lift, forward lean, bigger bob |
| climb_ladder | 1.2 s | yes | hands alternate up the rails, legs alternate |
| open_door | 1.2 s | no | reach, grip, push with a lean |
| cook | 1.4 s | yes | stirring circle, other hand steadies the pot |
| eat | 1.8 s | yes | seated, hand to mouth |
| sit | 4.0 s | yes | seated (pelvis drops by thigh length), breathing, looks around |
| sleep | 4.0 s | yes | lying on the back at bed height, slow breathing, eyes closed (Godot) |
| fish | 3.0 s | yes | both hands forward on a rod, small bobbing |
| work | 0.9 s | yes | hammer raise and strike |
| wave | 0.8 s | yes | raised hand waving (smile in Godot) |
| haul_rope (A) | 1.6 s | yes | hand-over-hand pull, leaning back |
| hand_fruit (B) | 2.6 s | yes | offers a mango, holds, takes it back; basket stays on the hip |
| mend_net (C) | 2.0 s | yes | knotting motions at chest height, head bowed |
| run_play (D) | 0.7 s | yes | skipping run with a hop |

Character holds are layered under every clip: B's left arm keeps the basket, C keeps
his stoop, cane and net, A and D keep the fish / bucket hand closed.

Status: clips exist and play in Godot (`tests/hero_test.tscn`). **UNVERIFIED:** how
they read in motion to a person (only still frames were reviewed). **Not done:** foot
IK on stairs (feet follow the clip, not the step heights), root motion, facial
lip-sync, using the hero models for the 42 simulated residents.

## Session 8 update — every resident animated, life clips
All 42 residents now use one of 14 crowd characters (`crowd.py`, V01–V14) and the four
heroes keep their own; every character carries the same 23 clips (A–D add their job
clip, so 24). `VillagerAnimator` plays them through a shared AnimationTree state machine.

| Clip | Length | Loop | Motion | Used by |
|---|---|---|---|---|
| give | 2.4 s | no* | take an item from the hip / counter, reach it out, hold, return | fish-market server and buyer, stallholders and customers (prop shown in hand) |
| carry | 1.0 s | yes | walk with both hands holding a load in front | crews unloading the catch (crate prop) |
| row | 1.8 s | yes | seated facing the stern: catch, drive, finish, recovery; oars follow the clip phase | skiff crews outbound / inbound |
| steer | 3.0 s | yes | seated at the stern, hand on the outboard tiller, looking ahead | fishing-boat helmsman |
| swim | 1.4 s | yes | front crawl at the waterline, flutter kick | swimmers off the spit |
| cast | 4.0 s | yes | back swing, flick, then wait with the rod | crew at the fishing grounds (rod prop) |
| haul_net | 1.5 s | yes | bent over the gunwale, hand over hand | crew at the fishing grounds, alternating with cast |
| sweep | 1.2 s | yes | broom strokes side to side | stallholders between customers (broom prop) |
| talk | 2.4 s | yes | gestures, head turns, weight shift | residents who meet within 3 m (both face each other) |
| play | 0.8 s | yes | hop and skip, arms high | children idling outdoors |
| run | 0.66 s | yes | as Session 7 | — |

\* looped in the tree, timed by the caller.

Reactions (`Villager.react`) no longer interrupt a crew at sea or a swimmer: a gull
pestering a boat used to make the helmsman stand up mid-voyage.

Status: PASSED for loading and playing in Godot (`tests/hero_test.tscn`,
`tests/life_capture.tscn` screenshots). UNVERIFIED: how the motion reads to a person in
real time. NOT IMPLEMENTED: foot IK, oar blades meeting the moving wave surface exactly
(the oars swing with the clip, the hull rides the swell).
