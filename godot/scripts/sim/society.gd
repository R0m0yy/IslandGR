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
var counts := {"births": 0, "deaths": 0, "partnerships": 0, "came_of_age": 0, "retired": 0, "moves": 0, "estates": 0}

const CHILD_NAMES := ["Ari", "Bea", "Cai", "Dee", "Eli", "Fen", "Gil", "Hana", "Isa", "Jem", "Kel", "Lio", "Mae", "Nico", "Oli", "Paz", "Rui", "Sia", "Tai", "Uli"]

func setup(v, seed_: int = 11) -> void:
	village = v
	rng.seed = seed_

static func key(a: String, b: String) -> String:
	return a + "|" + b if a < b else b + "|" + a

func bond(a: String, b: String) -> float:
	return bonds.get(key(a, b), 0.0)

func record(type: String, who: Array, detail: String = "") -> void:
	events.append({"day": GameClock.day(), "type": type, "who": who, "detail": detail})

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
				bonds[k] = minf(100.0, bonds.get(k, 0.0) + (0.6 if g[i].hh == g[j].hh else 0.9))

func _new_day() -> void:
	var years := 1.0 / days_per_year
	for v in village.villagers.duplicate():
		var before := int(v.age)
		v.age += years
		if before < 16 and int(v.age) >= 16:
			counts["came_of_age"] += 1
			record("came_of_age", [v.villager_id])
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
			record("retired", [v.villager_id], String(v.job["role"]))
			counts["retired"] += 1
			village.release_job(v)
		if v.age >= 70.0 and rng.randf() < 0.035 * (v.age - 69.0) * years * 4.0:
			_death(v)
	_partnerships()
	_births(years)
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
			if bond(a.villager_id, b.villager_id) >= 30.0:
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
		if p == null or p.hh != v.hh or v.age < 20.0 or v.age > 44.0 or p.age < 20.0 or p.age > 44.0:
			continue
		var hh: Dictionary = village.households[v.hh]
		if GameClock.day() - int(hh.get("last_birth", -9999)) < int(2.5 * days_per_year):
			continue
		# room for a child: a spare bed, or a place in a parent's bed while the household is under capacity
		var spare := village.free_bed(v.home) != null
		var share: String = ""
		if not spare and hh["members"] < int(hh.get("capacity", 3)):
			for par in [v, p]:
				if par.bed and par.bed.co_sleepers.is_empty():
					share = par.villager_id
					break
		if (not spare and share == "") or village.ledger.money(v.hh) < 25:
			continue
		if rng.randf() < 0.9 * years * 3.0:
			var rec := {"id": "V%d" % next_id, "name": CHILD_NAMES[next_id % CHILD_NAMES.size()], "household": v.hh, "home": v.home.building_id,
				"bed_slot": -1, "job": null, "age": 0.0, "parents": [v.villager_id, p.villager_id], "shares_bed_of": "" if spare else share}
			next_id += 1
			var child = village.add_villager(rec)
			if child:
				v.children.append(child.villager_id)
				p.children.append(child.villager_id)
				hh["last_birth"] = GameClock.day()
				counts["births"] += 1
				record("birth", [child.villager_id], "to %s and %s" % [v.display_name, p.display_name])

func _death(v) -> void:
	counts["deaths"] += 1
	record("death", [v.villager_id], "%s, aged %d" % [v.display_name, int(v.age)])
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

func to_dict() -> Dictionary:
	return {"days_per_year": days_per_year, "bonds": bonds, "events": events, "next_id": next_id, "day": _day, "counts": counts,
		"seed": rng.seed, "rng": rng.state}

func from_dict(d: Dictionary) -> void:
	days_per_year = d["days_per_year"]
	bonds = d["bonds"].duplicate()
	events = d["events"].duplicate(true)
	next_id = int(d["next_id"])
	_day = int(d["day"])
	for k in d["counts"]:
		counts[k] = int(d["counts"][k])
	rng.seed = int(d["seed"]); rng.state = int(d["rng"])
