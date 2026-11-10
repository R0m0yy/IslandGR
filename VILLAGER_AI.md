# VILLAGER AI — specification (not implemented)

## Data per villager
id, name, birth tick, sex, household, home, occupation + employer, personality (5 traits, 0–1: diligence, sociability, boldness, generosity, temper), preferences (foods, activities), needs, health, money share, skills (fishing, cooking, carpentry, trade, boat handling…), inventory, relationships map, memories list, current goal, plan (step list), location (node or in-transit), life history.

## Needs
Each 0–100 with a decay per sim-hour and a personal modifier: hunger, thirst, energy, hygiene, social, comfort, safety. Mood is derived, not stored.

## Decision: utility scoring
Every candidate activity returns a score: `urgency(need) × availability × personality fit × context`, where context includes time of day, weather, money, duty (work hours, childcare), and memory modifiers. The highest score wins, with hysteresis so a villager finishes what they started unless something scores at least 25% higher. Work is a duty with strong weight during hours — but a fisher at energy 15 and hunger 80 scores "eat" and "rest" above "go fishing", which is exactly the brief's example.

Candidates at first build: sleep, eat at home, cook, buy food, drink, wash, work (per occupation), sell catch, socialise, rest, shelter, repair, fetch supplies, child care.

## Execution
A chosen activity expands to steps: `navigate → reserve → align → act(duration) → apply effects → release`. Failure handling per step:
| Failure | Response |
|---|---|
| No path | mark destination unreachable for N hours, re-decide |
| Object taken | try another of the same type, else wait up to T, else re-decide |
| Missing ingredient or tool | insert fetch/buy sub-goal once; if that fails, pick next-best activity |
| Interrupted (weather, emergency) | release reservations, roll back partial effects, re-decide |
| Shop closed | remember hours, choose alternative |
Loop guard: the same failed goal cannot be re-chosen within a cooldown; three consecutive failures of any kind force the idle/rest fallback and log an AI-failure event that tests count.

## Memory
Capped list of `{tick, type, subject, valence, weight}`; weight decays; memories adjust relationship scores and activity context (e.g. avoiding a rival's stall, lending to someone who helped in a storm).

## Tests to write with the code (from the proof directive)
A hunger, B fatigue, C unsafe weather, D occupied object, E interruption, F off-screen continuity, G save/load mid-activity, plus the 3-day log and 7-day soak with counts of failed decisions, stuck agents and ledger imbalances. All run headless against the core.
