# ENGINE EVALUATION — v2 (supersedes `docs/ENGINE_EVALUATION_v1_superseded.md`)

**Decision: Godot 4.** GDScript, Compatibility renderer as the baseline. The v1 recommendation (Three.js) is withdrawn: it optimised for ease of capture, and the owner's priority is the quality of the finished simulation.

Neither engine has been run for this project. Everything below is desk evaluation from engine knowledge and should be confirmed by the first Godot spike (see "First proof" at the end).

## Requirement-by-requirement
| Requirement | Godot 4 | Three.js | Verdict |
|---|---|---|---|
| Autonomous villagers | Plain script logic; scene tree gives each villager a node with child systems; headless runs of the same project for tests | Plain script logic; fastest headless tests (Node) | Even. Logic is ours either way |
| Skeletal animation | glTF skins import directly; AnimationPlayer per character; built-in humanoid retargeting map so one clip set drives different rigs | SkinnedMesh + AnimationMixer; retargeting helper is basic | Godot |
| Animation blending | AnimationTree: state machines with cross-fades, 1D/2D blend spaces (walk↔run, turn), one-shots, additive layers, per-bone filters (carry with arms while legs walk) | Manual weight cross-fades only; no state machine, blend spaces or bone masks — all to be written | **Godot, by a wide margin** |
| Interaction animations (hand on rod, cabinet, chair) | Skeleton modifiers for look-at and IK, bone attachments for held items, animation tracks that call methods so a door opens on the exact frame | One CCD IK add-on; attachments by parenting; event timing by hand | **Godot** |
| Multiple-elevation navigation | Navigation meshes baked from level geometry, navigation links for ladders/boarding, agents with avoidance | Recast via WebAssembly or a custom graph; avoidance custom | Godot |
| Functional homes | One scene per building, instanced; markers for anchors, areas for triggers, per-instance state script; visibility layers and material fades for cutaways | Everything assembled in code | Godot |
| Boats | Paths and path-followers for lanes; buoyancy from a shared wave function; boarding via navigation links | Same ideas, all custom | Godot (less glue) |
| Physics | Built in (collision, ray casts, rigid bodies) | Add a third-party physics library | Godot |
| Save/load | JSON or resource files in the user data folder; works on web through browser storage | JSON in browser storage | Even |
| Browser and mobile previews | Web export; single-threaded export is the default path, so ordinary static hosting works. Larger first download; the web build uses the lighter Compatibility renderer. Native Android/iOS export also exists | Lightest and fastest to load | Three.js for convenience; Godot is sufficient |

Seven of ten go to Godot, two are even, one goes to Three.js — and the Three.js win is convenience, not quality. The three that matter most to the brief (blending, interaction animation, navigation) are the ones Three.js would force us to hand-build. No Three.js prototype exists showing otherwise, so the owner's stated default stands.

## Consequences accepted with Godot
- **GDScript, not C#**, because C# projects cannot be exported to the web and the phone preview depends on that.
- **Compatibility renderer as baseline** so the web/phone build and desktop look the same. Its lighting feature set is smaller than Godot's desktop renderers; the art direction (flat-shaded vertex colour, one sun, baked or simple ambient occlusion, lamp glows) is designed to fit inside it. A higher-quality desktop mode can be layered on later.
- **No editor GUI in cloud sessions.** Scenes are text files and will be authored by script and import; fine for me, but it means nobody is dragging things around by eye.
- **Simulation core stays separate** from rendering, as before: plain GDScript classes with no node dependencies, runnable headless for the multi-day tests.
- **The authored walk graph stays.** It is the design intent; the baked navigation mesh must agree with it, and a test will compare the two.

## First proof once Godot can be installed
1. Record version; create project; import `village_massing_v02.glb`; export for web.
2. Capture the web build in headless Chrome (the same capture route already working here) — real in-engine frames.
3. Bake navigation on the massing; walk a capsule from the fish market to the crown cottage; compare with the walk-graph route (currently 119 m door to door for the longest pair).
4. One rigged placeholder walking, climbing a stair, and opening a door with a method-call track.
If step 4 turns out to be unexpectedly hard, that is the moment to revisit this decision — not before.
