# ENGINE EVALUATION

Desk comparison. **No engine was run in session 1**, so nothing here is a measurement. Version facts come from web search on 2026-11-09 and should be re-checked at install time.

## Constraint that shapes the choice
Development happens in cloud sessions and review happens on a phone. There is no desktop workstation. An engine that needs a human at a desktop editor is a poor fit regardless of its rendering quality.

| Criterion | Godot 4 | Unity 6 | Three.js / Babylon.js |
|---|---|---|---|
| Blender integration | Direct glTF and `.blend` import | FBX/glTF import, mature | glTF is the native format |
| Animation | AnimationTree, blend spaces, built-in IK nodes | Best-in-class (Mecanim, rigging package) | Mixer and clips only; state machine, IK and foot placement must be written |
| Navigation | Built-in 3D navmesh with links for ladders | Built-in navmesh + links | Recast compiled to WebAssembly, or a hand-authored walk graph |
| Rendering ceiling | High on desktop; web export uses the lighter Compatibility renderer | Highest | High for this style; all lighting set up by hand |
| Custom shaders | Yes | Yes (Shader Graph) | Yes (GLSL/TSL) |
| Sim performance | GDScript adequate; C# not available on web | C# strong | JS/TS adequate; sim can run in a worker |
| Phone browser | Works; single-threaded web export has been the default since 4.3, so no special hosting headers | Heavier downloads | Lightest; instant load |
| Native mobile | Yes | Yes, strongest | Via wrapper only |
| Headless build and test in the cloud | Yes, command-line export | Possible but needs licence activation and a multi-GB install | Yes — it is just a web page plus Node tests |
| Reviewable on a phone each session | Yes, via web export | Awkward | Yes |
| Maintainability by an AI-led pipeline | Good; scenes are text files | Poor without the editor | Good; everything is code |

## Recommendation
**Three.js for the runtime, with the simulation as a separate engine-independent TypeScript core.**

Why:
1. Every build can be opened on a phone and captured automatically in the cloud, which is how the proof requirements get met each milestone.
2. The art style (flat-shaded vertex colour, one sun, soft shadows, lamp glow) is well inside what WebGL2 delivers. Session 1's hand-written test renderer already produces soft-shadowed diorama lighting from the same asset format.
3. The simulation core runs headless in Node, so seven-day unattended tests are fast and deterministic and never depend on the renderer.

What it costs, plainly:
- Animation tooling must be built: state machine, blending, IK for hand and foot targets, root-motion handling. This is the largest risk in the whole project, and Godot or Unity would hand much of it over for free.
- No scene editor. Placement comes from Blender (empties exported in the GLB) and data files.
- Native app store release would need a wrapper.

**Fallback: Godot 4.** If the animation requirements (section 8 of the brief) prove too costly to hand-build, move the presentation layer to Godot and keep the simulation core by porting or bridging it. Keeping simulation and rendering separate from day one is what makes that switch affordable.

**Not recommended: Unity 6.** Strongest toolset, but it cannot realistically be operated without a desktop editor.

Decision needed from the owner before any engine code is written.
