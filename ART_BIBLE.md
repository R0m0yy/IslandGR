# ART BIBLE — v0.1 (awaiting approval)

## 1. One-line target
A hand-built miniature you could pick up: warm rock, painted timber, tin roofs, calm paper-cut sea, lit like a studio model by day and from within by night.

## 2. What we keep from the reference, and what is ours
| Keep (general language) | Change (original design) |
|---|---|
| Diorama on a slab, high three-quarter camera | Different land form: a crescent island around a lagoon, no enclosing arch |
| Stacked, overlapping shacks; roofs breaking the skyline | Six building families instead of one box type |
| Warm unifying rock + restrained multi-hue paint | Own palette, own colour-zoning rule (§4) |
| Props carrying the story | Every prop tied to a simulated use |
| Faceted flat-shaded sea | Animated facets, depth tint, soft shore foam |
| Ladders as accent | Stairs and ramps as the real network; ladders only as shortcuts |

## 3. Form rules
- Scale: 1 unit = 1 m. Door 0.9 × 1.9 m. Storey 2.4 m. Adult villager 1.7 m. Plank 0.2–0.34 m wide.
- Nothing perfectly square: 0.5–2° lean on boards, roofs 2–6° off axis from neighbours.
- Every building breaks its box at least twice (porch, lean-to, balcony, dormer, external stair, chimney).
- Bevel nothing; let flat facets and overlaps make the edges. Triangle size on rock: 0.4–1.5 m.
- Silhouette test: the village must read as a black shape at thumbnail size before colour is applied.
- Density gradient: props thickest at doors, docks and the plaza; rock faces left clean so the eye can rest.

## 4. Palette (sRGB)
| Role | Colour | Hex |
|---|---|---|
| Rock light / mid / shadow | terracotta sand | `#DDB57A` / `#C98B4C` / `#955B33` |
| Sea light / mid / deep | | `#79BEEC` / `#4C97D6` / `#3A78C2` |
| Weathered red, coral | | `#B5463C`, `#D8725F` |
| Ochre, cream | | `#D7A546`, `#EBDCB4` |
| Turquoise, ocean blue, deep blue | | `#3FA79E`, `#3F7DC0`, `#2D5894` |
| Plum accent | | `#7B4F86` |
| Foliage dark / mid / light | | `#6E9C58` / `#4FA05A` / `#7DBB55` |
| Timber dark / mid / light | | `#553828` / `#8B5D3F` / `#A9774F` |
| Stone, whitewash, rope | | `#9C9CAB`, `#F1EEE6`, `#C9B48A` |

These are a starting set chosen by eye, not sampled from the reference. The Dribbble palette has not been read.

**Zoning rule.** Terrain and sea stay under 55% saturation. Homes use one wall hue and one contrasting roof hue. Public buildings own the strongest colours: market = coral + cream awning, school = ochre, hall = turquoise, clinic = whitewash with red trim. Paths are pale so routes read from the overview.

## 5. Materials
Vertex colour, roughness 0.85–0.95, no metal except tin roofs (roughness 0.6, slight sheen) and glass. Weathering by colour variation per board and by darker vertex tint near ground and under eaves. No image textures unless a specific asset proves it needs one.

## 6. Lighting
| Time | Key | Fill | Ambient | Practicals |
|---|---|---|---|---|
| Morning | warm white, low from the east, long soft shadows | cool sky | bright | off |
| Midday | neutral-warm, high | soft opposite fill | brightest | off |
| Sunset | deep orange, very low | violet | rose-violet | windows begin to glow |
| Night | dim blue moon | almost none | dark indigo | windows, lanterns, shop fronts carry the image |
| Storm | grey, diffuse, low contrast | — | desaturated | lamps on; lightning flashes |

Contact shadows and ambient occlusion are mandatory. Bloom only on lamp cores, kept subtle. Fixed tone curve and exposure per time of day.

## 7. Building families
Cottage (1 room) · Family house (2–3 rooms, porch) · Stacked house (shop below, home above) · Stilt house (over water) · Long shed (workshop, warehouse) · Civic (hall, school, clinic — taller, symmetrical front, sign).

## 8. Structured comparison: session-1 test scene vs the reference
The test scene (`evidence/renders/`) is a single cottage on a rock, built to prove file output and rendering. It is rated here because the directive requires it, not because it is offered as art.

| Category | Rating | Evidence |
|---|---|---|
| Overall composition | Below | One object in the centre of the tile; no path for the eye |
| Village silhouette | Below | There is no village |
| House architecture | Approaching | Individual planks, corner posts, footings, framed door with brace, shuttered windows (render 04). One house, one type |
| Roof geometry | Approaching | Corrugated sheets in overlapping rows, patch, weights, rafters (render 04) |
| Colour harmony | Below | Ochre/red/blue/plum works on the house; water too bright, rock too yellow |
| Cliff modelling | Below | Ring-lofted lump; no caves, undercut or planes |
| Rock formations | Below | Three scattered blobs |
| Harbor design | Below | One short jetty, one boat |
| Ocean appearance | Below | Faceted like the reference but over-exposed; shoreline band is flat |
| Architectural layering | Below | Single level plus one deck |
| Walkways and stairs | Below | One ladder, and it clips through the rock |
| Vegetation | Approaching | Two palms with arched fronds, faceted tree and shrubs |
| Environmental details | Below | ~15 prop types versus hundreds of placements |
| Lighting | Approaching | Key + fill + occlusion give soft diorama light (renders 01, 04) |
| Shadows | Approaching | Soft, grounded; some banding noise |
| Materials | Below | Vertex colour only; no tin sheen, no weathering gradient |
| Atmosphere | Below | No haze, no depth cue |
| Visual depth | Below | Nothing overlaps anything |
| Camera framing | Approaching | Same family of view; subject too small in frame |

Nothing is rated comparable or better. The useful conclusions: the plank/roof/prop construction method holds up in close-up; the cliff method does not and must be replaced with hand-shaped geometry in Blender.
