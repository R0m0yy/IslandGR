#!/usr/bin/env python3
"""Copy the data the game reads into the Godot project (res://data).
data/ at the repository root stays the source of truth."""
import os, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dst = os.path.join(ROOT, "godot/data")
os.makedirs(os.path.join(dst, "buildings"), exist_ok=True)
n = 0
for f in ("village_layout.json", "environment.json", "dev_population.json"):
    shutil.copy2(os.path.join(ROOT, "data", f), os.path.join(dst, f)); n += 1
for f in sorted(os.listdir(os.path.join(ROOT, "data/buildings"))):
    shutil.copy2(os.path.join(ROOT, "data/buildings", f), os.path.join(dst, "buildings", f)); n += 1
print("synced", n, "files ->", dst)
