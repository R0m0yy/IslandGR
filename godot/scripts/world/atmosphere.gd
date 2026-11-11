extends Node3D
## Presentation of the living world. Draws what the simulation says is true:
## every animal comes from Ecosystem state, boats ride the shared Ocean wave
## model, rain and sea state follow Weather. Nothing here changes the
## simulation. Animal shapes are simple placeholders (not final art).

const SWAY := preload("res://shaders/foliage_sway.gdshader")

var village = null
var rain: CPUParticles3D
var watchables: Array = []          # [label, Node3D] for the observer's wildlife camera
var _sea: ShaderMaterial = null
var _sway: ShaderMaterial = null
var _player: AudioStreamPlayer = null
var _play: AudioStreamGeneratorPlayback = null
var _lp = [0.0, 0.0, 0.0]
var _at = 0.0
var _boat_y = {}
var _wakes = {}
var _birds = {}
var _schools = {}
var _hunters = {}
var _dolphins = {}
var _turtles = {}
var _crabs = {}
var _scraps: Node3D
var _mats = {}

func _mat(c: Color, unshaded := false) -> StandardMaterial3D:
	var k = c.to_html() + str(unshaded)
	if not _mats.has(k):
		var m = StandardMaterial3D.new()
		m.albedo_color = c
		m.roughness = 0.85
		m.cull_mode = BaseMaterial3D.CULL_DISABLED
		if unshaded:
			m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		_mats[k] = m
	return _mats[k]

func _mesh(parent: Node3D, mesh: Mesh, c: Color, pos := Vector3.ZERO, rot := Vector3.ZERO, scl := Vector3.ONE, nm := "") -> MeshInstance3D:
	var mi = MeshInstance3D.new()
	mi.mesh = mesh
	mi.material_override = _mat(c)
	mi.position = pos
	mi.rotation = rot
	mi.scale = scl
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	if nm != "":
		mi.name = nm
	parent.add_child(mi)
	return mi

func _box(x: float, y: float, z: float) -> BoxMesh:
	var b = BoxMesh.new()
	b.size = Vector3(x, y, z)
	return b

func _sphere(r: float, h: float = -1.0) -> SphereMesh:
	var s = SphereMesh.new()
	s.radius = r
	s.height = r * 2.0 if h < 0.0 else h
	s.radial_segments = 8
	s.rings = 4
	return s

func _ready() -> void:
	rain = CPUParticles3D.new()
	rain.name = "Rain"
	rain.amount = 900
	rain.lifetime = 1.1
	rain.emission_shape = CPUParticles3D.EMISSION_SHAPE_BOX
	rain.emission_box_extents = Vector3(45, 1, 45)
	rain.direction = Vector3(0.15, -1, 0.05)
	rain.spread = 2.0
	rain.gravity = Vector3(0, -30, 0)
	rain.initial_velocity_min = 22.0
	rain.initial_velocity_max = 28.0
	var qm = QuadMesh.new()
	qm.size = Vector2(0.03, 0.9)
	var rm = StandardMaterial3D.new()
	rm.albedo_color = Color(0.8, 0.88, 0.95, 0.5)
	rm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	rm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	rm.billboard_mode = BaseMaterial3D.BILLBOARD_FIXED_Y
	qm.material = rm
	rain.mesh = qm
	rain.emitting = false
	add_child(rain)
	var sea = village.get_node_or_null("Environment/Sea")
	if sea:
		_sea = sea.material_override
	var veg = village.get_node_or_null("Environment/vegetation")
	if veg:
		_sway = ShaderMaterial.new()
		_sway.shader = SWAY
		for mi in veg.find_children("*", "MeshInstance3D", true, false):
			mi.material_override = _sway
	for b in village.boats.values():
		if b.visual:
			_boat_y[b] = b.visual.position.y
			_wakes[b] = _wake(b)
	_build_animals()
	_audio()

# ------------------------------------------------------------------ animals
func _build_animals() -> void:
	var eco: Ecosystem = village.ecosystem
	var root = Node3D.new()
	root.name = "Wildlife"
	add_child(root)
	var fish_col = {"scad": Color(0.55, 0.66, 0.76), "snapper": Color(0.86, 0.42, 0.40), "mackerel": Color(0.28, 0.52, 0.58)}
	for s in eco.schools:
		var n = Node3D.new()
		n.name = "School_" + s["id"]
		root.add_child(n)
		var fishes = []
		for i in 14:
			var f = _mesh(n, _box(0.32 if s["sp"] != "snapper" else 0.42, 0.08, 0.1), fish_col[s["sp"]])
			fishes.append(f)
		_schools[s["id"]] = [n, fishes]
		watchables.append(["%s school" % s["sp"], n])
	for h in eco.hunters:
		var n = Node3D.new()
		n.name = h["id"]
		root.add_child(n)
		_mesh(n, _box(1.3, 0.16, 0.18), Color(0.34, 0.38, 0.42))
		_mesh(n, _box(0.25, 0.25, 0.04), Color(0.3, 0.33, 0.37), Vector3(-0.68, 0.05, 0))
		_hunters[h["id"]] = n
		watchables.append(["barracuda", n])
	var pod = Node3D.new()
	pod.name = "DolphinPod"
	root.add_child(pod)
	watchables.append(["dolphin pod", pod])
	for d in eco.dolphins:
		var n = Node3D.new()
		n.name = d["id"]
		pod.add_child(n)
		_mesh(n, _sphere(0.28, 2.0), Color(0.48, 0.55, 0.62), Vector3.ZERO, Vector3(0, 0, PI / 2))
		_mesh(n, _box(0.08, 0.36, 0.22), Color(0.42, 0.48, 0.55), Vector3(0.05, 0.3, 0), Vector3(0, 0, -0.4), Vector3.ONE, "Fin")
		_mesh(n, _box(0.12, 0.06, 0.6), Color(0.42, 0.48, 0.55), Vector3(-0.98, 0, 0))
		_dolphins[d["id"]] = n
	for t in eco.turtles:
		var n = Node3D.new()
		n.name = t["id"]
		root.add_child(n)
		_mesh(n, _sphere(0.45, 0.32), Color(0.40, 0.42, 0.24))
		_mesh(n, _sphere(0.12), Color(0.55, 0.55, 0.38), Vector3(0.5, 0.02, 0))
		for fx in [-0.25, 0.25]:
			for fz in [-0.32, 0.32]:
				_mesh(n, _box(0.22, 0.03, 0.12), Color(0.5, 0.5, 0.33), Vector3(fx, -0.05, fz), Vector3(0, 0.5 * sign(fx * fz), 0))
		_turtles[t["id"]] = n
		watchables.append(["sea turtle", n])
	for c in eco.crabs:
		var n = Node3D.new()
		n.name = c["id"]
		root.add_child(n)
		_mesh(n, _box(0.14, 0.06, 0.11), Color(0.92, 0.82, 0.62))
		for sx in [-1, 1]:
			for k in 3:
				_mesh(n, _box(0.02, 0.02, 0.09), Color(0.88, 0.78, 0.6), Vector3(-0.04 + k * 0.04, -0.02, 0.08 * sx), Vector3(0.5 * sx, 0, 0))
		_crabs[c["id"]] = n
	watchables.append(["ghost crabs", _crabs[eco.crabs[0]["id"]]])
	var spec = {   # body colour, wing colour, wingspan, body length
		"gull": [Color(0.96, 0.96, 0.94), Color(0.7, 0.72, 0.76), 0.75, 0.32],
		"pelican": [Color(0.62, 0.55, 0.48), Color(0.45, 0.4, 0.36), 1.5, 0.6],
		"tern": [Color(0.97, 0.97, 0.97), Color(0.85, 0.87, 0.9), 0.55, 0.24],
		"frigatebird": [Color(0.12, 0.12, 0.14), Color(0.1, 0.1, 0.12), 1.7, 0.5],
		"sandpiper": [Color(0.62, 0.52, 0.4), Color(0.55, 0.45, 0.35), 0.22, 0.12],
	}
	for b in eco.birds:
		var sp: Array = spec[b["kind"]]
		var n = Node3D.new()
		n.name = b["id"]
		root.add_child(n)
		_mesh(n, _sphere(sp[3] * 0.4, sp[3]), sp[0], Vector3.ZERO, Vector3(0, 0, PI / 2))
		if b["kind"] == "pelican":
			_mesh(n, _box(0.36, 0.05, 0.07), Color(0.86, 0.66, 0.32), Vector3(0.38, 0.03, 0))
		if b["kind"] == "tern":
			_mesh(n, _sphere(0.055), Color(0.1, 0.1, 0.1), Vector3(0.12, 0.05, 0))
		if b["kind"] == "frigatebird":
			_mesh(n, _sphere(0.07), Color(0.85, 0.15, 0.15), Vector3(0.12, -0.06, 0))   # the red throat pouch
		if b["kind"] == "sandpiper":
			_mesh(n, _box(0.01, 0.1, 0.01), Color(0.2, 0.2, 0.2), Vector3(0, -0.08, 0))
		for sgn in [-1.0, 1.0]:
			var pm = PrismMesh.new()
			pm.size = Vector3(sp[2] * 0.5, sp[3] * 0.6, 0.02)
			var w = _mesh(n, pm, sp[1], Vector3(0, 0.02, sp[2] * 0.25 * sgn), Vector3(PI / 2, 0, 0), Vector3.ONE, "WingL" if sgn < 0 else "WingR")
		var fish = _mesh(n, _box(0.16, 0.04, 0.05), Color(0.75, 0.8, 0.85), Vector3(sp[3] * 0.5, -0.05, 0), Vector3.ZERO, Vector3.ONE, "Carry")
		fish.visible = false
		_birds[b["id"]] = n
		if b["kind"] in ["pelican", "frigatebird"] or b["id"] == "gull0":
			watchables.append([b["kind"], n])
	_scraps = Node3D.new()
	_scraps.name = "ScrapHeap"
	root.add_child(_scraps)
	_scraps.position = Ecosystem.SCRAP_HEAP
	for i in 10:
		var f = _mesh(_scraps, _box(0.3, 0.06, 0.09), Color(0.62, 0.66, 0.66), Vector3(randf_range(-0.35, 0.35), 0.03 + (i / 4) * 0.05, randf_range(-0.3, 0.3)), Vector3(0, randf() * TAU, 0))
		f.visible = false

func _wake(b) -> CPUParticles3D:
	var p = CPUParticles3D.new()
	p.amount = 40
	p.lifetime = 2.6
	p.local_coords = false
	p.direction = Vector3(0, 0.1, 0)
	p.spread = 30.0
	p.initial_velocity_min = 0.2
	p.initial_velocity_max = 0.5
	p.gravity = Vector3.ZERO
	p.scale_amount_min = 0.6
	p.scale_amount_max = 1.2
	var qm = QuadMesh.new()
	qm.size = Vector2(0.5, 0.5)
	qm.orientation = PlaneMesh.FACE_Y
	var m = StandardMaterial3D.new()
	m.albedo_color = Color(0.95, 0.98, 1.0, 0.55)
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	qm.material = m
	p.mesh = qm
	p.emitting = false
	add_child(p)
	return p

func _sea_y(p: Vector3) -> float:
	return village.ocean.height(p.x, p.z)

func _face(n: Node3D, from: Vector3, to: Vector3) -> void:
	var d = to - from
	d.y = 0.0
	if d.length_squared() > 1e-6:
		n.rotation.y = atan2(-d.z, d.x)

func _process(dt: float) -> void:
	if village == null:
		return
	var w: Weather = village.weather
	var oc: Ocean = village.ocean
	var eco: Ecosystem = village.ecosystem
	if village.camera_rig:
		rain.global_position = village.camera_rig.target + Vector3(0, 26, 0)
	rain.emitting = w.rain > 0.2
	rain.amount = int(lerpf(300.0, 1400.0, w.rain))
	var t = Time.get_ticks_msec() / 1000.0
	if _sea:
		_sea.set_shader_parameter("wave_height", oc.amplitude())
		_sea.set_shader_parameter("sim_time", oc.time)
		_sea.set_shader_parameter("tide", oc.tide())
		_sea.set_shader_parameter("storm", w.cloud)
	if _sway:
		_sway.set_shader_parameter("wind", 0.25 + w.wind)
	# boats ride the same surface the shader draws, pitch and roll to its slope
	for b in _boat_y:
		if b.visual:
			var bp: Vector3 = b.visual.global_position
			b.visual.position.y = _boat_y[b] + _sea_y(bp)
			var sl: Vector2 = oc.slope(bp.x, bp.z)
			b.visual.rotation.x = clampf(sl.y * 1.6, -0.35, 0.35)
			b.visual.rotation.z = clampf(-sl.x * 1.6, -0.35, 0.35)
			var wk: CPUParticles3D = _wakes[b]
			wk.global_position = Vector3(bp.x, _sea_y(bp) + 0.05, bp.z)
			wk.emitting = b.boat_state in ["outbound", "inbound"]
	_draw_animals(eco, t)
	_fill_audio(w)

func _draw_animals(eco: Ecosystem, t: float) -> void:
	for s in eco.schools:
		var e: Array = _schools[s["id"]]
		var n: Node3D = e[0]
		var sp: Dictionary = Ecosystem.SPECIES[s["sp"]]
		var depth: float = sp["depth"] * (2.2 if s.get("deep", false) else 1.0)
		var p: Vector3 = s["pos"]
		var prev = n.global_position
		n.global_position = Vector3(p.x, _sea_y(p) - depth, p.z)
		_face(n, prev, n.global_position)
		var shown = clampi(int(s["size"] / 5.0), 0, 14)
		var spread = 1.6 if s["state"] == "flee" else 1.0
		for i in 14:
			var f: MeshInstance3D = e[1][i]
			f.visible = i < shown
			var a = t * (0.8 if s["state"] != "flee" else 2.4) + i * 2.399
			f.position = Vector3(sin(a * 0.7 + i) * 1.4 * spread, sin(a * 1.3) * 0.25, cos(a + i * 0.5) * 1.0 * spread)
	for h in eco.hunters:
		var n2: Node3D = _hunters[h["id"]]
		var prev2 = n2.global_position
		n2.global_position = Vector3(h["pos"].x, _sea_y(h["pos"]) - 0.5, h["pos"].z)
		_face(n2, prev2, n2.global_position)
	var pod: Node3D = get_node_or_null("Wildlife/DolphinPod")
	var pp: Vector3 = eco.pod_pos()
	if pod:
		var prevp = pod.global_position
		pod.global_position = Vector3(pp.x, 0, pp.z)
		_face(pod, prevp, pod.global_position)
	for d in eco.dolphins:
		var n3: Node3D = _dolphins[d["id"]]
		var off: Vector3 = d["off"]
		var wp = pp + off
		var y = _sea_y(wp) - 0.22 + 0.06 * sin(t * 2.0 + off.x)
		if d["air"] > 0.0:
			var k: float = 1.0 - d["air"] / 1.3
			y = _sea_y(wp) + sin(k * PI) * 1.6
			n3.rotation.z = lerpf(0.7, -0.7, k)
		else:
			n3.rotation.z = 0.0
		n3.position = Vector3(off.x, y, off.z)
	for tt in eco.turtles:
		var n4: Node3D = _turtles[tt["id"]]
		var prev4 = n4.global_position
		n4.global_position = Vector3(tt["pos"].x, _sea_y(tt["pos"]) + (0.0 if tt["state"] == "surface" else -1.1), tt["pos"].z)
		_face(n4, prev4, n4.global_position)
	for c in eco.crabs:
		var n5: Node3D = _crabs[c["id"]]
		n5.visible = c["state"] != "hidden"
		n5.global_position = c["pos"] + Vector3(0, 0.06, 0)
	for b in eco.birds:
		var n6: Node3D = _birds[b["id"]]
		var prev6 = n6.global_position
		n6.global_position = b["pos"]
		var moving = prev6.distance_to(b["pos"]) > 0.001
		if moving:
			_face(n6, prev6, b["pos"])
		var flying: bool = b["state"] != "roost" and not (b["kind"] == "sandpiper" and b["state"] != "flush")
		var flap = 0.0
		if flying:
			var rate = 5.0 if b["kind"] in ["tern", "gull"] else (2.4 if b["kind"] == "pelican" else 1.4)
			flap = sin(t * rate * TAU * 0.3 + b["phase"] * 3.0) * (0.15 if b["kind"] == "frigatebird" else 0.55)
			if b["state"] == "dive":
				flap = 1.2                                   # wings folded back for the plunge
				n6.rotation.z = -1.1
			else:
				n6.rotation.z = 0.0
		else:
			flap = 1.35                                      # perched: wings folded
			n6.rotation.z = 0.0
		n6.get_node("WingL").rotation.x = PI / 2 - flap
		n6.get_node("WingR").rotation.x = PI / 2 + flap
		n6.get_node("Carry").visible = b["carry"]
	var heap = village.ledger.qty(Economy.SCRAPS, "fish")
	var i = 0
	for f in _scraps.get_children():
		f.visible = i < heap
		i += 1

# ------------------------------------------------------------------ sound
func _audio() -> void:
	## Original, generated ambience (no sampled assets): filtered noise shaped
	## into surf, wind and rain. Volumes follow the weather and the sea state.
	_player = AudioStreamPlayer.new()
	var gen = AudioStreamGenerator.new()
	gen.mix_rate = 22050.0
	gen.buffer_length = 0.2
	_player.stream = gen
	_player.volume_db = -14.0
	add_child(_player)
	_player.play()
	_play = _player.get_stream_playback()

func _fill_audio(w: Weather) -> void:
	if _play == null:
		return
	var n = _play.get_frames_available()
	var surf_amp = 0.25 + 0.5 * village.ocean.roughness()
	for i in n:
		var white = randf() * 2.0 - 1.0
		_lp[0] += (white - _lp[0]) * 0.02
		_lp[1] += (white - _lp[1]) * 0.18
		_at += 1.0 / 22050.0
		var swell = 0.55 + 0.45 * sin(_at * 0.9) * sin(_at * 0.31 + 1.0)
		var s = _lp[0] * 4.0 * surf_amp * swell + _lp[1] * (0.05 + 0.5 * w.wind) + white * 0.22 * w.rain
		_play.push_frame(Vector2(s, s))
