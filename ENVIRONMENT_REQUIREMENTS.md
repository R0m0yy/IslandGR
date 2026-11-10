# ENVIRONMENT REQUIREMENTS — what is needed to run Blender and Godot

## Re-checked this session (2026-11-09, session 2)
| Check | Result |
|---|---|
| `blender`, `godot` on the machine | Not found |
| `import bpy` | Not installed |
| PyPI reachable | No (connection refused by the session's network policy) |
| GitHub releases reachable | No (HTTP 403 from the session proxy) |
| download.blender.org reachable | No |
| Present and useful | Python 3.11, 3.12 and 3.13; `uv`; Xvfb; Mesa EGL libraries; headless Chrome with WebGL2; ffmpeg |
| Hardware | 2 CPU cores, 8 GB RAM, no GPU |

So nothing changed since session 1: this chat cannot install either tool.

## Option A — cloud sessions with network access (works from a phone)
**What you need to do:** in the settings that control this workspace's network access, allow package installs — at minimum the Python package index (PyPI) and GitHub. If custom domains can be added, add `download.blender.org`. Then **start a new chat**; this one may not pick the change up.

**What I would then do, in order:**
1. Blender: create a Python 3.11 environment and install the `bpy` package (Blender as a Python module), or unpack the official Linux build if blender.org is reachable. Run `blender/import_render_test.py`. Report version, `.blend` path, export warnings, render.
2. Godot: download the Linux editor binary and web export templates from Godot's GitHub releases. Create the project, import the GLB, export for web, capture in headless Chrome.

**Unverified, and I will not know until I try:**
- Whether a `bpy` build exists for the Python versions on these machines.
- Whether Blender's EEVEE renderer works with no GPU. Cycles on 2 CPU cores will work but slowly (minutes per still).
- Whether Godot's web export runs acceptably under software WebGL for captures. Frame rate cannot be measured in the cloud at all; it has to be measured on your phone.

**Limits that remain even if everything installs:** no one can open Blender's or Godot's interface. All modelling is still by script — more capable script (modifiers, bevels, booleans, sculpt-like displacement, proper `.blend` files), but not a person shaping cliffs by hand.

## Option B — Claude Code on a desktop computer
Only relevant if you get access to a Windows, Mac or Linux computer. Requirements: Blender 4.x or newer and Godot 4.x installed, a graphics card of any recent kind, and Claude Code running in the project folder. I would drive both tools from the command line; you could open the `.blend` and the Godot project yourself and see or adjust anything. This is the only route that gives real-time frame rates, GPU rendering, and human eyes inside the tools.

## Recommendation
Option A is the practical route for how you work today. If Option A's Blender step fails, I will say so immediately and not paper over it with more scripted geometry.

## Why there is still scripted geometry in this session
The corrective directive asks for a full-village massing layout now and also asks me to stop growing untested scripted geometry. I resolved that as follows: the **layout data** (`data/village_layout.json`) is the real deliverable and carries forward unchanged into Blender and Godot. The massing GLB is deliberately crude — boxes, slabs, extruded terraces — and exists only to make the layout visible and testable. It is not a step towards final art and none of it is meant to survive.
