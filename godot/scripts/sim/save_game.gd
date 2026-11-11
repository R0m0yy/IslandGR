class_name SaveGame
extends RefCounted
## Versioned save / load. A save holds the whole simulation state as JSON;
## loading applies it to a freshly built village (same layout data).
## Activities in progress are not resumed mid-step: on load every villager
## stands at their last walk node with reservations cleared and decides again;
## a boat that was at sea is back at its mooring with its cargo still aboard.

const VERSION := 3
const MIGRATIONS := {   # from version -> function name
	1: "_migrate_1_to_2",
}

static func snapshot(village) -> Dictionary:
	var vs := []
	for v in village.villagers:
		vs.append(v.to_record())
	var bs := {}
	for id in village.buildings:
		bs[id] = village.buildings[id].state.duplicate()
	var boats := {}
	for id in village.boats:
		var b: Boat = village.boats[id]
		boats[id] = {"condition": b.condition, "trips": b.trips, "landed": b.landed, "aborted": b.aborted}
	var grounds := {}
	for id in village.grounds:
		grounds[id] = village.grounds[id]["stock"]
	return {"schema": "living-tides.save", "version": VERSION, "clock": GameClock.total_minutes,
		"weather": village.weather.to_dict(), "ledger": village.ledger.to_dict(), "economy": village.economy.stats.duplicate(),
		"economy_day": village.economy._day, "society": village.society.to_dict(), "households": village.households.duplicate(true),
		"open_jobs": village.open_jobs.duplicate(true), "journal": village.journal.to_dict(), "ecosystem": village.ecosystem.to_dict(),
		"economy_extra": village.economy.extra_state(), "ocean_time": village.ocean.time, "people": village.people.duplicate(true), "villagers": vs, "buildings": bs, "boats": boats, "grounds": grounds}

static func save(village, path: String) -> bool:
	var f := FileAccess.open(path, FileAccess.WRITE)
	if f == null:
		return false
	f.store_string(JSON.stringify(snapshot(village), " "))
	f.close()
	return true

static func load_file(path: String) -> Dictionary:
	if not FileAccess.file_exists(path):
		return {"error": "missing file"}
	var d = JSON.parse_string(FileAccess.get_file_as_string(path))
	if typeof(d) != TYPE_DICTIONARY or d.get("schema") != "living-tides.save":
		return {"error": "not a Living Tides save"}
	var ver := int(d.get("version", 0))
	if ver > VERSION or ver < 1:
		return {"error": "unsupported save version %d" % ver}
	while ver < VERSION:
		if ver == 1:
			d = _migrate_1_to_2(d)
		elif ver == 2:
			d = _migrate_2_to_3(d)
		ver += 1
		d["version"] = ver
	for k in ["clock", "weather", "ledger", "society", "households", "villagers", "buildings", "boats", "grounds"]:
		if not d.has(k):
			return {"error": "save is missing '%s'" % k}
	return d

static func _migrate_1_to_2(d: Dictionary) -> Dictionary:
	## v1 saves predate thirst / hygiene / social and fishing-ground stocks.
	for r in d.get("villagers", []):
		for k in ["thirst", "hygiene", "social"]:
			if not r["needs"].has(k):
				r["needs"][k] = 50.0
	if not d.has("grounds"):
		d["grounds"] = {}
	if not d.has("open_jobs"):
		d["open_jobs"] = []
	return d

static func _migrate_2_to_3(d: Dictionary) -> Dictionary:
	## v2 saves predate the journal, the ecosystem, debts and the five-state weather.
	if d["weather"].get("state") == "rain":
		d["weather"]["state"] = "light_rain"
	for k in ["journal", "ecosystem", "economy_extra"]:
		if not d.has(k):
			d[k] = {}
	return d

static func apply(village, d: Dictionary) -> bool:
	## Never partially applied: validate first (load_file), then replace state.
	if d.has("error"):
		return false
	for v in village.villagers.duplicate():
		village.remove_villager(v)
	village.open_jobs = []
	GameClock.total_minutes = float(d["clock"])
	village.weather.from_dict(d["weather"])
	village.ledger.from_dict(d["ledger"])
	for k in d["economy"]:
		village.economy.stats[k] = int(d["economy"][k])
	village.economy._day = int(d.get("economy_day", -1))
	village.society.from_dict(d["society"])
	village.journal.from_dict(d.get("journal", {}))
	village.ecosystem.from_dict(d.get("ecosystem", {}))
	village.economy.load_extra(d.get("economy_extra", {}))
	village.ocean.time = float(d.get("ocean_time", 0.0))
	village.people = d.get("people", {}).duplicate(true)
	for hh in d["households"]:
		village.households[hh] = d["households"][hh].duplicate()
		village.households[hh]["members"] = 0
		for k in ["capacity", "last_birth", "vacant_day"]:
			if village.households[hh].has(k):
				village.households[hh][k] = int(village.households[hh][k])
	for id in d["buildings"]:
		if village.buildings.has(id):
			village.buildings[id].state = d["buildings"][id].duplicate()
	for id in d["boats"]:
		if village.boats.has(id):
			var b: Boat = village.boats[id]
			b.condition = float(d["boats"][id]["condition"])
			b.trips = int(d["boats"][id]["trips"]); b.landed = int(d["boats"][id]["landed"]); b.aborted = int(d["boats"][id]["aborted"])
			b.boat_state = "moored"
			b.users.clear(); b.reservations.clear()
			b.place(b.home_pos)
	for id in d["grounds"]:
		if village.grounds.has(id):
			village.grounds[id]["stock"] = float(d["grounds"][id])
	var ordered: Array = d["villagers"].filter(func(r): return r.get("shares_bed_of", "") == "") + d["villagers"].filter(func(r): return r.get("shares_bed_of", "") != "")
	for r in ordered:
		r["bed_slot"] = int(r.get("bed_slot", -1))
		if r.get("job") != null:
			r["job"]["hours"] = [float(r["job"]["hours"][0]), float(r["job"]["hours"][1])]
		village.add_villager(r)
	village.open_jobs = d.get("open_jobs", []).duplicate(true)
	return true
