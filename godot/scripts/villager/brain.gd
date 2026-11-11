class_name VillagerBrain
extends RefCounted
## Decision layer (VILLAGER_AI.md): scores candidate activities from needs,
## the hour, the weather, the household's pantry and purse, the job and the
## life stage, then expands the winner into steps:
##   {"go": node_id}  |  {"use": Interactable, "state": name, ...args}  |  {"idle": seconds}
## A failed goal goes on cooldown so it is not chosen again immediately.

var v = null
var cooldown: Dictionary = {}          # activity -> game minute it may be retried
var last_scores: Dictionary = {}

func _init(villager) -> void:
	v = villager

func decide() -> Dictionary:
	var h := GameClock.hour()
	var w = v.world
	var l: Ledger = w.ledger
	var hunger: float = v.needs["hunger"]
	var energy: float = v.needs["energy"]
	var thirst: float = v.needs["thirst"]
	var night := h >= 21.0 or h < 5.5
	var meals := l.qty(v.hh, "meal")
	var raw := l.qty(v.hh, "fish")
	var purse := l.money(v.hh)
	var out_f: float = w.weather.outdoor_factor()
	var adult: bool = v.age >= 16.0
	var s := {}
	s["sleep"] = (100.0 - energy) * (1.6 if night else 0.55) + (25.0 if night else 0.0)
	if (energy > 60.0 and not night) or energy > 88.0 or ((hunger > 75.0 or thirst > 85.0) and energy > 12.0):
		s["sleep"] = 0.0
	s["eat"] = hunger * 1.25 if meals > 0 else 0.0
	s["drink"] = thirst * 1.15 if thirst > 40.0 else 0.0
	s["wash"] = (100.0 - v.needs["hygiene"]) * 0.6 if v.needs["hygiene"] < 40.0 and not night else 0.0
	if adult:
		# cook for the household, not only for yourself
		var need := hunger
		for o in w.villagers:
			if o.hh == v.hh:
				need = maxf(need, o.needs["hunger"])
		s["cook"] = (need * 1.1 + 12.0) if (meals == 0 and raw > 0 and need > 30.0) else 0.0
		var shop_open := h >= 6.0 and h < 20.0
		s["buy_food"] = (hunger * 1.0 + 11.0) if (meals == 0 and raw == 0 and shop_open and l.qty(Economy.MARKET, "fish") > 0 and purse >= w.economy.fish_sell_price()) else 0.0
		s["eat_out"] = (hunger * 1.05 + 4.0) if (meals == 0 and hunger > 45.0 and h >= 7.0 and h < 21.0 and l.qty(Economy.EATERY, "meal") > 0 and purse >= Economy.MEAL_PRICE + 6) else 0.0
		s["fish"] = (hunger * 0.95 + 8.0) * (1.0 if out_f > 0.0 else 0.0) if (meals == 0 and raw == 0 and (not night or hunger > 70.0)) else 0.0
		var job = v.job
		var rest_day: bool = GameClock.day() % 7 == 6
		if job != null and not rest_day and v.age < 65.0:
			var on_shift: bool = h >= job["hours"][0] + v.wake_offset and h < job["hours"][1]
			if on_shift:
				if job["role"] == "fisher":
					var b = w.boats.get(job["place"])
					if b and b.boat_state == "moored" and not w.weather.unsafe_at_sea() and b.is_available(v) and energy > 30.0:
						s["boat_trip"] = 58.0
				else:
					s["work"] = 46.0 * v.diligence
	s["stroll"] = (14.0 + (100.0 - v.needs["social"]) * 0.2 * v.sociability) * out_f if not night else 0.0
	s["rest_home"] = (9.0 if not night else 22.0) + (16.0 if out_f < 0.5 else 0.0)
	for k in s.keys():
		if cooldown.get(k, -1.0) > GameClock.total_minutes:
			s[k] = 0.0
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
	var w = v.world
	match act:
		"sleep":
			return _use(v.bed, "sleep")
		"eat":
			var seat = home.find("chair", v)
			if seat == null:
				seat = home.find("table", v)
			return _use(seat, "eat")
		"eat_out":
			var e = w.buildings.get("P06")
			if e == null:
				return []
			var st = e.find("chair", v)
			if st == null:
				st = e.find("table", v)
			return _use(st, "eat", {"out": true})
		"drink":
			var sink = home.find("sink", v)
			if sink == null:
				sink = w.well
			return _use(sink, "drink")
		"wash":
			return _use(home.find("washstand", v), "wash")
		"cook":
			return _use(home.find("stove", v), "cook")
		"buy_food":
			return _use(w.market_counter(v), "shop")
		"fish":
			var best = null
			var bd := INF
			for fs in w.fishing_spots:
				if fs.is_available(v):
					var d: float = fs.use_position.distance_to(v.global_position)
					if d < bd:
						bd = d
						best = fs
			return _use(best, "fish", {"target": 2})
		"boat_trip":
			return _use(w.boats.get(v.job["place"]), "fish_trip")
		"work":
			return _use(w.work_station_for(v), "work", {"minutes": 60.0 + v.rng.randf() * 60.0})
		"stroll":
			var nodes: Array = w.stroll_nodes
			if nodes.is_empty():
				return []
			var n: String = nodes[v.rng.randi() % nodes.size()]
			if v.age < 16.0:
				n = "door_" + home.building_id          # children play near home
			return [{"go": n}, {"idle": 6.0 + v.rng.randf() * 14.0}]
		"rest_home":
			var seat2 = home.find("chair", v)
			if seat2:
				return _use(seat2, "sit", {"minutes": 20.0 + v.rng.randf() * 30.0})
			return [{"go": home.node_id("hub0")}, {"idle": 8.0}]
	return []
