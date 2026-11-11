class_name Villager
extends Node3D
## An autonomous villager. Composition:
##   needs      plain numbers that drift with game time
##   brain      chooses an activity and expands it into steps (brain.gd)
##   fsm        reusable state machine; one state per locomotion mode / activity
##   animator   TEMPORARY placeholder figure + the animation-name contract
## Movement is kinematic along the typed walk graph: the link type decides the
## locomotion state (walk, climb stairs, climb ladder, open door...).

const Activities = preload("res://scripts/villager/states/activities.gd")
const LOCO := {"stair": "climb_stairs", "ladder": "climb_ladder", "bridge": "cross_bridge", "doorway": "open_door"}

var villager_id: String = ""
var display_name: String = ""
var world = null                    # Village
var graph: NavGraph = null
var home: Building = null
var hh: String = ""                 # household id = Ledger account
var job = null
var bed: Bed = null
var age: float = 30.0
var partner: String = ""
var parents: Array = []
var children: Array = []
var at_sea: bool = false
var shares_bed_of: String = ""
var diligence: float = 1.0          # personal traits: small, persistent differences
var sociability: float = 1.0
var wake_offset: float = 0.0
var generosity: float = 0.5
var boldness: float = 0.5
var ambition: String = "provide"    # provide | family | wealth | sea : a long-term leaning that tilts daily choices
var skills := {"fishing": 0.2, "cooking": 0.2, "trade": 0.2, "carpentry": 0.2}
var memories: Array = []            # {"day", "type", "text", "valence"} - significant events only, capped
var sick_days: int = 0
var _react_t: float = 0.0
var _shelter_t: float = 0.0
var health: float = 100.0
var needs := {"hunger": 25.0, "energy": 85.0, "thirst": 20.0, "hygiene": 80.0, "social": 60.0}
var rng := RandomNumberGenerator.new()
var brain: VillagerBrain
var fsm: StateMachine
var animator: VillagerAnimator

var at_node: String = ""
var path: Array = []
var seg_a: String = ""
var seg_b: String = ""
var seg_done: float = 0.0
var seg_len: float = 0.0
var plan: Array = []
var activity: String = ""
var stuck_time: float = 0.0
var stats := {"sleeps": 0, "meals_cooked": 0, "meals_eaten": 0, "fish_caught": 0, "work_blocks": 0, "doors_opened": 0,
	"stairs_climbed": 0, "ladders_climbed": 0, "bridges_crossed": 0, "failed_paths": 0, "failed_uses": 0, "boat_trips": 0, "thefts_suffered": 0, "nets_mended": 0, "gifts_given": 0, "gifts_received": 0, "sheltered": 0, "stayed_ashore": 0, "empty_trips": 0, "repairs_done": 0, "wages": 0, "income": 0, "drinks": 0, "washes": 0,
	"plans": 0, "fish_bought": 0, "fish_sold": 0, "metres": 0.0, "max_hunger": 0.0, "starve_minutes": 0.0}
var log: Array = []

func setup(rec: Dictionary, village) -> void:
	villager_id = rec["id"]
	display_name = rec["name"]
	name = "Villager_" + villager_id
	world = village
	graph = village.graph
	home = village.buildings[rec["home"]]
	hh = rec["household"]
	job = rec.get("job")
	rng.seed = hash(villager_id) & 0x7fffffff
	age = rec["age"] if rec.has("age") else 20.0 + float(rng.randi() % 36)
	partner = rec.get("partner", "")
	parents = rec.get("parents", []).duplicate()
	children = rec.get("children", []).duplicate()
	diligence = 0.8 + rng.randf() * 0.4
	sociability = 0.6 + rng.randf() * 0.8
	wake_offset = rng.randf_range(-0.6, 0.9)
	generosity = rng.randf()
	boldness = rng.randf()
	ambition = ["provide", "family", "wealth", "sea"][rng.randi() % 4]
	for k in skills:
		skills[k] = rng.randf_range(0.1, 0.35)
	if job != null:
		var main: String = {"fisher": "fishing", "cook": "cooking", "carpenter": "carpentry", "apprentice": "carpentry", "boatwright": "carpentry"}.get(job["role"], "trade")
		skills[main] = rng.randf_range(0.35, 0.7)
	for k in rec.get("skills", {}):
		skills[k] = float(rec["skills"][k])
	memories = rec.get("memories", []).duplicate(true)
	sick_days = int(rec.get("sick_days", 0))
	if rec.has("ambition"):
		ambition = rec["ambition"]
	var beds := home.all_of("bed")
	if rec.get("shares_bed_of", "") != "":
		bed = null
	elif int(rec.get("bed_slot", -1)) >= 0 and int(rec["bed_slot"]) < beds.size():
		bed = beds[int(rec["bed_slot"])]
	else:
		bed = village.free_bed(home)
	if bed == null and rec.get("shares_bed_of", "") != "":
		# a young child sleeps in a parent's bed until one of their own is free
		var par = village.villager_by_id(rec["shares_bed_of"])
		if par and par.bed and par.home == home:
			bed = par.bed
			shares_bed_of = rec["shares_bed_of"]
			bed.co_sleepers.append(villager_id)
	elif bed:
		bed.owner_id = villager_id
	needs["hunger"] = 20.0 + rng.randf() * 25.0
	needs["energy"] = 70.0 + rng.randf() * 25.0
	needs["thirst"] = 10.0 + rng.randf() * 25.0
	animator = VillagerAnimator.new()
	animator.name = "Animator"
	add_child(animator)
	animator.build(Color.from_hsv(rng.randf(), 0.55, 0.85))
	brain = VillagerBrain.new(self)
	fsm = StateMachine.new()
	fsm.add("idle", IdleState.new(self))
	fsm.add("walk", LocomotionState.new(self, "walk", 1.5))
	fsm.add("climb_stairs", LocomotionState.new(self, "climb_stairs", 0.85))
	fsm.add("climb_ladder", LocomotionState.new(self, "climb_ladder", 0.5))
	fsm.add("cross_bridge", LocomotionState.new(self, "walk", 1.0))
	fsm.add("open_door", OpenDoorState.new(self))
	fsm.add("sleep", Activities.SleepState.new(self))
	fsm.add("cook", Activities.CookState.new(self))
	fsm.add("eat", Activities.EatState.new(self))
	fsm.add("fish", Activities.FishState.new(self))
	fsm.add("work", Activities.WorkState.new(self))
	fsm.add("sit", Activities.SitState.new(self))
	fsm.add("shop", Activities.ShopState.new(self))
	fsm.add("fish_trip", Activities.FishTripState.new(self))
	fsm.add("drink", Activities.DrinkState.new(self))
	fsm.add("wash", Activities.WashState.new(self))
	fsm.add("mend_nets", Activities.MendNetsState.new(self))
	at_node = rec.get("at_node", bed.nav_node if bed else home.node_id("hub0"))
	if not graph.pos.has(at_node):
		at_node = home.node_id("hub0")
	for k in rec.get("needs", {}):
		needs[k] = float(rec["needs"][k])
	health = float(rec.get("health", 100.0))
	for k in rec.get("stats", {}):
		stats[k] = rec["stats"][k]
	global_position = graph.pos[at_node]
	fsm.change("idle", {"seconds": rng.randf() * 2.0})

# ------------------------------------------------------------------ tick
func tick(dt: float, minutes: float) -> void:
	var asleep := fsm.current_name == "sleep"
	var hrs := minutes / 60.0
	needs["hunger"] = minf(100.0, needs["hunger"] + (2.2 if asleep else 6.5) * hrs)
	needs["thirst"] = minf(100.0, needs["thirst"] + (2.5 if asleep else 8.0) * hrs)
	if needs["hunger"] >= 99.9:
		stats["starve_minutes"] += minutes
	if not asleep:
		needs["energy"] = maxf(0.0, needs["energy"] - 5.5 * hrs)
		needs["hygiene"] = maxf(0.0, needs["hygiene"] - 3.0 * hrs)
		needs["social"] = maxf(0.0, needs["social"] - 2.5 * hrs)
	var deprived: bool = needs["hunger"] >= 99.9 or needs["thirst"] >= 99.9
	health = clampf(health + (-5.0 if deprived else 1.0) * hrs, 0.0, 100.0)
	stats["max_hunger"] = maxf(stats["max_hunger"], needs["hunger"])
	if _react_t > 0.0:
		_react_t -= dt
		if _react_t <= 0.0 and fsm.current:
			play(fsm.current.anim)
	_shelter_t -= dt
	if _shelter_t <= 0.0:
		_shelter_t = 4.0
		if world.weather.shelter_needed() and not at_sea and inside_building() == "" and activity in ["stroll", "fish", "give_food"]:
			seek_shelter()
	fsm.tick(dt, minutes)

func remember(type: String, text: String, valence: float = 0.0) -> void:
	memories.append({"day": GameClock.day(), "type": type, "text": text, "valence": valence})
	if memories.size() > 30:
		memories.pop_front()

func react(clip: String, seconds: float) -> void:
	## A brief visible reaction (shooing a gull, waving) that does not change the plan.
	_react_t = seconds
	if animator:
		animator.play({"shoo": "work"}.get(clip, clip))

func seek_shelter() -> void:
	## Heavy rain: drop what you were doing outdoors and get home.
	stats["sheltered"] += 1
	_note("caught in %s: heading home" % world.weather.state)
	remember("weather", "ran home through the %s" % world.weather.state.replace("_", " "), -1.0)
	for st in plan:
		if st.has("use"):
			st["use"].release(self)
	if fsm.current is UseObjectState:
		fsm.change("idle", {"seconds": 0.1})
	activity = "shelter"
	plan = [{"go": home.node_id("hub0")}, {"idle": 30.0}]
	path = []
	_run_step()

func play(clip: String) -> void:
	if animator:
		animator.play(clip)

# ------------------------------------------------------------------ plan
func step_done() -> void:
	if plan.is_empty():
		_new_plan()
	_run_step()

func _new_plan() -> void:
	var d := brain.decide()
	activity = d["activity"]
	plan = d["steps"]
	stats["plans"] += 1
	_note("plan %s" % activity)

func fail_plan(why: String) -> void:
	_note("FAILED %s: %s" % [activity, why])
	for st in plan:
		if st.has("use"):
			st["use"].release(self)
	brain.fail(activity)
	plan = []
	path = []
	fsm.change("idle", {"seconds": 2.0})

func _run_step() -> void:
	if plan.is_empty():
		fsm.change("idle", {"seconds": 1.0})
		return
	var st: Dictionary = plan.pop_front()
	if st.has("go"):
		var p := graph.find_path(at_node, st["go"])
		if p.is_empty():
			stats["failed_paths"] += 1
			fail_plan("no path %s -> %s" % [at_node, st["go"]])
			return
		p.pop_front()
		path = p
		next_segment()
	elif st.has("use"):
		fsm.change(st["state"], st.merged({"obj": st["use"]}))
	elif st.has("gift"):
		world.economy.give(self, st["gift"], st["item"], st["n"])
		fsm.change("idle", {"seconds": 6.0})
	elif st.has("cut_bait"):
		if world.economy.cut_bait(self):
			_note("cut bait from a fish")
		fsm.change("idle", {"seconds": 12.0, "anim": "work"})
	elif st.has("repair"):
		world.economy.repair_building(self, st["repair"])
		fsm.change("idle", {"seconds": 40.0, "anim": "work"})
	elif st.has("idle"):
		fsm.change("idle", {"seconds": st["idle"], "anim": st.get("anim", "idle")})

# ------------------------------------------------------------------ travel
func next_segment() -> void:
	if path.is_empty():
		seg_b = ""
		step_done()
		return
	seg_a = at_node
	seg_b = path.pop_front()
	var e := graph.edge(seg_a, seg_b)
	seg_len = maxf(e.get("len", 0.01), 0.01)
	seg_done = 0.0
	var mode: String = LOCO.get(e.get("type", "walk"), "walk")
	match mode:
		"climb_stairs": stats["stairs_climbed"] += 1
		"climb_ladder": stats["ladders_climbed"] += 1
		"cross_bridge": stats["bridges_crossed"] += 1
	if mode == "open_door":
		fsm.change("open_door", {"door": e.get("ref")})
	elif fsm.current_name != mode:
		fsm.change(mode)

func advance_segment(metres: float) -> bool:
	## Moves along the current link; true when its end is reached.
	if seg_b == "":
		return true
	seg_done += metres
	stats["metres"] += metres
	var a: Vector3 = graph.pos[seg_a]
	var b: Vector3 = graph.pos[seg_b]
	var k := clampf(seg_done / seg_len, 0.0, 1.0)
	global_position = a.lerp(b, k)
	var d := b - a
	d.y = 0.0
	if d.length_squared() > 1e-6:
		face(d)
	if k >= 1.0:
		at_node = seg_b
		return true
	return false

func face(dir: Vector3) -> void:
	dir.y = 0.0
	if dir.length_squared() < 1e-8:
		return
	var yaw := atan2(-dir.x, -dir.z)              # -Z is forward
	rotation = Vector3(0.0, yaw, 0.0)

func snap_to(pos: Vector3, dir: Vector3, _pose: String) -> void:
	global_position = pos
	face(dir)

func unsnap() -> void:
	if graph.pos.has(at_node):
		global_position = graph.pos[at_node]

func on_catch(_spot) -> void:
	## hand-line catch from a pier or the shore: straight into the household pantry
	world.ledger.mint(hh, "fish", 1, "handline_catch")
	stats["fish_caught"] += 1
	world.economy.sell_handline(self)
	var st = fsm.current
	if st and st.has_method("on_catch"):
		st.on_catch()

func mood() -> float:
	## Derived, never stored (VILLAGER_AI.md).
	var m: float = 100.0 - 0.35 * needs["hunger"] - 0.2 * needs["thirst"] - 0.2 * (100.0 - needs["energy"]) \
		- 0.15 * (100.0 - needs["hygiene"]) - 0.2 * (100.0 - needs["social"])
	return clampf(m + 25.0, 0.0, 100.0)

func note(msg: String) -> void:
	_note(msg)

func info() -> Dictionary:
	## Everything the resident inspector shows.
	var friends := []
	for o in world.villagers:
		if o != self:
			var b: float = world.society.bond(villager_id, o.villager_id)
			if b >= 20.0:
				friends.append([b, o.display_name])
	friends.sort_custom(func(x, y): return x[0] > y[0])
	return {"id": villager_id, "name": display_name, "age": int(age), "household": hh, "home": home.building_id,
		"job": (job["role"] + " @ " + String(job["place"])) if job != null else ("child" if age < 16.0 else ("retired" if age >= 65.0 else "none")),
		"activity": activity, "state": fsm.current_name, "going_to": path[-1] if not path.is_empty() else "",
		"needs": needs.duplicate(), "mood": int(mood()), "health": int(health), "sick": sick_days > 0,
		"skills": skills.duplicate(), "ambition": ambition, "traits": {"diligence": diligence, "sociability": sociability, "generosity": generosity, "boldness": boldness},
		"memories": memories.slice(-5), "parents": parents, "kids": children,
		"household_money": world.ledger.money(hh), "pantry": world.ledger.acc[hh]["items"].duplicate(),
		"partner": partner, "children": children.size(), "friends": friends.slice(0, 4), "recent": log.slice(-5)}

func inside_building() -> String:
	var i := at_node.find(":")
	return at_node.substr(0, i) if i > 0 else ""

func status() -> String:
	return "%s  %s/%s  hunger %d  energy %d" % [display_name, activity, fsm.current_name, int(needs["hunger"]), int(needs["energy"])]

func _note(msg: String) -> void:
	log.append("%s %s" % [GameClock.text(), msg])
	if log.size() > 40:
		log.pop_front()

func to_record() -> Dictionary:
	## Persistent state (save game). The current activity is not stored: after a
	## load the villager stands at `at_node` and decides again.
	var slot := -1
	if bed and shares_bed_of == "":
		slot = home.all_of("bed").find(bed)
	return {"id": villager_id, "name": display_name, "household": hh, "home": home.building_id, "bed_slot": slot, "job": job,
		"shares_bed_of": shares_bed_of, "age": age, "partner": partner, "parents": parents, "children": children, "needs": needs.duplicate(), "health": health, "skills": skills.duplicate(), "memories": memories.duplicate(true),
		"sick_days": sick_days, "ambition": ambition, "at_node": at_node,
		"stats": stats.duplicate(), "activity": activity, "state": fsm.current_name}

func shutdown() -> void:
	## Leave the world cleanly: finish the current state, drop every reservation.
	if fsm.current:
		fsm.current.exit()
		fsm.current = null
	for st in plan:
		if st.has("use"):
			st["use"].release(self)
	plan = []
	if bed:
		bed.release(self)
		if shares_bed_of != "":
			bed.co_sleepers.erase(villager_id)
		else:
			bed.owner_id = ""
			bed.co_sleepers.clear()
