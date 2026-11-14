# Response to the Living Tides audit of 1741f7d

Statuses use the project's words: PASSED (ran here and passed), UNVERIFIED (not measurable here),
NOT IMPLEMENTED. Test numbers are in the last section.

| Audit finding | What was done | Status |
|---|---|---|
| **P0** hosted build seems stuck loading | The start card had no real progress: the bar only moved after the whole 47 MB had arrived. It now shows three named steps with megabytes downloaded, and stays up until the game prints `LT_READY`, which it does only when the village is built, a frame has been drawn and the clock has moved. A hint appears after 45 s on a slow device. `tools/build_web.sh` now generates the page, so part counts and sizes cannot go stale. | PASSED in Chromium software WebGL; UNVERIFIED on the owner's device |
| **P0** clock crawls at low frame rate | The simulation was driven from physics ticks, which Godot caps per frame; at 1 fps the clock ran about 20x slow. It is now driven per rendered frame and catches up to one second of real time each frame. | PASSED (`tools/web_smoke.js` clock check) |
| **P0** lighter web preset | The game measures its own frame rate and steps quality down (render scale, shadows, glow, light shadows, character budget, wildlife) in three levels when below 20 fps. Hidden characters no longer animate or ray-cast. Download size is unchanged (characters are 27 MB of 42 MB; no single wasteful part was found). | PASSED for the mechanism; real-device frame rate UNVERIFIED |
| **P1** followed resident hidden by a roof | Following a resident who is indoors opens that building (roof and camera-facing walls, tracking the orbit) and closes it when they leave or the follow ends. New test `tests/follow_test.tscn`. | PASSED 8/8, screenshot `evidence/renders_follow/F01_followed_indoors.png` |
| **P1** residents beyond the 20 nearest vanish | Nobody is hidden any more. Residents over the budget are drawn as a simple stand-in figure in their own clothing colour and height; the followed resident is always a full character. | PASSED (follow_test budget checks) |
| **P1** stall trade is cosmetic | A handover at a quay stall is shown only for a real sale: the fish stall sells the market's fish, the fruit and bread stalls sell the eatery's take-home food; goods and money move in the ledger. | PASSED by code path; not covered by a headless test (stalls are presentation objects) |
| **P1** hero villagers and stallholders are not simulated residents; plane and yacht are ambience | Unchanged. The four heroes wait for character approval before they replace real residents. | NOT IMPLEMENTED |
| **P1** 42% of work unpaid | Rule defined: a wage the employer cannot pay on the day is owed, not lost. Claims are kept per employer and household, settled oldest first from the till, then by the council above its reserve; shown in the resident inspector ("is owed N in wages") and the journal; saved and loaded. Rebalanced so they do get settled: wage 4 to 3 per block, harbour dues scale with savings (8% above 50, nothing for the poorest), dues are not waived while wages are owed. | PASSED: 624 owed over 7 days, 553 settled, 71 (11%) outstanding; regression check added |
| **P1** people pass through one another | Residents on foot who stand within arm's reach are drawn a step apart (figures only; routes and timings unchanged). | PASSED by inspection of code; no queueing at doors, no person/boat collision, no foot IK: NOT IMPLEMENTED |
| **P2** memories not used in decisions | `feeling(type)` sums remembered events with recency. A storm remembered makes the same sky look riskier for weeks; full or empty boats raise or lower the wish to sail; having been helped raises the wish to help. A kindness received becomes a held commitment (kept up to 40 days, saved, shown in the inspector) that is acted on when there is food to spare. Important memories are no longer pushed out by everyday ones. | PASSED (3 new regression checks) |
| **P2** longer plans (saving, job seeking, avoiding a ground) | Only the repay commitment exists. | NOT IMPLEMENTED |
| **P2** art direction against the reference | Not started; it needs the owner's approval of a direction first. Rower's hands and oar alignment unchanged. | NOT IMPLEMENTED |
| **P2** fish_bought / fish_sold counters always zero | Now updated per resident. | PASSED by code path |
| **P2** non-finite normal warning on import | Source mesh not located. | NOT IMPLEMENTED |
| Browser smoke gate | `tools/web_smoke.js`: waits for `LT_READY`, requires a real picture (distinct colours) and a clock that advances. | see results |

Found while fixing: large households went hungry with food in the larder because one fish (three
meals) was cooked at a time and every chair was taken. A cook now fills the pot for the whole
household, starts before the last meal is gone, and a resident with no free chair eats on the
edge of their bed.
