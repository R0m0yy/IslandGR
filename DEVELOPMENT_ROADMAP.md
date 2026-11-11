# DEVELOPMENT ROADMAP

Phases follow the owner's directive (Part 22). Status is what has been executed, not what is planned.

| Phase | Scope | Status | Gate |
|---|---|---|---|
| A | Project recovery, baseline, audit | **Done** (`QA_REPORT.md`) | — |
| B | Visual-quality foundation: representative district | **Built, not approved** | **Owner approval of the district** |
| C | Roll the approved language across the village; layout v0.3 | Kit improvements already apply village-wide; layout revision not started | After B |
| D | Functional environments: interiors, entrances, household support | First version done; storage, cabinets, cleaning missing | — |
| E | Resident simulation | First version done (5 needs, traits, routines, interruption by storm) | — |
| F | Fishing and transport | Logic done; presentation and gear missing | — |
| G | Economy | First closed loop done; needs tuning and more goods | — |
| H | Social and generational | First version done; population not self-sustaining (**FAILED** test) | — |
| I | Environmental life: weather, wildlife, foliage, ocean, audio | Started; all presentation **UNVERIFIED** on real hardware | Needs a GPU session |
| J | Integration, optimisation, playable build | Tests in place; no GPU profiling, no export | Needs a GPU + export templates |
| K | Final character art | **BLOCKED until the owner approves character designs** | Owner |

## Next, in order
1. **Owner review of the district** (`evidence/renders_village_v04/D01-D05`, golden and night variants, `evidence/renders_godot_v04/E03, E04, E07`). Nothing more is multiplied across the village until this is answered.
2. Layout v0.3 in `village/layout.py`: stagger and overlap houses, platforms cantilevered past the rock, uneven terrace heights, second route to the crown. Rebuild from data.
3. Architecture: more roof forms (mono-pitch, hip, lean-to stacks), a sixth "hillside residence" family, verandas, external stairs; soften strata contrast.
4. Demographics: more beds per home or a children's room; pairing through shared activities; make the 45-year test pass.
5. Villager depth: skills, preferences, memories, goals; tests A-G from `VILLAGER_AI.md`; shelter-seeking; queueing; residents avoiding each other.
6. Economy depth: more goods (bread, timber, nets), shop opening hours per business, price model beyond three steps, household emergencies.
7. Boats: fuel or rations, gear pickup, docking manoeuvre, collision avoidance, wake.
8. Storage / cabinet inventories, cleaning, lamp switching as interactions; wall fade instead of hide.
9. Audio from licensed or recorded sources; footsteps by surface; spatial emitters.
10. GPU session: Forward+ look, lighting, sea, performance budget, input test, short captured play session.
11. Export templates → desktop build.
12. Character concepts for the owner to compare (only when asked).
