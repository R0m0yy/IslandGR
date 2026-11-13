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
var figures_visible: bool = true
var low_quality: bool = false         # phones / browsers: fewer pixels, no shadow pass, lighter sea
var show_heroes: bool = true          # the four hero villagers on the Harbour Stair (presentation only)
var hero_showcase = null
var village_life = null
var street_lamps: Array = []
var ledger := Ledger.new()
var economy := Economy.new()
var weather := Weather.new()
var society := Society.new()
var journal := Journal.new()
var ecosystem := Ecosystem.new()
var ocean := Ocean.new()
var boats: Dictionary = {}           # id -> Boat
var grounds: Dictionary = {}         # fishing ground id -> {pos, stock, cap, richness}
var open_jobs: Array = []
var people: Dictionary = {}         # everyone who ever lived here: id -> {name, parents, partner, children, born, died, household, job}            # vacated job records
var well: Interactable = null
var villager_root: Node3D = null
var sim: Simulation
var day_night = null
var camera_rig = null
var atmosphere = null
var hud = null
var _lamps_on := false

func _ready() -> void:
	build()

func build() -> void:
	low_quality = OS.has_feature("web") or OS.has_feature("mobile")
	_build_environment()
	_build_graph()
	_build_buildings()
	_build_outdoor()
	economy.setup(self, ledger)
	_build_boats()
	society.setup(self)
	ecosystem.setup(self)
	weather.changed.connect(_on_weather_changed)
	sim = Simulation.new()
	sim.name = "Simulation"
	sim.village = self
	add_child(sim)
	if spawn_villagers:
		_spawn_villagers()
	economy.assign_owners()
	for v in villagers:
		if v.job != null and v.job["role"] == "fisher":
			ledger.mint(v.hh, "bait", 2, "start_stock")
	if with_presentation:
		_build_presentation()

# ------------------------------------------------------------------ helpers shared by the systems
func household_name(hh: String) -> String:
	var b: String = households[hh]["building"] if households.has(hh) else hh
	return "the household at %s" % (buildings[b].record["name"] if buildings.has(b) else b)

func business_name(biz: String) -> String:
	var id := biz.substr(4)
	return String(buildings[id].record["name"]) if buildings.has(id) else biz

func damaged_building() -> String:
	for id in buildings:
		if buildings[id].state.get("condition", 1.0) < 0.9:
			return id
	return ""

func household_in_need(v) -> String:
	## A household this villager knows (a friend, or a next-door neighbour)
	## whose larder is empty while someone there is hungry or ill.
	var best := ""
	var bs := 0.0
	for hh in households:
		if hh == v.hh or households[hh]["members"] <= 0 or economy.food_of(hh) > 0:
			continue
		var hungry := 0.0
		var known := 0.0
		var frail := false
		for o in villagers:
			if o.hh == hh:
				hungry = maxf(hungry, o.needs["hunger"])
				known = maxf(known, society.bond(v.villager_id, o.villager_id))
				frail = frail or o.sick_days > 0 or o.age >= 68.0
		var near: bool = buildings[households[hh]["building"]].global_position.distance_to(v.home.global_position) < 9.0
		if hungry < 50.0 or (known < 8.0 and not near):
			continue
		var score: float = hungry + known + (25.0 if frail else 0.0) + (10.0 if near else 0.0)
		if score > bs:
			bs = score
			best = hh
	return best

func _on_weather_changed(st: String) -> void:
	if st == "storm":
		journal.add("weather", [], "A storm broke over Saltcrown.", "weather turned from heavy rain", true)
		# real damage: some roofs lose sheets; they stay damaged until a carpenter mends them
		for id in buildings:
			if society.rng.randf() < 0.10:
				buildings[id].state["condition"] = 0.6
				journal.add("damage", [], "The storm tore sheets from the roof of %s." % buildings[id].record["name"], "storm", false, buildings[id].global_position)
	elif st == "heavy_rain":
		journal.add("weather", [], "Heavy rain set in.", "weather")
	elif st in ["cloudy", "clear"] and _last_weather in ["light_rain", "heavy_rain", "storm"]:
		journal.add("weather", [], "The weather cleared.", "weather")
	_last_weather = st

var _last_weather: String = "clear"

# ------------------------------------------------------------------ world
func _build_environment() -> void:
	var env := Node3D.new()
	env.name = "Environment"
	add_child(env)
	for n in ["island", "seabed", "structures", "props", "vegetation", "boats"]:
		var path := "res://assets/env/%s.glb" % n
		if ResourceLoader.exists(path):
			var inst: Node3D = load(path).instantiate()
			inst.name = n
			env.add_child(inst)
			if n in ["island", "structures"]:
				# real collision geometry for the rock, stairs, piers and decks (ray picks, feet on the steps)
				for mi in inst.find_children("*", "MeshInstance3D", true, false):
					mi.create_trimesh_collision()
	var sea := MeshInstance3D.new()
	sea.name = "Sea"
	var pm := PlaneMesh.new()
	pm.size = Vector2(420, 420)
	pm.subdivide_width = 64 if low_quality else 160
	pm.subdivide_depth = 64 if low_quality else 160
	sea.mesh = pm
	var sm := ShaderMaterial.new()
	sm.shader = OCEAN_SHADER
	var hm: Dictionary = VillageDB.environment.get("seabed_height", {})
	if not hm.is_empty() and ResourceLoader.exists("res://assets/env/" + hm["file"]):
		sm.set_shader_parameter("height_tex", load("res://assets/env/" + hm["file"]))
		sm.set_shader_parameter("height_rect", Vector4(hm["x"][0], hm["z"][0], hm["x"][1], hm["z"][1]))
		sm.set_shader_parameter("height_range", Vector2(hm["h"][0], hm["h"][1]))
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
			households[b["household"]["id"]] = {"building": id, "members": 0, "capacity": int(b["household"]["capacity"])}

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
	# the plaza well: free drinking water for anyone
	well = Interactable.new()
	well.name = "Well"
	well.object_id = "well"
	well.kind = "well"
	well.capacity = 3
	well.nav_node = "plaza"
	root.add_child(well)
	well.use_position = graph.pos["plaza"]
	interactables.append(well)
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

func _build_boats() -> void:
	## Boats become Interactables with a Ledger account for cargo and a sea route.
	var root := Node3D.new()
	root.name = "Boats"
	add_child(root)
	var L: Dictionary = VillageDB.layout
	var i := 0
	for g in L["fishing_grounds"]:
		grounds[g["id"]] = {"pos": Vector3(g["pos"][0], 0, g["pos"][1]), "stock": 90.0, "cap": 140.0,
			"richness": [1.0, 1.25, 1.1][i % 3], "name": g["name"]}
		i += 1
	var lanes := {"FG_A": [Vector3(14.5, 0, 17), Vector3(20, 0, 20), Vector3(22, 0, 22)]}
	lanes["FG_B"] = lanes["FG_A"] + [Vector3(28, 0, 9), Vector3(35, 0, 8.5), Vector3(44, 0, 9)]     # through The Gate
	lanes["FG_C"] = lanes["FG_A"] + [Vector3(18, 0, 30), Vector3(10, 0, 34)]
	var board := {}
	for e in L["nav"]["edges"]:
		if e["type"] == "board":
			board[e["b"]] = e["a"]
	var visuals := {}
	var bn := get_node_or_null("Environment/boats")
	if bn:
		for c in bn.find_children("BOAT_*", "Node3D", true, false):
			visuals[String(c.name).substr(0, 7)] = c
	i = 0
	for rec in L["boats"]:
		var b := Boat.new()
		b.name = rec["id"]
		b.object_id = rec["id"]
		b.kind = "boat"
		b.boat_kind = rec["kind"]
		b.nav_node = board.get(rec["mooring"], "")
		root.add_child(b)
		var mp: Vector3 = graph.pos[rec["mooring"]]
		b.home_pos = Vector3(mp.x, 0, mp.z)
		b.pos = b.home_pos
		b.visual = visuals.get(rec["id"])
		b.engine = rec["kind"] == "fishing_boat"
		if b.visual:
			b.home_yaw = b.visual.rotation.y
			_fit_boat_gear(b)
		var gid: String = ["FG_A", "FG_B", "FG_C"][i % 3]
		b.ground = grounds[gid]
		b.route = [b.home_pos] + lanes[gid]
		b.use_position = graph.pos[b.nav_node] if b.nav_node != "" else b.home_pos
		ledger.open(rec["id"], 0)
		boats[rec["id"]] = b
		interactables.append(b)
		i += 1

var _swim_spots := {}
func swim_spot(node: String) -> Vector3:
	## A point in the water a few metres off a beach node (found once by probing the rock collision).
	if _swim_spots.has(node):
		return _swim_spots[node]
	var p: Vector3 = graph.pos.get(node, Vector3.ZERO)
	var best := p + Vector3(0, 0, 5)
	if is_inside_tree():
		var space := get_world_3d().direct_space_state
		for i in 16:
			var a := TAU * i / 16.0
			var q := p + Vector3(cos(a), 0, sin(a)) * 5.5
			var ray := PhysicsRayQueryParameters3D.create(q + Vector3(0, 20, 0), q + Vector3(0, -20, 0))
			var hit := space.intersect_ray(ray)
			if hit.is_empty() or hit["position"].y < -0.6:
				best = q
				break
	_swim_spots[node] = Vector3(best.x, 0, best.z)
	return _swim_spots[node]

func _fit_boat_gear(b: Boat) -> void:
	## Oars in rowlocks for skiffs, an outboard motor on the transom for fishing boats.
	## Bow is +x in the boat models; the gear is animated by atmosphere.gd.
	var aabb := AABB()
	var first := true
	var inv: Transform3D = b.visual.global_transform.affine_inverse()
	for mi in b.visual.find_children("*", "MeshInstance3D", true, false):
		var bb: AABB = (inv * mi.global_transform) * mi.get_aabb()       # in the boat's own frame
		aabb = bb if first else aabb.merge(bb)
		first = false
	var L: float = maxf(aabb.size.x, 3.0)
	var W: float = maxf(aabb.size.z, 1.0)
	var top: float = aabb.position.y + aabb.size.y * 0.55
	if first or aabb.size.y < 0.3:
		# hull measurements of the boat models (blender/livingtides/environment.py boat())
		L = 6.2 if b.engine else 3.6
		W = 1.9 if b.engine else 1.15
		top = 0.62 if b.engine else 0.42
		aabb = AABB(Vector3(-L / 2.0, 0.0, -W / 2.0), Vector3(L, top / 0.55, W))
	var wood := StandardMaterial3D.new(); wood.albedo_color = Color(0.55, 0.4, 0.26); wood.roughness = 0.8
	var dark := StandardMaterial3D.new(); dark.albedo_color = Color(0.12, 0.12, 0.13); dark.roughness = 0.45; dark.metallic = 0.4
	if not b.engine:
		for side in [-1, 1]:
			var piv := Node3D.new()
			piv.name = "Oar%d" % side
			piv.position = Vector3(aabb.get_center().x - L * 0.05, top, side * W * 0.48)
			b.visual.add_child(piv)
			var shaft := MeshInstance3D.new()
			var cm := CylinderMesh.new(); cm.top_radius = 0.022; cm.bottom_radius = 0.022; cm.height = 2.3
			shaft.mesh = cm; shaft.material_override = wood
			shaft.rotation = Vector3(PI / 2, 0, 0)
			shaft.position = Vector3(0, 0, side * 0.75)
			piv.add_child(shaft)
			var blade := MeshInstance3D.new()
			var bx := BoxMesh.new(); bx.size = Vector3(0.16, 0.02, 0.5)
			blade.mesh = bx; blade.material_override = wood
			blade.position = Vector3(0, 0, side * 1.75)
			piv.add_child(blade)
			b.gear["oar%d" % side] = piv
	else:
		var motor := Node3D.new()
		motor.name = "Outboard"
		motor.position = Vector3(aabb.position.x - 0.05, top - 0.05, 0)
		b.visual.add_child(motor)
		var head := MeshInstance3D.new()
		var hb := BoxMesh.new(); hb.size = Vector3(0.32, 0.36, 0.26)
		head.mesh = hb; head.material_override = dark; head.position = Vector3(-0.08, 0.2, 0)
		motor.add_child(head)
		var leg := MeshInstance3D.new()
		var lb := BoxMesh.new(); lb.size = Vector3(0.08, 0.7, 0.06)
		leg.mesh = lb; leg.material_override = dark; leg.position = Vector3(-0.12, -0.3, 0)
		motor.add_child(leg)
		var prop := Node3D.new(); prop.position = Vector3(-0.12, -0.62, 0)
		motor.add_child(prop)
		for k in 3:
			var bl := MeshInstance3D.new()
			var pb := BoxMesh.new(); pb.size = Vector3(0.02, 0.14, 0.05)
			bl.mesh = pb; bl.material_override = dark
			bl.rotation = Vector3(k * TAU / 3.0, 0, 0.4)
			prop.add_child(bl)
		var tiller := MeshInstance3D.new()
		var tb := CylinderMesh.new(); tb.top_radius = 0.015; tb.bottom_radius = 0.015; tb.height = 0.6
		tiller.mesh = tb; tiller.material_override = dark
		tiller.rotation = Vector3(0, 0, PI / 2 - 0.2); tiller.position = Vector3(0.25, 0.3, 0)
		motor.add_child(tiller)
		b.gear["motor"] = motor
		b.gear["prop"] = prop

func _spawn_villagers() -> void:
	villager_root = Node3D.new()
	villager_root.name = "Villagers"
	add_child(villager_root)
	var recs: Array = VillageDB.population.get("villagers", [])
	for rec in recs:
		if buildings.has(rec["home"]):
			add_villager(rec)
	# placeholder data: two adults sharing a home start as a couple
	for hh in households:
		var m: Array = villagers.filter(func(x): return x.hh == hh)
		if m.size() == 2 and m[0].partner == "" and m[1].partner == "":
			m[0].partner = m[1].villager_id
			m[1].partner = m[0].villager_id
			society.bonds[Society.key(m[0].villager_id, m[1].villager_id)] = 70.0

func add_villager(rec: Dictionary):
	if villager_root == null:
		villager_root = Node3D.new()
		villager_root.name = "Villagers"
		add_child(villager_root)
	var v := Villager.new()
	villager_root.add_child(v)
	v.setup(rec, self)
	if v.bed == null:
		v.queue_free()
		return null
	villagers.append(v)
	households[v.hh]["members"] += 1
	if not people.has(v.villager_id):
		people[v.villager_id] = {"name": v.display_name, "parents": v.parents.duplicate(), "born_day": GameClock.day() - int(v.age * society.days_per_year),
			"age_at_arrival": v.age, "arrived_day": GameClock.day(), "died_day": -1, "native": not rec.has("age") or float(rec.get("age", 30.0)) < 0.5}
	if v.animator:
		v.animator.visible = figures_visible
	return v

func remove_villager(v) -> void:
	if people.has(v.villager_id):
		var pe: Dictionary = people[v.villager_id]
		pe["died_day"] = GameClock.day()
		pe["age_at_death"] = v.age
		pe["partner"] = v.partner
		pe["children"] = v.children.duplicate()
		pe["household"] = v.hh
		pe["last_job"] = v.job["role"] if v.job != null else ""
	v.shutdown()
	release_job(v)
	households[v.hh]["members"] -= 1
	villagers.erase(v)
	v.queue_free()

func villager_by_id(id: String):
	for v in villagers:
		if v.villager_id == id:
			return v
	return null

func free_bed(b: Building) -> Bed:
	for o in b.interactables:
		if o is Bed and o.owner_id == "":
			return o
	return null

func move_household(v, to_hh: String) -> bool:
	## The villager joins another household if its home has a spare bed.
	var b: Building = buildings[households[to_hh]["building"]]
	var nb := free_bed(b)
	if nb == null:
		return false
	if v.bed:
		v.bed.release(v)
		if v.shares_bed_of != "":
			v.bed.co_sleepers.erase(v.villager_id)
			v.shares_bed_of = ""
		else:
			v.bed.owner_id = ""
	households[v.hh]["members"] -= 1
	v.hh = to_hh
	v.home = b
	v.bed = nb
	nb.owner_id = v.villager_id
	households[to_hh]["members"] += 1
	society.record("moved", [v.villager_id], "to %s" % b.record["name"], "a bed was free there")
	return true

func release_job(v) -> void:
	if v.job != null:
		open_jobs.append(v.job)
		v.job = null

func assign_free_job(v) -> bool:
	## A young adult chooses among the open jobs: a parent's trade pulls, and so does what they are good at.
	if v.job != null or open_jobs.is_empty():
		return false
	var parent_roles := []
	for pid in v.parents:
		var pv = villager_by_id(pid)
		if pv and pv.job != null:
			parent_roles.append(pv.job["role"])
	var best := 0
	var bs := -1.0
	for i in open_jobs.size():
		var role: String = open_jobs[i]["role"]
		var skill: String = {"fisher": "fishing", "cook": "cooking", "carpenter": "carpentry", "apprentice": "carpentry", "boatwright": "carpentry"}.get(role, "trade")
		var sc: float = v.skills[skill] + (0.35 if parent_roles.has(role) else 0.0) + (0.25 if role == "fisher" and v.ambition == "sea" else 0.0) + v.rng.randf() * 0.3
		if sc > bs:
			bs = sc
			best = i
	v.job = open_jobs[best]
	open_jobs.remove_at(best)
	var why := "follows a parent's trade" if parent_roles.has(v.job["role"]) else "own choice among %d open jobs" % (open_jobs.size() + 1)
	society.record("hired", [v.villager_id], String(v.job["role"]), why)
	return true

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
	day_night.village = self
	add_child(day_night)
	if low_quality:
		var phone: bool = DisplayServer.is_touchscreen_available()
		var vp := get_viewport()
		vp.msaa_3d = Viewport.MSAA_DISABLED
		vp.scaling_3d_scale = 0.6 if phone else 0.8          # the 3D view renders at fewer pixels; the UI stays sharp
		day_night.sun.shadow_enabled = not phone              # the shadow pass redraws the whole village
		day_night.sun.directional_shadow_mode = DirectionalLight3D.SHADOW_ORTHOGONAL
		day_night.sun.directional_shadow_max_distance = 140.0
		day_night.moon.shadow_enabled = false
		for id in buildings:
			var ls: Array = buildings[id].lights
			while ls.size() > 1:
				ls.pop_back().queue_free()
	var atmo = load("res://scripts/world/atmosphere.gd").new()
	atmo.name = "Atmosphere"
	atmo.village = self
	atmosphere = atmo
	camera_rig = load("res://scripts/camera/orbit_camera.gd").new()
	camera_rig.name = "CameraRig"
	add_child(camera_rig)
	camera_rig.village = self
	hud = load("res://scripts/ui/hud.gd").new()
	hud.name = "HUD"
	add_child(hud)
	hud.village = self
	hud.attach()
	add_child(atmo)
	var life = load("res://scripts/world/village_life.gd").new()
	life.setup(self)
	add_child(life)
	village_life = life
	if show_heroes:
		var hs = load("res://scripts/world/hero_showcase.gd").new()
		if hs.setup(self):
			add_child(hs)
			hero_showcase = hs
		else:
			hs.free()

func set_figures_visible(on: bool) -> void:
	## Simulation agents keep running; only the temporary figures are hidden.
	figures_visible = on
	for v in villagers:
		if v.animator:
			v.animator.visible = on

func cut_sides() -> Array:
	## Wall groups that face the camera and should fade.
	if camera_rig == null:
		return ["S", "E"]
	var d: Vector3 = camera_rig.cam.global_position - camera_rig.target
	return ["S" if d.z > 0.0 else "N", "E" if d.x > 0.0 else "W"]

func toggle_cutaway(id: String = "") -> void:
	if id != "" and buildings.has(id):
		buildings[id].set_cutaway(not buildings[id].cutaway, cut_sides())
		return
	var any := false
	for k in buildings:
		any = any or buildings[k].cutaway
	for k in buildings:
		buildings[k].set_cutaway(not any, cut_sides())

func person_name(id: String) -> String:
	var v = villager_by_id(id)
	if v:
		return v.display_name
	return people[id]["name"] if people.has(id) else id

func is_alive(id: String) -> bool:
	return villager_by_id(id) != null

func children_of(id: String) -> Array:
	var v = villager_by_id(id)
	if v:
		return v.children
	return people[id].get("children", []) if people.has(id) else []

func parents_of(id: String) -> Array:
	var v = villager_by_id(id)
	if v:
		return v.parents
	return people[id].get("parents", []) if people.has(id) else []

func earners(hh: String) -> int:
	return villagers.filter(func(x): return x.hh == hh and x.job != null).size()
