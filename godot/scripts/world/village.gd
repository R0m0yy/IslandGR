class_name Village
extends Node3D
## Assembles the playable world from data: environment GLBs, the 30 building
## prefabs, the combined walk graph (village + every interior), outdoor
## interactables, lamps, the sea, and the placeholder villagers.

const OCEAN_SHADER := preload("res://shaders/ocean.gdshader")

@export var spawn_villagers: bool = true
@export var with_presentation: bool = true      # sky, sun, camera, HUD (off in logic tests)

var graph := NavGraph.new()
var buildings: Dictionary = {}       # id -> Building
var households: Dictionary = {}      # id -> {raw_fish, meals, ...}
var villagers: Array = []
var interactables: Array = []
var doors: Array = []
var fishing_spots: Array = []
var stroll_nodes: Array = []
var street_lamps: Array = []
var market_stock: int = 4          # raw fish on the market stalls (P01)
var sim: Simulation
var day_night = null
var camera_rig = null
var hud = null
var _lamps_on := false

func _ready() -> void:
	build()

func build() -> void:
	_build_environment()
	_build_graph()
	_build_buildings()
	_build_outdoor()
	sim = Simulation.new()
	sim.name = "Simulation"
	sim.village = self
	add_child(sim)
	if spawn_villagers:
		_spawn_villagers()
	if with_presentation:
		_build_presentation()

# ------------------------------------------------------------------ world
func _build_environment() -> void:
	var env := Node3D.new()
	env.name = "Environment"
	add_child(env)
	for n in ["terrain", "cliffs", "gate", "structures", "props", "vegetation", "boats"]:
		var path := "res://assets/env/%s.glb" % n
		if ResourceLoader.exists(path):
			var inst: Node3D = load(path).instantiate()
			inst.name = n
			env.add_child(inst)
	var sea := MeshInstance3D.new()
	sea.name = "Sea"
	var pm := PlaneMesh.new()
	pm.size = Vector2(420, 420)
	pm.subdivide_width = 160
	pm.subdivide_depth = 160
	sea.mesh = pm
	var sm := ShaderMaterial.new()
	sm.shader = OCEAN_SHADER
	sea.material_override = sm
	sea.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	env.add_child(sea)

func _build_graph() -> void:
	var nav: Dictionary = VillageDB.layout["nav"]
	for id in nav["nodes"]:
		var n: Dictionary = nav["nodes"][id]
		graph.add_node(id, Vector3(n["x"], n["y"], n["z"]), {"kind": n["kind"]})
	for e in nav["edges"]:
		graph.add_edge(e["a"], e["b"], e["type"])

func _build_buildings() -> void:
	var root := Node3D.new()
	root.name = "Buildings"
	add_child(root)
	for b in VillageDB.layout["buildings"]:
		var id: String = b["id"]
		if not VillageDB.sidecars.has(id):
			continue
		var bld := Building.new()
		root.add_child(bld)
		bld.setup(id)
		bld.register_nav(graph)
		buildings[id] = bld
		interactables.append_array(bld.interactables)
		if bld.door:
			doors.append(bld.door)
		if b.get("household") != null:
			var start: Dictionary = VillageDB.population.get("start_pantry", {})
			households[b["household"]["id"]] = {"building": id, "raw_fish": int(start.get("raw_fish", 0)), "meals": int(start.get("meals", 0))}

func _build_outdoor() -> void:
	var root := Node3D.new()
	root.name = "Outdoor"
	add_child(root)
	for f in VillageDB.population.get("fishing_spots", []):
		var fs := FishingSpot.new()
		fs.name = f["id"]
		fs.object_id = f["id"]
		fs.capacity = int(f["slots"])
		fs.nav_node = f["node"]
		fs.rng.seed = hash(f["id"])
		root.add_child(fs)
		fs.facing = Vector3(f["facing"][0], 0, f["facing"][1]).normalized()
		fs.use_position = graph.pos[f["node"]] + fs.facing * 0.55
		fs.global_position = fs.use_position
		fishing_spots.append(fs)
		interactables.append(fs)
	stroll_nodes = VillageDB.population.get("stroll_nodes", []).filter(func(n): return graph.pos.has(n))
	for l in VillageDB.environment.get("lamps", []):
		street_lamps.append(_lamp(root, l["id"], VillageDB.v3(l["pos"]), 9.0, 2.2))
	for lm in VillageDB.environment.get("landmarks", []):
		if lm.has("light"):
			street_lamps.append(_lamp(root, "LIGHT_" + lm["id"], VillageDB.v3(lm["light"]), 26.0, 5.0))

func _lamp(parent: Node, id: String, p: Vector3, rng_m: float, energy: float) -> OmniLight3D:
	var l := OmniLight3D.new()
	l.name = id
	l.light_color = Color(1.0, 0.8, 0.5)
	l.light_energy = energy
	l.omni_range = rng_m
	l.shadow_enabled = false
	l.visible = false
	parent.add_child(l)
	l.global_position = p
	return l

func set_street_lamps(on: bool) -> void:
	if on == _lamps_on:
		return
	_lamps_on = on
	for l in street_lamps:
		l.visible = on

func _spawn_villagers() -> void:
	var root := Node3D.new()
	root.name = "Villagers"
	add_child(root)
	for rec in VillageDB.population.get("villagers", []):
		if not buildings.has(rec["home"]):
			continue
		var v := Villager.new()
		root.add_child(v)
		v.setup(rec, self)
		villagers.append(v)

func work_station_for(v) -> Interactable:
	## The object a villager works at: something in their employer's building.
	if v.job == null or not buildings.has(v.job["place"]):
		return null
	var b: Building = buildings[v.job["place"]]
	var skip := ["door", "bed", "chair", "lamp", "storage", "cabinet", "washstand", "sink", "bench", "net_rack"]
	for o in b.interactables:
		if not skip.has(o.kind) and o.nav_node != "" and o.is_available(v):
			return o
	return null

func market_counter(v) -> Interactable:
	if not buildings.has("P01"):
		return null
	for k in ["counter", "scales", "ice_box"]:
		var o = buildings["P01"].find(k, v)
		if o and o.nav_node != "":
			return o
	return null

# ------------------------------------------------------------------ presentation
func _build_presentation() -> void:
	day_night = load("res://scripts/world/day_night.gd").new()
	day_night.name = "DayNight"
	add_child(day_night)
	camera_rig = load("res://scripts/camera/orbit_camera.gd").new()
	camera_rig.name = "CameraRig"
	add_child(camera_rig)
	camera_rig.village = self
	hud = load("res://scripts/ui/hud.gd").new()
	hud.name = "HUD"
	add_child(hud)
	hud.village = self

func toggle_cutaway(id: String = "") -> void:
	if id != "" and buildings.has(id):
		buildings[id].set_cutaway(not buildings[id].cutaway)
		return
	var any := false
	for k in buildings:
		any = any or buildings[k].cutaway
	for k in buildings:
		buildings[k].set_cutaway(not any)
