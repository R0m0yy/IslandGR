#!/usr/bin/env bash
# Package the complete source project (git-tracked files) into dist/.
#   bash tools/package.sh [label]      -> dist/living-tides-<label>.zip  (+ a lean zip without evidence images)
set -euo pipefail
cd "$(dirname "$0")/.."
label="${1:-$(date +%Y%m%d)}"
mkdir -p dist
full="dist/living-tides-${label}.zip"
lean="dist/living-tides-${label}-lean.zip"
rm -f "$full" "$lean"
git ls-files -z | xargs -0 zip -q -9 "$full"
git ls-files -z | grep -zv -E '^evidence/renders|^assets/glb/' | xargs -0 zip -q -9 "$lean"
ls -la "$full" "$lean"
unzip -l "$full" | tail -1
