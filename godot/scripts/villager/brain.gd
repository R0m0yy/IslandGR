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
var _gift_to: String = ""

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
	if meals > 0 and hunger > 25.0:
		for o in w.villagers:
			if o != v and o.hh == v.hh and o.fsm.current_name == "eat":
				s["eat"] += 18.0                 # sit down with the family
				break
	s["drink"] = thirst * 1.15 if thirst > 40.0 else 0.0
	s["wash"] = (100.0 - v.needs["hygiene"]) * 0.6 if v.needs["hygiene"] < 40.0 and not night else 0.0
	# a parent feeds the household, not only themselves: food decisions use the hungriest member's need
	var need := hunger
	for o in w.villagers:
		if o.hh == v.hh:
			need = maxf(need, o.needs["hunger"])
	if adult:
		s["cook"] = (need * 1.1 + 12.0) if (meals == 0 and raw > 0 and need > 30.0) else 0.0
		var shop_open := h >= 6.0 and h < 20.0
		s["buy_food"] = (need * 1.0 + 11.0) if (meals == 0 and raw == 0 and shop_open and w.weather.state != "storm" and l.qty(Economy.MARKET, "fish") > 0 and purse >= w.economy.fish_sell_price()) else 0.0
		s["eat_out"] = (hunger * 1.05 + 4.0) if (meals == 0 and hunger > 45.0 and h >= 7.0 and h < 21.0 and l.qty(Economy.EATERY, "meal") > 0 and purse >= Economy.MEAL_PRICE + 6) else 0.0
		s["fish"] = (need * 0.95 + 8.0) * (1.0 if out_f > 0.0 else 0.0) if (meals == 0 and raw == 0 and (not night or need > 70.0)) else 0.0
		var job = v.job
		var rest_day: bool = GameClock.day() % 7 == 6
		if job != null and not rest_day and v.age < 65.0 and v.sick_days <= 0:
			var on_shift: bool = h >= job["hours"][0] + v.wake_offset and h < job["hours"][1]
			if on_shift:
				if job["role"] == "fisher":
					var b = w.boats.get(job["place"])
					if b and b.boat_state == "moored" and not w.weather.unsafe_at_sea() and b.is_available(v) and energy > 30.0:
						# read the sky: the cautious and the inexperienced judge the same weather differently
						var risk: float = w.weather.forecast(v.skills["fishing"], v.rng)
						if risk > 0.22 + 0.4 * v.boldness:
							if cooldown.get("boat_trip", -1.0) <= GameClock.total_minutes:
								v.stats["stayed_ashore"] += 1
								v.note("sky looks bad (risk %d%%): staying ashore" % int(risk * 100.0))
								w.journal.add("fishing", [v.villager_id], "%s read the sky and kept the boat in." % v.display_name, "storm risk judged %d%% (true %d%%)" % [int(risk * 100.0), int(w.weather.storm_risk() * 100.0)])
							cooldown["boat_trip"] = GameClock.total_minutes + 90.0
						elif l.qty(v.hh, "bait") < 1:
							if purse >= Economy.BAIT_PRICE and l.qty(Economy.STORE, "bait") > 0:
								s["buy_bait"] = 56.0
							elif raw > 0:
								s["cut_bait"] = 52.0                          # shop is out: cut bait from a fish at home
							else:
								s["fish"] = maxf(s.get("fish", 0.0), 40.0 * out_f)   # nothing to bait with: hand-line from the pier
						elif w.economy.fish_buy_price() <= 2 and raw >= Economy.HOME_KEEP and v.ambition != "wealth":
							s["mend_nets"] = 50.0                             # market glutted, larder full: not worth the trip today
						else:
							s["boat_trip"] = 58.0 + (6.0 if v.ambition == "sea" else 0.0)
				elif job["role"] in ["carpenter", "apprentice"] and w.damaged_building() != "" and not w.weather.shelter_needed():
					s["repair"] = 54.0
				else:
					s["work"] = 46.0 * v.diligence * (1.15 if v.ambition in ["provide", "wealth"] else 1.0)
				if false:
					pass
	if adult and v.sick_days <= 0:
		# kindness: someone I know has an empty larder and I have food to spare
		var spare: int = raw - 2 * maxi(1, w.households[v.hh]["members"])
		if spare >= 2 and cooldown.get("give_food", -1.0) <= GameClock.total_minutes:
			var need_hh: String = w.household_in_need(v)
			if need_hh != "":
				_gift_to = need_hh
				s["give_food"] = 24.0 + 40.0 * v.generosity + 6.0 * float(w.economy.favours.get(need_hh + "|" + v.hh, 0))
	if v.sick_days > 0:
		s["rest_home"] = 60.0
	s["stroll"] = (14.0 + (100.0 - v.needs["social"]) * 0.2 * v.sociability) * out_f if not night else 0.0
	s["rest_home"] = maxf(s.get("rest_home", 0.0), (9.0 if not night else 22.0) + (16.0 if out_f < 0.5 else 0.0) + (8.0 if v.ambition == "family" else 0.0))
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
		"cut_bait":
			return [{"go": home.node_id("hub0")}, {"cut_bait": true}]
		"mend_nets":
			var nl = w.buildings.get("P04")
			var frame = nl.find("net_frame", v) if nl else null
			if frame == null:
				frame = home.find("net_rack", v)
			return _use(frame, "mend_nets", {"minutes": 60.0 + v.rng.randf() * 40.0})
		"buy_bait":
			var st2 = w.buildings.get("P05")
			return _use(st2.find("counter", v) if st2 else null, "shop", {"what": "bait"})
		"give_food":
			if _gift_to == "" or not w.households.has(_gift_to):
				return []
			cooldown["give_food"] = GameClock.total_minutes + 240.0
			return [{"go": "door_" + w.households[_gift_to]["building"]}, {"gift": _gift_to, "item": "fish", "n": 2 + (1 if v.generosity > 0.7 else 0)}]
		"repair":
			var bid: String = w.damaged_building()
			if bid == "":
				return []
			return [{"go": "door_" + bid}, {"repair": bid}]
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
