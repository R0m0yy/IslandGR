# KNOWN ISSUES
| # | Area | Issue | Severity |
|---|---|---|---|
| 1 | Tooling | Blender unavailable in session 1; whole Blender pipeline unproven | Blocker |
| 2 | Tooling | No engine installable in session 1 | Blocker |
| 3 | Research | Behance, ArtStation, Dribbble pages not opened directly; Dribbble palette unread; Old Dock and Watermill pages unread | Medium |
| 4 | Test scene | Ladder clips through cliff | Low (test asset) |
| 5 | Test scene | Day water too bright; shoreline band flat | Low |
| 6 | Test scene | Night preset under-contrasted | Low |
| 7 | Test scene | Cliff shape generic (ring-lofted) | Medium — the approach will not reach the reference; cliffs need hand modelling |
| 8 | Test scene | No UVs, collision meshes, per-object pivots | Medium |
| 9 | Measurement | Viewer frame timing not credible under software GL | Medium |
| 10 | Massing | Terraces are regular L-steps; reads as a ziggurat | High (design) |
| 11 | Massing | Buildings in rows facing only south or east; no rotation, stacking or cantilever | High (design) |
| 12 | Massing | The Gate hides part of the east quay and warehouse from the default camera | Medium |
| 13 | Massing | One boat shows a stray white block (cabin offset wrong) | Low |
| 14 | Massing | Terrace tops too pale; dominate the palette in daylight | Low |
| 15 | Layout | Crown cottage has a single access route | Low (decision) |
| 16 | Layout | 24 job slots vs 70 household beds — ratio untuned | Medium (sim design) |
| 17 | Docs | ART_BIBLE §2 and ASSET_MANIFEST still reflect layout v0.1 | Medium |
| 18 | Preview | Night preset lights every window; not driven by state | Low |

## Session 3 updates
| # | Area | Issue | Severity |
|---|---|---|---|
| 1, 2 | Tooling | **Resolved here:** Blender (bpy 4.5.15 LTS) and Godot 4.3 headless both run. Still no GPU, no Blender app binary | — |
| 10 | Terrain | Partly addressed: cliff lips, ledges and rock masses are irregular; the terrace *plan* is still the L-shaped steps | High (design) |
| 11 | Layout | Unchanged: rows facing S or E. Needs a layout revision in `village/layout.py` | High (design) |
| 17 | Docs | ASSET_MANIFEST re-keyed; ART_BIBLE §2 still v0.1 | Low |
| 18 | Lighting | Resolved in Godot: lights follow occupancy per building | — |
| 19 | Godot | Forward+ renderer, input, HUD and performance never run on a GPU | High (unverified) |
| 20 | Godot | ~295 `Parameter "m" is null` messages at headless shutdown; cause unknown | Low |
| 21 | Godot | Importer adds a numeric suffix to some node names (`P01_ROOF2`); handled in `building.gd`, cause not understood | Low |
| 22 | Sim | Needs, scores, durations and the fish market are first-guess numbers | Medium |
| 23 | Sim | Villagers pass through each other; no collision, no queueing at doors | Medium |
| 24 | Sim | Sleeping pose places the placeholder figure roughly on the bed, not fitted | Low |
| 25 | Assets | GLBs unwelded and large (43 MB total); no LODs, no instancing | Medium |
| 26 | Assets | One anchor stub unplaced (P06 third table) | Low |
| 27 | Assets | Vegetation placement ignores canopy size; a tree can crowd a house | Low |
| 28 | Assets | No caves, undercuts or boat shed under rock (layout weakness 5) | Medium |
| 29 | Architecture | Sim core is GDScript, not the TypeScript core specified in ARCHITECTURE.md - decision pending | Medium |

## Session 4 updates
| # | Area | Issue | Severity |
|---|---|---|---|
| 10, 28 | Terrain | Addressed: sculpted island with undercut, overhangs and 10 caves. Terrace *plan* still L-shaped | Medium (design) |
| 11 | Layout | Rows remain; only a ≤5° turn per building was added | High (design) |
| 23 | Sim | Still open: residents pass through each other; no queues | Medium |
| 25 | Assets | Island is now 38k tris / 4.6 MB (was 100k / 12 MB for terrain + cliffs). Buildings grew to 390k tris with dressing; still no LODs or instancing | Medium |
| 30 | Visual | Rock strata first read as a regular "layer cake" in Godot; beds were made thicker and uneven and ledge grass cut back (see `E06_cliffs_west.png`). Still blocky in places; needs an art pass | Low-Medium |
| 31 | Visual | 16k of the island's 38k triangles are under water | Low |
| 32 | Visual | Sea under the stilt deck shows a dashed pattern (depth-map sampling against jittered facets) | Low |
| 33 | Visual | Homes still share one roof family; no overlap or cantilever like the benchmark | High (art) |
| 34 | Sim | Population is not self-sustaining over generations (42 → 15 in 45 years) - **FAILED test** | High |
| 35 | Sim | Fish supply far exceeds demand (about 1,200 caught vs 270 cooked per week); market caps at 60 and the rest piles up in pantries | Medium |
| 36 | Sim | 51 of 468 wages unpaid in the 7-day run: council income still short | Medium |
| 37 | Sim | After a load, activities restart from the last walk node; a boat at sea is returned to its mooring | Low (documented behaviour) |
| 38 | Sim | Friendship grows from proximity only; no rivalry, conflict, ceremonies or shared-activity bonding | Medium |
| 39 | Sim | No skills, preferences, memories or personal goals yet | Medium |
| 40 | Sim | Children share a parent's bed and "play" at the door; no schooling, no parenting tasks | Medium |
| 41 | Sim | The 45-year test takes ~200 s; `Society._mingle` is the likely cost | Low |
| 42 | Boats | No fuel, gear pickup, docking manoeuvre, wake or collision between boats; the crew stands on the hull placeholder-style | Medium |
| 43 | UI | Inspectors, selection, camera easing, save/load keys never operated by a person | High (unverified) |
| 44 | Audio | Ambience is generated noise, never heard; no event sounds | High (unverified) |
| 45 | Wildlife | Only gulls on fixed circuits | Low |
| 46 | Tooling | Git tags cannot be pushed to the remote; baseline is commit `df08c5c` | Low |
| 47 | Reference | Benchmark pages blocked this session; comparison relies on the session-1 written analysis | Medium |

## Session 5 updates (living-world directive)
| # | Area | Issue | Severity |
|---|---|---|---|
| 34 | Sim | **Resolved:** population no longer collapses. Root causes found and fixed: cottage capacity capped families at one child; courting required hours of co-location, so singles almost never paired | — |
| 35 | Sim | **Resolved:** fish glut. Fresh fish now spoils to a scrap heap that gulls scavenge; fishermen with a full larder and a glutted market mend nets | — |
| 36 | Sim | Still open: commercial staff (market, store, eatery, boat yard, carpenter) go unpaid on many work blocks. The businesses have more staff than their trade supports. Unpaid blocks are counted per workplace in the year report | Medium |
| 48 | Sim | One-year run first found starvation (15,852 minutes) from a market liquidity trap: the market paid wages from its till and could not buy the catch. Fixed with consignment, payables before wages, stall rent, council surplus circulation | — (fixed) |
| 49 | Sim | Placeholder population dealt jobs to individuals at random, leaving whole households with no income. Fixed in `tools/gen_population.py` (one job per household first); vacancies now go first to households with no earner | — (fixed) |
| 50 | Sim | Prices first followed only stock on the slab, so fish got cheaper in a poor season. Now stock × 24-hour supply/demand flow. The rise in a poor season is modest because shore fishermen sell into the market and partly replace the boats | Low |
| 51 | Sim | A save/load identity check failed once (5 founders differed) on an older build and has not recurred. The check now names the differing field. Root cause not found | Medium (unexplained) |
| 52 | Sim | Gift-giving needs a hungry household with an empty larder that the giver knows. In normal years gifts are few (tens per year) | Low |
| 53 | Sim | Immigration fills houses empty for 1.5 years; it is a setting (`Society.settings.immigration`). With it off, the 90-year population has not been measured | Low |
| 54 | Sim | Weather has no temperature. Shutters do not close. Laundry does not move in the wind (it is baked into building meshes) | Low |
| 55 | Sim | Residents still pass through each other; boats pass through each other and through rock if a lane crosses it | Medium |
| 56 | Sim | No skill-based job change in mid-life; no rivalry or conflict; no marriage ceremony or celebration events | Medium |
| 57 | Wildlife | Animals are simple placeholder shapes. Fish schools are visible only as dark silhouettes near the surface. No sharks, rays or octopus | Low |
| 58 | Visual | First night captures showed a daylight-bright sea and over-strong moonlight; fixed (moon is a soft key, sea darkens with the scene light) | — (fixed) |
| 59 | Visual | The cinematic camera and the wildlife camera have only been exercised by scripts, never by a person | Medium (unverified) |
| 60 | Tests | Scenario B and the capture's gift scene bend the world on purpose (food spoiled, savings lost); every such step is labelled `scenario_setup_*` in the ledger | — |
| 61 | Tests | The capture's neighbour-help shot timed out (no gift happened in the 10-hour window on that build) | Low |
| 62 | Wildlife | Gull thefts first cascaded (15 in a morning); a stall-vigilance rule now limits them to about 5 a day across the market and boats. The longer suites predate this rule | Low |


## Session 7 — hero villagers v2
- Godot shows dark skin and navy / deep cloth darker and more saturated than the Blender (AgX) renders. Mitigated with `hero_character.gdshader` (albedo power curve 0.66, slight desaturation, rim) and a per-hero fill light; in deep cliff shade faces are still darker than in the renders.
- The game versions are decimated (14.7k–19.3k tris); stripes are re-sliced after decimation, the madras checks are only repainted, so their edges step.
- C's beard hides most of the mouth; B's fitted top shows some body shape; A's boot toes faintly visible; the fish prop is plain.
- Feet follow the clip, not the stair step heights (no foot IK). No root motion: the showcase script moves the captain along the stair.
- glTF import adds the held props as extra skeleton nodes named `<key>_<prop>`; tests exclude them from the 53-bone rig count.
- The four heroes are presentation only; the 42 simulated residents still use the grey placeholder.
