# MILESTONES, SCHEDULE, RISKS

Status vocabulary as in `PROOF_OF_WORK.md`. Sessions are working sessions, not calendar promises.

| M | Goal | Gate | Rough size | Status |
|---|---|---|---|---|
| M0 | Research, feasibility, direction | Owner approves engine + art direction | 1–2 sessions | In progress — engine chosen (Godot 4); Blender leg still FAILED |
| M0.5 | Full-village massing layout + route tests | Owner approves layout | 1 session | Delivered for review (session 2) |
| M1 | Premium environment (hero set), day/sunset/night captures | **Owner approves visuals** | 6–10 sessions | Not started |
| M2 | Navigation across all levels, tested | — | 2–3 | Not started |
| M3 | Three functional homes, full household routine | — | 4–6 | Not started |
| M4 | Six autonomous residents, multi-day runs, save/load | 7-day soak passes | 5–8 | Not started |
| M5 | Fishing economy loop | Ledger balanced | 4–6 | Not started |
| M6 | Relationships, family, memories, events | — | 4–6 | Not started |
| M7 | Living environment: water, wildlife, weather, audio | — | 4–6 | Not started |
| M8 | Character style proposals | **Owner approves characters** | 2–3 | Not started |
| M9 | Final characters, animation polish | — | 8–12 | Not started |
| M10 | Expansion | Performance holds | open | Not started |
| M11 | Polish, long soak, final comparison | — | open | Not started |

## Risk register
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Blender cannot be run in cloud sessions even with installs enabled | Medium | High | Try `bpy` wheel first; otherwise the owner would need some machine able to run Blender, or the direct-to-GLB route becomes the pipeline and "Blender" becomes an import target only |
| Scripted modelling cannot reach hand-crafted quality, especially cliffs | High | High | Budget most M1 time for cliffs; review renders at every pass; accept that an AI-authored village may plateau below the reference and say so if it does |
| Object-accurate animation (hands on rods, cabinets, chairs) without a mature animation toolset | High | High | Build IK early with the temporary rig; fall back to Godot if hand-built tooling stalls |
| No phone-side performance data | High | Medium | Publish a test build early and measure on the owner's phone |
| Scope: 24 modules, generations, economy, weather | Certain | High | Strict milestone order; nothing multiplied before one of it works |
| Session memory loss between chats | Certain | Medium | `PROGRESS.md` handoff + repository archive each session |
| Animation/audio licences unverified | Medium | Medium | Read terms first-hand before any import; log in `LICENSES.md` |
