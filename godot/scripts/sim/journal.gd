class_name Journal
extends RefCounted
## The living-world journal: every meaningful happening is recorded here by the
## system that caused it, with who was involved and why. Nothing is written
## for show - an entry exists only because simulation state changed.

signal added(entry: Dictionary)

var entries: Array = []
var counts: Dictionary = {}
var notable_queue: Array = []        # for the observer's "focus on notable events"

func add(type: String, actors: Array, text: String, cause: String = "", notable: bool = false, where = null) -> Dictionary:
	var e := {"n": entries.size(), "minute": snappedf(GameClock.total_minutes, 0.1), "day": GameClock.day(), "type": type,
		"actors": actors, "text": text, "cause": cause, "notable": notable}
	if where != null:
		e["where"] = [where.x, where.y, where.z]
	entries.append(e)
	counts[type] = int(counts.get(type, 0)) + 1
	if notable:
		notable_queue.append(e)
		if notable_queue.size() > 20:
			notable_queue.pop_front()
	added.emit(e)
	return e

func of_actor(id: String, limit: int = 12) -> Array:
	var out := []
	for i in range(entries.size() - 1, -1, -1):
		if entries[i]["actors"].has(id):
			out.append(entries[i])
			if out.size() >= limit:
				break
	return out

func of_type(type: String) -> Array:
	return entries.filter(func(e): return e["type"] == type)

func recent(limit: int = 12, notable_only: bool = false) -> Array:
	var out := []
	for i in range(entries.size() - 1, -1, -1):
		if not notable_only or entries[i]["notable"]:
			out.append(entries[i])
			if out.size() >= limit:
				break
	return out

static func stamp(e: Dictionary) -> String:
	var m: float = e["minute"]
	return "Day %d %02d:%02d" % [int(m / 1440.0) + 1, int(fmod(m / 60.0, 24.0)), int(fmod(m, 60.0))]

func to_dict() -> Dictionary:
	return {"entries": entries, "counts": counts}

func from_dict(d: Dictionary) -> void:
	entries = d.get("entries", []).duplicate(true)
	counts = {}
	for k in d.get("counts", {}):
		counts[k] = int(d["counts"][k])
