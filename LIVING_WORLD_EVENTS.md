# LIVING WORLD EVENTS

The journal (`godot/scripts/sim/journal.gd`) is the world's history. An entry exists only because simulation state changed: it is written by the system that changed it, names the residents involved (`actors`), says why (`cause`), carries the game time and, where useful, a position. Notable entries (★) feed the cinematic camera and the toast line.

| Type | Written by | When (cause) | Notable |
|---|---|---|---|
| `fishing` | boat trip, brain | full boat; empty boat; turned back by a storm; stayed ashore after reading the sky; did not cast off at the mooring | full boats and storm turn-backs |
| `wildlife` | ecosystem | a gull steals a fish (with the gull's hunger and whether the fish was guarded); a frigatebird robs another bird | gull thefts |
| `weather` | village | storm breaks; heavy rain sets in; weather clears | storms |
| `damage` | village | a storm tears roof sheets from a building (condition 60 %) | |
| `repair` / `community` | economy | a carpenter mends storm damage (paid, or free when the household cannot pay) | free repairs |
| `community` | economy | a neighbour brings food to a household with nothing; the market lets a family take fish on credit | gifts |
| `economy` | economy | a debt is settled; a business cannot pay wages for 4 days; it recovers | struggling business |
| `business` | economy | ownership passes to a child or a colleague; or no one is left to run it | yes |
| `birth`, `death`, `partnership`, `estate`, `newcomers` | society | demography rules (see WORLD_SIMULATION.md) | yes |
| `came_of_age`, `hired`, `retired`, `moved`, `illness`, `recovery` | society, village | life stages, job choice (a parent's trade pulls), moving into a free bed or an empty house | |

Each life event is also written into the residents' **memories** (with a valence) and so appears in the resident inspector. The **people registry** (`Village.people`) keeps everyone who ever lived, including the dead, so family trees and household histories stay complete across generations. Journal, memories and the registry are saved (save format v3).

## Observer
| Key | View |
|---|---|
| J | journal: all → notable → the followed resident → off |
| T | the followed resident's timeline |
| F | family tree: grandparents, parents, siblings, partner, children, grandchildren (dead marked †) and the household's history |
| I | village inspector: population, food, prices, wealth spread, debts, gifts, boats, fish in the sea, gull thefts, weather and storm risk, moon phase, births and deaths |
| click a building | household / business: residents, purse, pantry, owner, staff, till, stock, struggling days, who is inside |
| K | cinematic mode: slow drift, cutting to the newest notable event every 30 s |
| G / N / B / Tab | follow a household / wildlife / a boat / a resident |
| H | hide all UI |
