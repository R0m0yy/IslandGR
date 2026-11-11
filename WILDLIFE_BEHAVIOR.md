# WILDLIFE BEHAVIOUR

Saltcrown is a **tropical reef coast** (palms, coral-pink rock, warm shallows). Species were chosen to fit that habitat. **Seals and sea lions are deliberately absent**: they belong to cold, nutrient-rich coasts, and a tropical island with them would need a design explanation we do not have. The habitat reasoning is general knowledge; no field source was consulted in this session (web access is blocked).

All animals are simulated in `godot/scripts/sim/ecosystem.gd`: each has a position, a state, hunger or size, and its own rules. `godot/scripts/world/atmosphere.gd` only draws them, as simple placeholder shapes, not final art.

| Species | Simulated state | Rules | Links to other systems |
|---|---|---|---|
| **Scad** (small schooling fish) | school size, position, heading, flee timer, deep flag | travel a ring of sea waypoints; regrow ~3 %/h of capacity (× `fertility`); bolt and reverse from predators and boats under way; go deep in rough water | eaten by barracuda, dolphins, pelicans, terns; caught by boats |
| **Snapper** (reef fish) | same | slower; hold near their home ground (often turn back) | caught by boats |
| **Mackerel** (open water) | same | fastest | dolphins, boats |
| **Barracuda** ×2 | hunger, state prowl / hunt | hungry above 55: hunt the nearest school, spook it at 9 m, take up to 3 fish on contact | reduces fish for fishing |
| **Bottlenose dolphins** (pod of 4) | pod position, hunger; per-animal breach timer | travel the outer ring; hungry above 60: chase a scad or mackerel school and feed; breach more while feeding | reduces fish; scatters schools |
| **Green turtles** ×2 | dive timer | dive 25–50 min, surface 1.5 min to breathe, wander the ring | observable |
| **Ghost crabs** ×7 | hidden / forage / bolt, burrow | out on the spit around dusk and dawn (17:30–06:30) when dry; shuffle near the burrow; bolt home if a person comes within 3 m | react to residents |
| **Gulls** ×5 | hunger, roost, patrol / raid / flee, carry | hungry above 45 leave the roost to patrol the harbour; above 55 they raid **exposed fish**: the scrap heap first (no one minds), else a boat being unloaded or the market stalls. Success 80 % if unattended, 32 % if someone is there, bolder when hungrier. A success removes one fish **from the right Ledger account**, the person present reacts and remembers it, the journal records it with the cause, and nearby gulls get excited. Failure sends the gull off with a 90 s cool-down. **After a theft the stall or boat is vigilant for 2 hours** (fish covered, birds waved off: 6 % success), so raids do not cascade | Ledger, villagers' memories, journal |
| **Brown pelicans** ×2 | hunger, search / dive / climb | plunge-dive on visible (not deep) schools; 55 % success, 2 fish | reduce fish |
| **Terns** ×3 | same | smaller, faster dives on scad only; carry the fish | can be robbed by the frigatebird |
| **Magnificent frigatebird** | soaring, hunger | soars high; when hungry, harries any bird carrying a fish until it drops it | kleptoparasitism |
| **Sandpipers** ×3 | forage / flush | run and probe along the tideline of the spit; flush and resettle if a person comes near | react to residents |

**Weather and night:** in storms or heavy rain every bird returns to its roost, and crabs stay in their burrows in rain. At night birds roost (sandpipers keep working the tideline). Fish go deep in rough water, which hides them from diving birds.

**Fishing depends on wildlife:** boats take their catch from the same schools. Predators, birds and fishing pressure all reduce the stock, and a poor season (lower `fertility`) cuts landings. Scenario F measured this: see `QA_REPORT.md`.

**Not implemented:** reef fish visible in the shallows by the docks, sharks, rays, octopus, wildlife bait-taking from lines, schools reacting to the tide, bird nesting / seasons.
