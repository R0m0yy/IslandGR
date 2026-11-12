class_name Building
extends Node3D
## One building prefab instance: the GLB from Blender plus everything the
## simulation needs from BUILDING_CONTRACT.md - interactables at the anchors,
## an interior walk graph stitched to the village graph at the door, fadeable
## wall groups, lights and persistent state.

const GROUPS := ["WALL_S", "WALL_E", "WALL_N", "WALL_W", "ROOF", "BASE", "INTERIOR", "FLOOR2", "DOOR_main"]

var building_id: String = ""
var record: Dictionary = {}            # layout record
var sidecar: Dictionary = {}
var model: Node3D = null
var groups: Dictionary = {}            # group name (WALL_S, ROOF, ...) -> Node3D
var interactables: Array = []
var door: Door = null
var lights: Array = []
var state: Dictionary = {"condition": 1.0, "lights_on": false, "door_open": false}
var cutaway: bool = false
var merged: MeshInstance3D = null       # all exterior groups as one mesh (few draw calls); groups show only in cutaway
static var merge_exteriors: bool = true
var _lit_glass: StandardMaterial3D = null

func setup(id: String) -> void:
	building_id = id
	name = "BLD_" + id
	record = VillageDB.buildings[id]
	sidecar = VillageDB.sidecars[id]
	state = record.get("state", state).duplicate()
	transform = VillageDB.building_transform(id)
	var scene: PackedScene = load("res://assets/buildings/%s.glb" % id)
	if scene:
		model = scene.instantiate()
		add_child(model)
		_index_groups(model)
	if merge_exteriors and model and DisplayServer.get_name() != "headless":
		_merge_exterior()   # skipped on the headless dummy renderer (no mesh data there)
	_make_interactables()

func _merge_exterior() -> void:
	## A building is ~9 nodes x 3-4 materials = ~30 draw calls. Seen from outside
	## it only needs one mesh with one surface per material. The separate groups
	## (and the interior) are kept for cutaway and switched in on demand.
	var by_mat := {}
	var inv := global_transform.affine_inverse()
	for g in groups:
		if g == "DOOR_main" or g == "INTERIOR" or g == "FLOOR2":
			continue
		for mi in _mesh_nodes(groups[g]):
			var mesh: Mesh = mi.mesh
			for si in mesh.get_surface_count():
				var mat := mesh.surface_get_material(si)
				if not by_mat.has(mat):
					var st := SurfaceTool.new()
					st.begin(Mesh.PRIMITIVE_TRIANGLES)
					by_mat[mat] = st
				by_mat[mat].append_from(mesh, si, inv * mi.global_transform)
	var out := ArrayMesh.new()
	for mat in by_mat:
		by_mat[mat].commit(out)
		out.surface_set_material(out.get_surface_count() - 1, mat)
	merged = MeshInstance3D.new()
	merged.name = "EXTERIOR_merged"
	merged.mesh = out
	model.add_child(merged)
	merged.global_transform = global_transform
	_show_groups(false)

func _mesh_nodes(n: Node) -> Array:
	var out := []
	if n is MeshInstance3D and n.mesh != null:
		out.append(n)
	for c in n.find_children("*", "MeshInstance3D", true, false):
		if c.mesh != null:
			out.append(c)
	return out

func _show_groups(on: bool, hide_sides: Array = []) -> void:
	for g in groups:
		if g == "DOOR_main":
			continue
		var vis: bool = on
		if on and (g == "ROOF" or g == "FLOOR2" or (g.begins_with("WALL_") and hide_sides.has(g.substr(5)))):
			vis = false
		groups[g].visible = vis

func _index_groups(n: Node) -> void:
	for c in n.get_children():
		var nm := String(c.name)
		var prefix := building_id + "_"
		if nm.begins_with(prefix) and c is Node3D:
			var g := nm.substr(prefix.length())
			# the importer may add a numeric suffix to keep names unique
			while g.length() > 0 and g[g.length() - 1].is_valid_int() and not GROUPS.has(g):
				g = g.substr(0, g.length() - 1)
			if GROUPS.has(g):
				groups[g] = c
		_index_groups(c)

func to_world(local) -> Vector3:
	return global_transform * Vector3(local[0], local[1], local[2])

func dir_world(f) -> Vector3:
	return (global_transform.basis * Vector3(f[0], 0.0, f[1])).normalized()

func node_id(local_name: String) -> String:
	if local_name == "out":
		return "door_" + building_id
	return building_id + ":" + local_name

func _make_interactables() -> void:
	for a in sidecar.get("anchors", []):
		var t: String = a["type"]
		if t == "lamp":
			var l := OmniLight3D.new()
			l.name = a["id"]
			l.position = Vector3(a["pos"][0], a["pos"][1], a["pos"][2])
			l.light_color = Color(1.0, 0.82, 0.55)
			l.light_energy = 1.4
			l.omni_range = 5.0
			l.shadow_enabled = false
			l.visible = false
			add_child(l)
			lights.append(l)
			continue
		if t == "stairs_interior":
			continue
		var obj: Interactable
		match t:
			"door":
				door = Door.new()
				obj = door
				door.setup(groups.get("DOOR_main"), a.get("open_deg", 100.0))
			"bed":
				obj = Bed.new()
			"stove":
				var cs := CookingStation.new()
				obj = cs
				if a.has("light"):
					var fl := OmniLight3D.new()
					fl.position = Vector3(a["light"][0], a["light"][1], a["light"][2])
					fl.light_color = Color(1.0, 0.55, 0.2)
					fl.light_energy = 1.8
					fl.omni_range = 3.5
					fl.visible = false
					add_child(fl)
					cs.light = fl
			_:
				obj = Interactable.new()
		obj.name = a["id"]
		obj.object_id = building_id + ":" + a["id"]
		obj.kind = t
		obj.pose = a["pose"] if a.get("pose") != null else "stand"
		obj.building = self
		obj.position = Vector3(a["pos"][0], a["pos"][1], a["pos"][2])
		add_child(obj)
		obj.use_position = to_world(a["pos"])
		if a.get("facing") != null:
			obj.facing = dir_world(a["facing"])
		if a.get("stand") != null and t != "door":
			obj.nav_node = node_id(a["id"])
		interactables.append(obj)

func register_nav(graph: NavGraph) -> void:
	var nav: Dictionary = sidecar["nav"]
	for k in nav["nodes"]:
		if k == "out":
			continue
		graph.add_node(node_id(k), to_world(nav["nodes"][k]), {"building": building_id})
	for e in nav["edges"]:
		var ref = door if e["type"] == "doorway" else null
		graph.add_edge(node_id(e["a"]), node_id(e["b"]), e["type"], ref)

func find(kind_name: String, who = null) -> Interactable:
	for o in interactables:
		if o.kind == kind_name and o.is_available(who):
			return o
	return null

func all_of(kind_name: String) -> Array:
	return interactables.filter(func(o): return o.kind == kind_name)

func set_lights(on: bool) -> void:
	if state.get("lights_on", false) == on and (lights.is_empty() or lights[0].visible == on):
		return
	state["lights_on"] = on
	for l in lights:
		l.visible = on
	_set_glass(on)

func _set_glass(on: bool) -> void:
	if model == null or DisplayServer.get_name() == "headless":
		return
	if _lit_glass == null:
		_lit_glass = StandardMaterial3D.new()
		_lit_glass.albedo_color = Color(1.0, 0.86, 0.55)
		_lit_glass.emission_enabled = true
		_lit_glass.emission = Color(1.0, 0.78, 0.42)
		_lit_glass.emission_energy_multiplier = 2.2
	for mi in model.find_children("*", "MeshInstance3D", true, false):
		var mesh: Mesh = mi.mesh
		if mesh == null:
			continue
		for s in mesh.get_surface_count():
			var m := mesh.surface_get_material(s)
			if m and m.resource_name == "LT_glass":
				mi.set_surface_override_material(s, _lit_glass if on else null)

func set_cutaway(on: bool, hide_sides: Array = ["S", "E"]) -> void:
	## Fades the camera-facing wall groups and lifts the roof (BUILDING_CONTRACT).
	cutaway = on
	if merged:
		merged.visible = not on
		_show_groups(on, hide_sides)
		return
	for g in groups:
		var hide: bool = on and (g == "ROOF" or g == "FLOOR2" or (g.begins_with("WALL_") and hide_sides.has(g.substr(5))))
		groups[g].visible = not hide
