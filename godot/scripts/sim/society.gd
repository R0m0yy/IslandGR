class_name Society
extends RefCounted
## Relationships, households over time, aging, births, deaths, inheritance.
## Everything here leaves a persistent trace: scores on pairs, links between
## people, beds and jobs that change hands, money that moves, and an event
## history. Pace is set by `days_per_year` (how many game days one year of a
## life takes) - a gameplay setting, not a constant.

var village = null
var days_per_year: float = 28.0
var rng := RandomNumberGenerator.new()
var bonds: Dictionary = {}            # "idA|idB" (sorted) -> friendship 0..100
var events: Array = []                # {"day", "type", "who", "detail"}
var next_id: int = 1000
var _day: int = -1
var _acc: float = 0.0
var _greeted: Dictionary = {}
var counts := {"births": 0, "deaths": 0, "partnerships": 0, "came_of_age": 0, "retired": 0, "moves": 0, "estates": 0, "illnesses": 0, "newcomers": 0, "greetings": 0}

const CHILD_NAMES := ["Ari", "Bea", "Cai", "Dee", "Eli", "Fen", "Gil", "Hana", "Isa", "Jem", "Kel", "Lio", "Mae", "Nico", "Oli", "Paz", "Rui", "Sia", "Tai", "Uli"]

func setup(v, seed_: int = 11) -> void:
	village = v
	rng.seed = seed_

static func key(a: String, b: String) -> String:
	return a + "|" + b if a < b else b + "|" + a

func bond(a: String, b: String) -> float:
	return bonds.get(key(a, b), 0.0)

var settings := {"fertile_min": 18.0, "fertile_max": 45.0, "births_per_fertile_year": 0.55, "birth_gap_years": 2.0, "pair_bond": 28.0,
	"immigration": true, "vacancy_years": 1.5, "old_age": 70.0, "illness_per_day": 0.006}
var birth_blocked := {"age": 0, "no_room": 0, "money": 0, "gap": 0, "apart": 0}     # why couples did not have a child (couple-days)

const TEXT := {"birth": "A child, %s, was born %s.", "death": "%s died (%s).", "partnership": "%s and %s became a couple.",
	"came_of_age": "%s came of age.", "retired": "%s retired (%s).", "moved": "%s moved %s.", "hired": "%s started work as %s.",
	"estate": "An estate was settled: %s.", "newcomers": "Newcomers settled: %s.", "illness": "%s fell ill.", "recovery": "%s is well again."}

func record(type: String, who: Array, detail: String = "", cause: String = "") -> void:
	events.append({"day": GameClock.day(), "type": type, "who": who, "detail": detail})
	var names := who.map(func(id): var x = village.villager_by_id(id); return x.display_name if x else id)
	var txt: String = detail
	match type:
		"birth": txt = TEXT[type] % [names[0], detail]
		"partnership": txt = TEXT[type] % [names[0], names[1]]
		"came_of_age", "illness", "recovery": txt = TEXT[type] % names[0]
		"retired", "moved", "hired": txt = TEXT[type] % [names[0], detail]
		"death": txt = "%s." % detail if detail != "" else names[0]
		"estate", "newcomers": txt = TEXT[type] % detail
	village.journal.add(type, who, txt, cause, type in ["birth", "death", "partnership", "newcomers", "estate"])
	for id in who:
		var x = village.villager_by_id(id)
		if x:
			x.remember(type, txt, 6.0 if type in ["birth", "partnership", "hired"] else (-6.0 if type in ["death", "illness"] else 1.0))

func tick(minutes: float) -> void:
	_acc += minutes
	if _acc >= 10.0:
		_acc -= 10.0
		_mingle()
	var d := GameClock.day()
	if d != _day:
		_day = d
		_new_day()

func _mingle() -> void:
	## People who are awake and close together get to know each other.
	var groups := {}
	for v in village.villagers:
		if v.fsm.current_name == "sleep" or v.at_sea:
			continue
		var cell := Vector3i(int(floor(v.global_position.x / 4.0)), int(floor(v.global_position.y / 3.0)), int(floor(v.global_position.z / 4.0)))
		if not groups.has(cell):
			groups[cell] = []
		groups[cell].append(v)
	for cell in groups:
		var g: Array = groups[cell]
		if g.size() < 2:
			continue
		for i in g.size():
			g[i].needs["social"] = minf(100.0, g[i].needs["social"] + 2.5)
			for j in range(i + 1, g.size()):
				var k: String = key(g[i].villager_id, g[j].villager_id)
				if bonds.get(k, 0.0) >= 30.0 and _greeted.get(k, -1) != GameClock.day():
					_greeted[k] = GameClock.day()               # friends who meet wave to each other, once a day
					g[i].react("wave", 2.0)
					g[j].react("wave", 2.0)
					counts["greetings"] += 1
				var courting: bool = g[i].partner == "" and g[j].partner == "" and g[i].age >= 17.0 and g[j].age >= 17.0 and g[i].hh != g[j].hh
				bonds[k] = minf(100.0, bonds.get(k, 0.0) + (0.6 if g[i].hh == g[j].hh else (2.2 if courting else 0.9)))

func _new_day() -> void:
	var years := 1.0 / days_per_year
	for v in village.villagers.duplicate():
		var before := int(v.age)
		v.age += years
		if before < 16 and int(v.age) >= 16:
			counts["came_of_age"] += 1
			record("came_of_age", [v.villager_id], "", "sixteenth birthday")
		if v.age >= 16.0 and v.age < 65.0 and v.job == null:
			village.assign_free_job(v)
		if v.age >= 12.0 and v.shares_bed_of != "":
			# too big to share: take a spare bed at home, else an empty house in the village
			var nb = village.free_bed(v.home)
			if nb:
				v.bed.co_sleepers.erase(v.villager_id)
				v.shares_bed_of = ""
				v.bed = nb
				nb.owner_id = v.villager_id
		if v.age >= 18.0 and (v.shares_bed_of != "" or village.households[v.hh]["members"] > 2 and v.partner == "" and not v.parents.is_empty()):
			for hh2 in village.households:
				if village.households[hh2]["members"] == 0 and village.move_household(v, hh2):
					# a young adult sets up home with a share of the family purse
					var share_m: int = village.ledger.money(village.households.keys()[0]) * 0
					var old_hh: String = ""
					for par_id in v.parents:
						var par = village.villager_by_id(par_id)
						if par:
							old_hh = par.hh
					if old_hh != "" and old_hh != hh2:
						share_m = village.ledger.money(old_hh) / 4
						if share_m > 0:
							village.ledger.pay(old_hh, hh2, share_m, "setting_up_home")
					counts["moves"] += 1
					break
		if before < 65 and int(v.age) >= 65 and v.job != null:
			record("retired", [v.villager_id], String(v.job["role"]), "reached 65")
			counts["retired"] += 1
			village.economy.succession(v)
			village.release_job(v)
		if v.sick_days > 0:
			v.sick_days -= 1
			v.health = minf(100.0, v.health + 12.0)
			if v.sick_days == 0:
				record("recovery", [v.villager_id])
		elif rng.randf() < settings["illness_per_day"] * (2.5 if v.age >= 65.0 else 1.0) * (1.6 if v.needs["hygiene"] < 25.0 else 1.0):
			# illness is a day-scale event: its rate is per game day, independent of how fast lives age
			v.sick_days = rng.randi_range(2, 5)
			v.health = minf(v.health, 45.0)
			counts["illnesses"] += 1
			record("illness", [v.villager_id], "", "chance%s" % (", poor hygiene" if v.needs["hygiene"] < 25.0 else ""))
		if v.age >= settings["old_age"] and rng.randf() < 0.035 * (v.age - settings["old_age"] + 1.0) * years * 4.0:
			_death(v)
	_partnerships()
	_births(years)
	if settings["immigration"]:
		_newcomers()
	for k in bonds.keys():                  # acquaintances fade without contact
		bonds[k] = bonds[k] - 0.15
		if bonds[k] <= 0.0:
			bonds.erase(k)

func _partnerships() -> void:
	var singles: Array = village.villagers.filter(func(v): return v.partner == "" and v.age >= 18.0 and v.age < 60.0)
	for i in singles.size():
		var a = singles[i]
		if a.partner != "":
			continue
		for j in range(i + 1, singles.size()):
			var b = singles[j]
			if b.partner != "" or a.parents.has(b.villager_id) or b.parents.has(a.villager_id) or _siblings(a, b):
				continue
			if bond(a.villager_id, b.villager_id) >= settings["pair_bond"]:
				a.partner = b.villager_id
				b.partner = a.villager_id
				counts["partnerships"] += 1
				record("partnership", [a.villager_id, b.villager_id])
				if a.hh != b.hh:
					# live together where there is a bed; otherwise each stays put for now
					if village.move_household(b, a.hh) or village.move_household(a, b.hh):
						counts["moves"] += 1
				break

func _siblings(a, b) -> bool:
	for p in a.parents:
		if b.parents.has(p):
			return true
	return false

func _births(years: float) -> void:
	for v in village.villagers.duplicate():
		if v.partner == "" or v.villager_id > v.partner:
			continue
		var p = village.villager_by_id(v.partner)
		if p == null:
			continue
		if p.hh != v.hh:
			birth_blocked["apart"] += 1
			continue
		if v.age < settings["fertile_min"] or v.age > settings["fertile_max"] or p.age < settings["fertile_min"] or p.age > settings["fertile_max"]:
			birth_blocked["age"] += 1
			continue
		var hh: Dictionary = village.households[v.hh]
		if GameClock.day() - int(hh.get("last_birth", -9999)) < int(settings["birth_gap_years"] * days_per_year):
			birth_blocked["gap"] += 1
			continue
		# room for a child: a spare bed, or a place in a parent's bed while the household is under capacity
		var spare := village.free_bed(v.home) != null
		var share: String = ""
		if not spare and hh["members"] < int(hh.get("capacity", 3)):
			for par in [v, p]:
				if par.bed and par.bed.co_sleepers.size() < 2:
					share = par.villager_id
					break
		if not spare and share == "":
			birth_blocked["no_room"] += 1
			continue
		if village.ledger.money(v.hh) < 20:
			birth_blocked["money"] += 1
			continue
		if rng.randf() < settings["births_per_fertile_year"] * years:
			var rec := {"id": "V%d" % next_id, "name": CHILD_NAMES[next_id % CHILD_NAMES.size()], "household": v.hh, "home": v.home.building_id,
				"bed_slot": -1, "job": null, "age": 0.0, "parents": [v.villager_id, p.villager_id], "shares_bed_of": "" if spare else share}
			next_id += 1
			var child = village.add_villager(rec)
			if child:
				v.children.append(child.villager_id)
				p.children.append(child.villager_id)
				hh["last_birth"] = GameClock.day()
				counts["births"] += 1
				record("birth", [child.villager_id, v.villager_id, p.villager_id], "to %s and %s" % [v.display_name, p.display_name], "couple aged %d and %d with room at home" % [int(v.age), int(p.age)])

func _death(v) -> void:
	counts["deaths"] += 1
	record("death", [v.villager_id] + v.children, "%s died, aged %d" % [v.display_name, int(v.age)], "old age")
	village.economy.succession(v)
	var hh_id: String = v.hh
	if v.partner != "":
		var p = village.villager_by_id(v.partner)
		if p:
			p.partner = ""
	village.remove_villager(v)
	if village.households[hh_id]["members"] <= 0:
		# nobody left at home: the estate passes to the children's households, else to the council
		var heirs := []
		for c in v.children:
			var cv = village.villager_by_id(c)
			if cv and cv.hh != hh_id and not heirs.has(cv.hh):
				heirs.append(cv.hh)
		var l: Ledger = village.ledger
		var m: int = l.money(hh_id)
		var to: String = heirs[0] if not heirs.is_empty() else Economy.COUNCIL
		if m > 0:
			l.pay(hh_id, to, m, "inheritance")
		for it in l.acc[hh_id]["items"].keys():
			var q: int = l.qty(hh_id, it)
			if q > 0:
				l.move(hh_id, to if l.acc.has(to) else Economy.COUNCIL, it, q, "inheritance")
		counts["estates"] += 1
		record("estate", [v.villager_id], "household %s closed, estate to %s" % [hh_id, to])

func _newcomers() -> void:
	## An empty house does not stay empty for ever: after a while a young couple
	## from along the coast takes it, bringing their savings. Configurable.
	for hh in village.households:
		var h: Dictionary = village.households[hh]
		if h["members"] > 0:
			h.erase("vacant_day")
			continue
		if not h.has("vacant_day"):
			h["vacant_day"] = GameClock.day()
		if GameClock.day() - int(h["vacant_day"]) < int(settings["vacancy_years"] * days_per_year) or rng.randf() > 0.25:
			continue
		var made := []
		for k in 2:
			var rec := {"id": "V%d" % next_id, "name": CHILD_NAMES[(next_id * 7 + 3) % CHILD_NAMES.size()] + ("a" if k == 0 else "o"), "household": hh, "home": h["building"],
				"bed_slot": -1, "job": null, "age": float(rng.randi_range(20, 29))}
			next_id += 1
			var nv = village.add_villager(rec)
			if nv:
				made.append(nv)
		if made.size() == 2:
			made[0].partner = made[1].villager_id
			made[1].partner = made[0].villager_id
			bonds[key(made[0].villager_id, made[1].villager_id)] = 70.0
			village.ledger.open(hh, 40)                           # their savings arrive with them (recorded as issued money)
			for nv in made:
				village.assign_free_job(nv)
			counts["newcomers"] += 2
			h.erase("vacant_day")
			record("newcomers", [made[0].villager_id, made[1].villager_id], "%s and %s took the empty house %s" % [made[0].display_name, made[1].display_name, h["building"]], "house empty for %d days" % int(settings["vacancy_years"] * days_per_year))

func to_dict() -> Dictionary:
	return {"settings": settings, "birth_blocked": birth_blocked, "days_per_year": days_per_year, "bonds": bonds, "events": events, "next_id": next_id, "day": _day, "counts": counts,
		"seed": rng.seed, "rng": rng.state}

func from_dict(d: Dictionary) -> void:
	days_per_year = d["days_per_year"]
	for k in d.get("settings", {}):
		settings[k] = d["settings"][k]
	for k in d.get("birth_blocked", {}):
		birth_blocked[k] = int(d["birth_blocked"][k])
	bonds = d["bonds"].duplicate()
	events = d["events"].duplicate(true)
	next_id = int(d["next_id"])
	_day = int(d["day"])
	for k in d["counts"]:
		if counts.has(k):
			counts[k] = int(d["counts"][k])
	rng.seed = int(d["seed"]); rng.state = int(d["rng"])
