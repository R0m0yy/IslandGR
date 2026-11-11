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
