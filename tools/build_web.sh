#!/usr/bin/env bash
# Build the browser version: Godot Web export (single-thread, Compatibility renderer), then the
# base64 text parts + loader page used by the hosted artifact (web_site/).
# Set GODOT=/path/to/godot if it is not on PATH. Needs Godot 4.3 and its web_nothreads_release template in ~/.local/share/godot/export_templates/4.3.stable/.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p web web_site
"${GODOT:-godot}" --headless --path godot --export-release Web ../web/index.html
cp web/index.js web/index.audio.worklet.js web_site/
gzip -9 -c web/index.wasm > web_site/index.wasm.gz
cp web/index.pck web_site/index.pck
python3 - <<'PY'
import base64, os
parts = {}; text = 0
for src, pre in (("web_site/index.pck", "pck"), ("web_site/index.wasm.gz", "wasm")):
    d = open(src, "rb").read(); n = 0
    for i in range(0, len(d), 6_000_000):
        t = base64.b64encode(d[i:i+6_000_000]).decode(); text += len(t)
        open(f"web_site/{pre}.{n}.txt", "w").write(t); n += 1
    parts[pre] = n
    print(pre, n, "parts")
# the loader page is generated from the template so its part counts and sizes can never go stale
s = open("tools/web_loader.html").read()
for k, v in (("PCK_PARTS", parts["pck"]), ("WASM_PARTS", parts["wasm"]), ("TOTAL_TEXT_BYTES", text),
             ("PCK_BYTES", os.path.getsize("web/index.pck")), ("WASM_BYTES", os.path.getsize("web/index.wasm")),
             ("DOWNLOAD_MB", round(text * 0.75 / 1048576))):
    s = s.replace(k, str(v))
open("web_site/index.html", "w").write(s)
os.remove("web_site/index.pck"); os.remove("web_site/index.wasm.gz")
PY
echo "Now publish web_site/index.html with index.js, index.audio.worklet.js, pck.*.txt, wasm.*.txt as supporting files."
