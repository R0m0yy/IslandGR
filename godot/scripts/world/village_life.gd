extends Node3D
## Ambient life around the simulation (presentation only: no ledger, no saves):
##  - market stalls on the quay outside the fish market: fish on ice, fruit, bread,
##    each with a stallholder (a character model) who serves residents who stop by:
##    reaches into the display, hands the item over, the customer walks off holding it
##  - a small plane crossing the sky now and then, a sailing boat on the horizon
## The fish market itself (P01) is the real economy: see ShopState in activities.gd.

var village = null
var stalls: Array = []              # {node, vendor (VillagerAnimator), item, pos, cool}
var plane: Node3D = null
var _plane_t: float = 30.0
var _plane_from := Vector3.ZERO
var _plane_dir := Vector3.ZERO
var sailboat: Node3D = null
var _sail_a: float = 0.0
var _mats := {}

func setup(v) -> void:
	village = v
	name = "VillageLife"

func _ready() -> void:
	_build_stalls()
	_build_plane()
	_build_sailboat()

# ------------------------------------------------------------------ helpers
func _mat(c: Color) -> StandardMaterial3D:
	var k := c.to_html()
	if not _mats.has(k):
		var m := StandardMaterial3D.new()
		m.albedo_color = c
		m.roughness = 0.75
		_mats[k] = m
	return _mats[k]

func _part(parent: Node3D, mesh: Mesh, c: Color, pos: Vector3, rot := Vector3.ZERO, scl := Vector3.ONE) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	mi.material_override = _mat(c)
	mi.position = pos
	mi.rotation = rot
	mi.scale = scl
	parent.add_child(mi)
	return mi

func _box(x: float, y: float, z: float) -> BoxMesh:
	var b := BoxMesh.new(); b.size = Vector3(x, y, z); return b

func _sph(r: float) -> SphereMesh:
	var s := SphereMesh.new(); s.radius = r; s.height = r * 2.0; s.radial_segments = 10; s.rings = 6; return s

func _cyl(r: float, h: float, r2: float = -1.0) -> CylinderMesh:
	var c := CylinderMesh.new(); c.top_radius = r; c.bottom_radius = r if r2 < 0.0 else r2; c.height = h; c.radial_segments = 12; return c

func _ground(x: float, z: float) -> float:
	var space := get_world_3d().direct_space_state
	var hit := space.intersect_ray(PhysicsRayQueryParameters3D.create(Vector3(x, 30, z), Vector3(x, -10, z)))
	return hit["position"].y if not hit.is_empty() else -99.0

# ------------------------------------------------------------------ market stalls
func _build_stalls() -> void:
	if not village.graph.pos.has("q_n_mkt"):
		return
	var specs := [
		{"x": 6.4, "item": "fish", "awning": [Color(0.85, 0.2, 0.18), Color(0.96, 0.95, 0.92)], "vendor": "V02"},
		{"x": 9.6, "item": "fruit", "awning": [Color(0.24, 0.6, 0.32), Color(0.95, 0.83, 0.3)], "vendor": "V05"},
		{"x": 12.6, "item": "bread", "awning": [Color(0.2, 0.42, 0.75), Color(0.96, 0.95, 0.92)], "vendor": "V06"},
	]
	var quay_y: float = village.graph.pos["q_n_mkt"].y
	for sp in specs:
		# between the market front and the walking line, on solid quay
		var z := 2.6
		var gy := _ground(sp["x"], z)
		if gy < quay_y - 0.6:
			continue
		var st := Node3D.new()
		st.name = "Stall_" + sp["item"]
		st.position = Vector3(sp["x"], gy, z)
		add_child(st)
		_stall_frame(st, sp["awning"])
		_display(st, sp["item"])
		var vend := VillagerAnimator.new()
		vend.name = "Vendor"
		var holder := Node3D.new()
		holder.position = Vector3(0, 0, -0.75)          # behind the table, facing the quay (+z)
		holder.rotation.y = PI
		st.add_child(holder)
		holder.add_child(vend)
		if ResourceLoader.exists("res://assets/characters/%s.glb" % sp["vendor"]):
			vend.build_model(sp["vendor"], "stall_" + sp["item"])
		else:
			vend.build()
		stalls.append({"node": st, "vendor": vend, "item": sp["item"], "pos": st.global_position + Vector3(0, 0, 0.9), "cool": 0.0, "t": randf() * 6.0})

func _stall_frame(st: Node3D, stripes: Array) -> void:
	var wood := Color(0.55, 0.39, 0.25)
	_part(st, _box(1.8, 0.07, 0.8), wood, Vector3(0, 0.88, 0))                     # table top
	_part(st, _box(1.75, 0.6, 0.04), wood.darkened(0.15), Vector3(0, 0.55, 0.38))   # front board
	for x in [-0.85, 0.85]:
		for zz in [-0.35, 0.35]:
			_part(st, _box(0.06, 0.88, 0.06), wood, Vector3(x, 0.44, zz))
		_part(st, _box(0.06, 2.3, 0.06), wood, Vector3(x, 1.15, -0.45))            # awning posts
		_part(st, _box(0.06, 2.05, 0.06), wood, Vector3(x, 1.02, 0.55))
	# striped canvas awning sloping toward the customers
	var n := 8
	for i in n:
		var c: Color = stripes[i % 2]
		_part(st, _box(2.0 / n, 0.025, 1.3), c, Vector3(-1.0 + (i + 0.5) * 2.0 / n, 2.2, 0.05), Vector3(-0.18, 0, 0))
	for i in n:          # scalloped valance
		_part(st, _box(2.0 / n * 0.95, 0.18, 0.02), stripes[i % 2], Vector3(-1.0 + (i + 0.5) * 2.0 / n, 2.02, 0.69))

func _display(st: Node3D, item: String) -> void:
	var y := 0.92
	match item:
		"fish":
			_part(st, _box(1.6, 0.08, 0.65), Color(0.88, 0.94, 0.97), Vector3(0, y + 0.03, 0))      # crushed ice
			var meshes := _animal_meshes()
			var kinds := ["snapper", "mackerel", "scad"]
			for i in 12:
				var k: String = kinds[i % 3]
				var p := Vector3(-0.65 + (i % 6) * 0.26, y + 0.1, -0.15 + (i / 6) * 0.3)
				if meshes.has(k):
					var f := MeshInstance3D.new()
					f.mesh = meshes[k]
					f.position = p
					f.rotation = Vector3(PI / 2, 0.3 * ((i % 3) - 1), 0)
					f.scale = Vector3.ONE * (0.7 if k != "scad" else 1.0)
					st.add_child(f)
				else:
					_part(st, _box(0.3, 0.05, 0.08), Color(0.6, 0.65, 0.7), p)
			_part(st, _box(0.35, 0.25, 0.02), Color(0.95, 0.93, 0.85), Vector3(0.7, 1.3, 0.4), Vector3(-0.3, 0, 0))   # price slate
		"fruit":
			for bx in [-0.55, 0.0, 0.55]:
				_part(st, _cyl(0.24, 0.18, 0.2), Color(0.66, 0.5, 0.3), Vector3(bx, y + 0.09, 0))
			for i in 9:
				_part(st, _sph(0.05), Color(0.96, 0.55 + 0.03 * (i % 3), 0.12), Vector3(-0.55 + (i % 3) * 0.08 - 0.08, y + 0.2, (i / 3) * 0.08 - 0.08))
			for i in 4:
				_part(st, CapsuleMesh.new(), Color(0.97, 0.84, 0.26), Vector3(0.0 + (i - 1.5) * 0.06, y + 0.21, 0.0), Vector3(0, 0, 1.3), Vector3(0.14, 0.2, 0.14))
			for i in 9:
				_part(st, _sph(0.035), Color(0.42, 0.72, 0.22), Vector3(0.55 + (i % 3) * 0.07 - 0.07, y + 0.2, (i / 3) * 0.07 - 0.07))
			for i in 3:
				_part(st, _sph(0.075), Color(0.42, 0.28, 0.16), Vector3(-0.3 + i * 0.3, y + 0.08, 0.28))   # coconuts
		"bread":
			for i in 10:
				_part(st, CapsuleMesh.new(), Color(0.86, 0.6, 0.3), Vector3(-0.65 + (i % 5) * 0.32, y + 0.07, -0.12 + (i / 5) * 0.26), Vector3(0, 0.4, PI / 2), Vector3(0.22, 0.3, 0.22))
			_part(st, _cyl(0.2, 0.12, 0.17), Color(0.72, 0.55, 0.32), Vector3(0.0, y + 0.06, 0.25))

func _animal_meshes() -> Dictionary:
	var out := {}
	if ResourceLoader.exists("res://assets/env/animals.glb"):
		var sc: Node = load("res://assets/env/animals.glb").instantiate()
		for mi in sc.find_children("ANIMAL_*", "MeshInstance3D", true, false):
			out[String(mi.name).substr(7)] = mi.mesh
		sc.free()
	return out

func _serve(dt: float) -> void:
	for st in stalls:
		var vend: VillagerAnimator = st["vendor"]
		st["cool"] = maxf(0.0, st["cool"] - dt)
		st["t"] += dt
		var customer = null
		if st["cool"] <= 0.0:
			for v in village.villagers:
				if v.fsm.current_name == "idle" and not v.at_sea and v.global_position.distance_to(st["pos"]) < 3.2:
					customer = v
					break
		if customer:
			# the stallholder reaches into the display and hands it over; the customer takes it
			st["cool"] = 14.0
			vend.play("give")
			vend.show_prop(st["item"], true, 1.6)
			customer.react("give", 2.6)
			customer.face(st["pos"] - customer.global_position)
			if customer.animator:
				customer.animator.show_prop(st["item"], false)
				get_tree().create_timer(1.6).timeout.connect(func():
					if is_instance_valid(customer) and customer.animator:
						customer.animator.show_prop(st["item"], true, 30.0))
		elif st["cool"] <= 10.0:
			# between customers: tidy the display, chat to passers-by, call out
			var cyc := fmod(st["t"], 16.0)
			vend.play("talk" if cyc < 6.0 else ("sweep" if cyc < 9.0 and st["item"] != "fish" else "idle"))

# ------------------------------------------------------------------ sky and horizon
func _build_plane() -> void:
	plane = Node3D.new()
	plane.name = "Plane"
	add_child(plane)
	var white := Color(0.94, 0.94, 0.92)
	var trim := Color(0.8, 0.22, 0.18)
	_part(plane, CapsuleMesh.new(), white, Vector3.ZERO, Vector3(0, 0, PI / 2), Vector3(1.0, 4.4, 1.0))       # fuselage along x
	_part(plane, _box(1.6, 0.08, 9.0), white, Vector3(0.4, 0.45, 0))                                              # high wing
	_part(plane, _box(0.8, 0.06, 3.2), white, Vector3(-3.6, 0.2, 0))                                              # tailplane
	_part(plane, _box(0.9, 1.3, 0.06), trim, Vector3(-3.7, 0.75, 0))                                              # fin
	_part(plane, _box(2.5, 0.12, 0.08), trim, Vector3(0.4, 0.0, 1.0))
	_part(plane, _box(2.5, 0.12, 0.08), trim, Vector3(0.4, 0.0, -1.0))
	var prop := Node3D.new(); prop.name = "Prop"; prop.position = Vector3(2.3, 0, 0)
	plane.add_child(prop)
	_part(prop, _box(0.06, 2.0, 0.14), Color(0.15, 0.15, 0.15), Vector3.ZERO)
	for sgn in [-1.0, 1.0]:             # floats: a little seaplane
		_part(plane, CapsuleMesh.new(), white, Vector3(0.2, -1.4, sgn * 1.3), Vector3(0, 0, PI / 2), Vector3(0.45, 2.8, 0.45))
	plane.visible = false

func _launch_plane() -> void:
	var a := randf() * TAU
	_plane_dir = Vector3(cos(a), 0, sin(a))
	_plane_from = -_plane_dir * 260.0 + Vector3(randf_range(-40, 40), randf_range(48.0, 70.0), randf_range(-40, 40))
	plane.global_position = _plane_from
	plane.rotation.y = atan2(-_plane_dir.z, _plane_dir.x)
	plane.visible = true

func _build_sailboat() -> void:
	sailboat = Node3D.new()
	sailboat.name = "Sailboat"
	add_child(sailboat)
	_part(sailboat, _box(5.0, 0.8, 1.6), Color(0.95, 0.93, 0.88), Vector3(0, 0.3, 0))
	_part(sailboat, _box(0.12, 6.5, 0.12), Color(0.5, 0.4, 0.3), Vector3(0.3, 3.5, 0))
	var pm := PrismMesh.new(); pm.size = Vector3(3.2, 5.6, 0.04); pm.left_to_right = 0.0
	_part(sailboat, pm, Color(0.97, 0.96, 0.92), Vector3(-1.2, 3.6, 0))
	var jib := PrismMesh.new(); jib.size = Vector3(2.0, 4.6, 0.04); jib.left_to_right = 1.0
	_part(sailboat, jib, Color(0.92, 0.35, 0.28), Vector3(1.5, 3.1, 0))

func _process(dt: float) -> void:
	if village == null:
		return
	_serve(dt)
	# the plane: every few minutes, straight across, propeller turning
	if plane.visible:
		plane.global_position += _plane_dir * 32.0 * dt
		plane.get_node("Prop").rotation.x += dt * 60.0
		plane.rotation.z = 0.04 * sin(Time.get_ticks_msec() / 900.0)
		if plane.global_position.distance_to(_plane_from) > 520.0:
			plane.visible = false
			_plane_t = randf_range(90.0, 240.0)
	else:
		_plane_t -= dt
		if _plane_t <= 0.0:
			_launch_plane()
	# the yacht reaches slowly round the island far out, heeling to the wind
	_sail_a += dt * 0.004 * (1.0 + village.weather.wind)
	var r := 150.0
	var p := Vector3(cos(_sail_a) * r, 0, sin(_sail_a) * r * 0.8)
	p.y = village.ocean.height(p.x, p.z) - 0.1
	sailboat.global_position = p
	var tan_ := Vector3(-sin(_sail_a), 0, cos(_sail_a) * 0.8).normalized()
	sailboat.rotation = Vector3(0, atan2(-tan_.z, tan_.x), 0.12 + 0.08 * village.weather.wind)
