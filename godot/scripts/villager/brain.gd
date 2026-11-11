class_name VillagerBrain
extends RefCounted
## Decision layer (VILLAGER_AI.md): scores the candidate activities from the
## villager's needs, the hour, the household pantry and the job, and returns a
## plan - a list of steps the villager executes:
##   {"go": node_id}  |  {"use": Interactable, "state": name, ...args}  |  {"idle": seconds}
## A failed goal goes on cooldown so it is not chosen again immediately.

var v = null
var cooldown: Dictionary = {}          # activity -> game minute it may be retried
var last_scores: Dictionary = {}

func _init(villager) -> void:
	v = villager

func decide() -> Dictionary:
	var h := GameClock.hour()
	var hunger: float = v.needs["hunger"]
	var energy: float = v.needs["energy"]
	var night := h >= 21.0 or h < 5.5
	var meals: int = v.household.get("meals", 0)
	var raw: int = v.household.get("raw_fish", 0)
	var s := {}
	s["sleep"] = (100.0 - energy) * (1.6 if night else 0.55) + (25.0 if night else 0.0)
	if energy > 60.0 and not night:
		s["sleep"] = 0.0
	s["eat"] = hunger * 1.25 if meals > 0 else 0.0
	s["cook"] = (hunger * 1.1 + 12.0) if (meals == 0 and raw > 0) else 0.0
	# with an empty pantry: fish by day, and at night too once really hungry
	s["fish"] = (hunger * 0.95 + 8.0) if (meals == 0 and raw == 0 and (not night or hunger > 70.0)) else 0.0
	if energy > 88.0 or (hunger > 75.0 and energy > 12.0):
		s["sleep"] = 0.0                      # too hungry to sleep: find food first
	# empty pantry and the market has fish: buy rather than queue for a fishing spot
	s["buy_food"] = (hunger * 1.0 + 11.0) if (meals == 0 and raw == 0 and v.world.market_stock > 0 and h >= 6.0 and h < 20.0) else 0.0
	var job = v.job
	var on_shift := false
	if job != null:
		on_shift = h >= job["hours"][0] and h < job["hours"][1]
	if on_shift:
		s["work"] = 46.0
		if job["role"] == "fisher":
			s["fish"] = maxf(s["fish"], 50.0)
			s["work"] = 0.0
	s["stroll"] = 14.0 if not night else 0.0
	s["rest_home"] = 9.0 if not night else 22.0
	for k in s.keys():
		if cooldown.get(k, -1.0) > GameClock.total_minutes:
			s[k] = 0.0
		# small personal wobble so villagers do not move in lockstep
		s[k] += v.rng.randf() * 3.0 if s[k] > 0.0 else 0.0
	last_scores = s
	var order := s.keys()
	order.sort_custom(func(a, b): return s[a] > s[b])
	for act in order:
		if s[act] <= 0.0:
			break
		var plan := _plan(act)
		if not plan.is_empty():
			return {"activity": act, "steps": plan}
		cooldown[act] = GameClock.total_minutes + 20.0
	return {"activity": "wait", "steps": [{"idle": 4.0}]}

func fail(activity: String) -> void:
	cooldown[activity] = GameClock.total_minutes + 30.0

func _use(obj: Interactable, state: String, extra: Dictionary = {}) -> Array:
	if obj == null or obj.nav_node == "" or not obj.reserve(v):
		return []
	var step := {"use": obj, "state": state}
	step.merge(extra)
	return [{"go": obj.nav_node}, step]

func _plan(act: String) -> Array:
	var home = v.home
	match act:
		"sleep":
			return _use(v.bed, "sleep")
		"eat":
			var seat = home.find("chair", v)
			if seat == null:
				seat = home.find("table", v)
			return _use(seat, "eat")
		"cook":
			return _use(home.find("stove", v), "cook")
		"fish":
			var best = null
			var bd := INF
			for fs in v.world.fishing_spots:
				if fs.is_available(v):
					var d: float = fs.use_position.distance_to(v.global_position)
					if d < bd:
						bd = d
						best = fs
			return _use(best, "fish", {"target": 2 if v.job == null or v.job["role"] != "fisher" else 3})
		"buy_food":
			return _use(v.world.market_counter(v), "shop")
		"work":
			var st = v.world.work_station_for(v)
			return _use(st, "work", {"minutes": 60.0 + v.rng.randf() * 60.0})
		"stroll":
			var nodes: Array = v.world.stroll_nodes
			if nodes.is_empty():
				return []
			var n: String = nodes[v.rng.randi() % nodes.size()]
			return [{"go": n}, {"idle": 6.0 + v.rng.randf() * 14.0}]
		"rest_home":
			var seat2 = home.find("chair", v)
			if seat2:
				return _use(seat2, "sit", {"minutes": 20.0 + v.rng.randf() * 30.0})
			return [{"go": home.node_id("hub0")}, {"idle": 8.0}]
	return []
