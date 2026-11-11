#!/usr/bin/env python3
"""Temporary development population + simulation overlay.

The layout leaves household members and job holders empty (character design
is undecided).  This fills them with PLACEHOLDER villagers so the simulation
can be exercised.  It never edits data/village_layout.json; it writes
data/dev_population.json, which Godot reads on top of the layout.
"""
import json, os, random
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
L = json.load(open(os.path.join(ROOT, "data/village_layout.json")))
rng = random.Random(20261110)
GIVEN = ["Ada", "Bram", "Cleo", "Dov", "Edda", "Finn", "Greta", "Hale", "Ines", "Joss", "Kit", "Lark", "Moss", "Nell", "Odo",
         "Pim", "Quill", "Rhea", "Sol", "Tam", "Una", "Vale", "Wren", "Xan", "Yara", "Zed", "Ansel", "Bryn", "Cass", "Dara",
         "Elio", "Faye", "Gus", "Hett", "Ivo", "June", "Kai", "Lise", "Milo", "Nora", "Orin", "Pia", "Rafe", "Suki", "Teo", "Vera"]
rng.shuffle(GIVEN)
villagers, jobs = [], []
for b in L["buildings"]:
    if b["business"]:
        for j in b["business"]["jobs"]:
            jobs.append(dict(role=j["role"], place=b["id"], hours=b["business"]["hours"]))
for bt in L["boats"]:
    jobs.append(dict(role="fisher", place=bt["id"], hours=[6, 15]))
homes = [b for b in L["buildings"] if b["household"]]
beds = {b["id"]: sum(1 for a in b["interior"]["anchors"] if a["type"] == "bed") for b in homes}
n = 0
for b in homes:
    for k in range(min(2, beds[b["id"]], b["household"]["capacity"])):
        villagers.append(dict(id=f"V{n+1:02d}", name=GIVEN[n % len(GIVEN)], household=b["household"]["id"], home=b["id"],
                              bed_slot=k, job=None, placeholder=True))
        n += 1
order = list(range(len(villagers))); rng.shuffle(order)
for vi, job in zip(order, jobs):
    villagers[vi]["job"] = job
out = dict(schema="living-tides.dev_population", version=1,
           note="PLACEHOLDER villagers for simulation development. Final characters are undecided.",
           villagers=villagers,
           fishing_spots=[dict(id="FS_pierA", node="pierA_end", facing=[0, 1], slots=2),
                          dict(id="FS_pierB", node="pierB_end", facing=[0, 1], slots=2),
                          dict(id="FS_spit", node="sp_2", facing=[1, 0.3], slots=2),
                          dict(id="FS_boardwalk", node="bw_3", facing=[0, 1], slots=1)],
           stroll_nodes=["plaza", "k_look", "k_tree", "st_beacon", "hd_mid", "sp_1", "q_n_mkt", "c_hall", "bw_2"],
           start_pantry=dict(raw_fish=1, meals=1))
json.dump(out, open(os.path.join(ROOT, "data/dev_population.json"), "w"), indent=1)
print(len(villagers), "villagers,", sum(1 for v in villagers if v["job"]), "employed of", len(jobs), "job slots")
