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
var household: Dictionary = {}
var job = null
var bed: Bed = null
var needs := {"hunger": 25.0, "energy": 85.0}
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
	"stairs_climbed": 0, "ladders_climbed": 0, "bridges_crossed": 0, "failed_paths": 0, "failed_uses": 0,
	"plans": 0, "fish_bought": 0, "fish_sold": 0, "metres": 0.0, "max_hunger": 0.0, "starve_minutes": 0.0}
var log: Array = []

func setup(rec: Dictionary, village) -> void:
	villager_id = rec["id"]
	display_name = rec["name"]
	name = "Villager_" + villager_id
	world = village
	graph = village.graph
	home = village.buildings[rec["home"]]
	household = village.households[rec["household"]]
	job = rec.get("job")
	rng.seed = hash(villager_id) & 0x7fffffff
	var beds := home.all_of("bed")
	if rec["bed_slot"] < beds.size():
		bed = beds[rec["bed_slot"]]
		bed.owner_id = villager_id
	needs["hunger"] = 20.0 + rng.randf() * 25.0
	needs["energy"] = 70.0 + rng.randf() * 25.0
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
	at_node = bed.nav_node if bed else home.node_id("hub0")
	global_position = graph.pos[at_node]
	fsm.change("idle", {"seconds": rng.randf() * 2.0})

# ------------------------------------------------------------------ tick
func tick(dt: float, minutes: float) -> void:
	var asleep := fsm.current_name == "sleep"
	needs["hunger"] = minf(100.0, needs["hunger"] + (2.2 if asleep else 6.5) * minutes / 60.0)
	if needs["hunger"] >= 99.9:
		stats["starve_minutes"] += minutes
	if not asleep:
		needs["energy"] = maxf(0.0, needs["energy"] - 5.5 * minutes / 60.0)
	stats["max_hunger"] = maxf(stats["max_hunger"], needs["hunger"])
	fsm.tick(dt, minutes)

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
	elif st.has("idle"):
		fsm.change("idle", {"seconds": st["idle"]})

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
	stats["fish_caught"] += 1
	# working fishers land every second fish at the market; the rest goes home
	if job != null and job["role"] == "fisher" and stats["fish_caught"] % 2 == 0:
		world.market_stock += 1
		stats["fish_sold"] += 1
	else:
		household["raw_fish"] = household.get("raw_fish", 0) + 1
	var st = fsm.current
	if st and st.has_method("on_catch"):
		st.on_catch()

func inside_building() -> String:
	var i := at_node.find(":")
	return at_node.substr(0, i) if i > 0 else ""

func status() -> String:
	return "%s  %s/%s  hunger %d  energy %d" % [display_name, activity, fsm.current_name, int(needs["hunger"]), int(needs["energy"])]

func _note(msg: String) -> void:
	log.append("%s %s" % [GameClock.text(), msg])
	if log.size() > 40:
		log.pop_front()
