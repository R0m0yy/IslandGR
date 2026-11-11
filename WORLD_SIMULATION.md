# WORLD SIMULATION

How Saltcrown lives. Every system below is GDScript in `godot/scripts/`, runs headless, and is exercised by `godot/tests/test_runner.gd` (regression) and `godot/tests/living_world_test.gd` (scenarios A–G, Y, P). Test status is in `QA_REPORT.md`; this file describes design.

## The one rule
Every meaningful activity has a **cause** (a need, an obligation, a relationship, the weather), a **decision** (utility scoring in `brain.gd`), a **physical action** (walking the walk graph, using an object, sailing a lane), a **state change** (needs, the Ledger, object state, positions), and **consequences** that other agents can see (stock on a stall, an empty larder, a damaged roof, a memory, a journal entry).
No animation changes the world by itself. The ledger and the needs are changed only by the state that owns the action.

## Systems and ownership
| System | File | Owns | Reads |
|---|---|---|---|
| Clock & calendar | `core/game_clock.gd` | minutes, day, hour; `minutes_per_second`, `speed` | — |
| Weather | `sim/weather.gd` | state (clear · cloudy · light rain · heavy rain · storm), cloud / rain / wind, hourly transitions, `storm_risk()`, per-resident `forecast()` | clock |
| Ocean | `sim/ocean.gd` | wave height & slope (same formula as `shaders/ocean.gdshader`), tide, roughness | wind |
| Ecosystem | `sim/ecosystem.gd` | fish schools, barracuda, dolphins, turtles, crabs, birds | weather, boats, villagers, Ledger (thefts) |
| Ledger | `sim/ledger.gd` | every account's money and goods; the transaction log; `audit()` | — |
| Economy | `sim/economy.gd` | prices, wages, levy, credit, gifts, spoilage, bait chain, repairs, ownership, succession | Ledger, buildings |
| Society | `sim/society.gd` | friendship bonds, partnerships, births, ageing, illness, retirement, death, estates, newcomers; demography settings | villagers, Ledger |
| Journal | `sim/journal.gd` | the world's history (typed entries with actors and cause) | written by every system |
| Residents | `villager/villager.gd`, `brain.gd`, `states/*` | needs, traits, skills, ambition, memories, plan, position | everything above |
| Boats | `sim/boat.gd` | boat state, route, condition | ocean, weather |
| Buildings | `world/building.gd` | interactables, door, lights, condition | — |
| Persistence | `sim/save_game.gd` | versioned snapshot (v3) and migrations 1→2→3 | all of the above |
| Observer | `camera/orbit_camera.gd`, `ui/hud.gd`, `world/atmosphere.gd`, `world/day_night.gd` | presentation only | read-only |

## A resident
**Persistent state:** id, name, age (life stage derived: infant <5, child <16, adult, elder ≥65), household (= Ledger account), home, bed, job, partner, parents, children; needs (hunger, thirst, energy, hygiene, social) and health; derived mood; traits (diligence, sociability, generosity, boldness); ambition (provide · family · wealth · sea); skills (fishing, cooking, trade, carpentry: they grow with use); memories (≤30 significant events with valence); illness days; a plan; a walk-graph position.

**Decision** (`brain.gd`): each candidate activity is scored from needs, the hour, the weather, the household's pantry and purse, the job and shift, the life stage, traits and ambition, then expanded into steps (`go` · `use` · `gift` · `repair` · `cut_bait` · `idle`). Failed goals go on cooldown, so no task repeats forever.
Candidates: sleep, eat, eat out, drink, wash, cook (for the hungriest member of the household), buy food, buy bait, cut bait, boat trip, hand-line fishing, mend nets, work, repair storm damage, give food to a neighbour in need, stroll (sunset walks, children watching the boats go out), rest at home.

**Interruptions**: heavy rain sends outdoor walkers home (`seek_shelter`). A storm turns boats back, and a fisherman who reaches the boat as a storm breaks does not cast off. Illness keeps people home. A failed object use or path releases reservations and re-decides.

## A fisherman's day (as simulated)
1. Wakes (personal offset ±1 h), eats; cooks for the household if the larder has fish but no meals.
2. On shift, reads the sky: `Weather.forecast(skill)` is the true storm risk blurred by inexperience. If it is above a threshold set by boldness, he stays ashore (journal entry).
3. With no bait he buys it at the general store (P05). If the shop is out, he cuts bait from a fish at home; with no fish either, he hand-lines from a pier.
4. If the market is glutted and his larder is full, he mends nets instead (boat condition up).
5. Walks to his mooring, checks the sky again, consumes 1 bait, casts off and sails the sea lane to his ground (The Gate route for the reef ground).
6. Fishes every 10 minutes: success depends on the fish actually in the schools near the ground (`Ecosystem.biomass_near`), his skill, and the sea state. Fish are taken from those schools. Cargo is capped by the hull.
7. Returns when full, after his patience runs out (longer for "sea" ambition), on an empty ground, when hungry or tired, or ahead of a storm.
8. Moors and unloads for 15 minutes; **gulls may steal from the open catch**. Sells to the market at the scarcity price while it can pay and has room; the rest goes home.
9. Rough water adds wear. Below 60 % condition he pays the boat yard for a repair.
10. Skills rise with every fish; memories record full boats, empty boats and storms.

## Day length and generational pace (settings)
| Setting | Where | Default | Meaning |
|---|---|---|---|
| `GameClock.minutes_per_second` | autoload | 1.0 | game minutes per real second at ×1 |
| speed keys | HUD | ×1 ×4 ×16 ×60 | |
| `Society.days_per_year` | society | 28 | game days per year of a life (28 → a resident lives ~5 real hours at ×60) |
| `Society.settings` | society | see below | demography: fertile ages, birth rate per fertile year, birth gap, pairing bond, old age, illness per day, immigration on/off, vacancy years |

## Off-screen simulation
There is one logical simulation for everyone. Rendering is the only thing that differs: `atmosphere.gd` and the animator draw what exists, and `Village.set_figures_visible(false)` hides the temporary figures without touching the simulation. Per-agent detail levels (thinning far-away updates) are **not implemented**: all 40–60 residents tick every 0.1 s step. Measured cost: see `QA_REPORT.md`.
