extends Node3D
## Presentation-only life: weather on screen, the sea state, boats riding the
## swell, a few gulls, foliage in the wind, and generated ambience.
## Nothing here changes the simulation.

const SWAY = preload("res://shaders/foliage_sway.gdshader")

var village = null
var rain: CPUParticles3D
var gulls: Array = []
var _t = 0.0
var _sea: ShaderMaterial = null
var _sway: ShaderMaterial = null
var _player: AudioStreamPlayer = null
var _play: AudioStreamGeneratorPlayback = null
var _lp = [0.0, 0.0, 0.0]
var _boat_y = {}

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
	for i in 7:
		gulls.append(_gull(i))
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
	_audio()

func _gull(i: int) -> Node3D:
	var g = Node3D.new()
	g.name = "Gull%d" % i
	var mat = StandardMaterial3D.new()
	mat.albedo_color = Color(0.96, 0.96, 0.94)
	mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	for sgn in [-1.0, 1.0]:
		var w = MeshInstance3D.new()
		var pm = PrismMesh.new()
		pm.size = Vector3(0.75, 0.3, 0.02)
		w.mesh = pm
		w.material_override = mat
		w.rotation = Vector3(deg_to_rad(90), 0, deg_to_rad(90) * sgn)
		w.position = Vector3(0.36 * sgn, 0, 0)
		w.name = "WingL" if sgn < 0 else "WingR"
		g.add_child(w)
	g.set_meta("phase", i * 0.9)
	g.set_meta("radius", 9.0 + i * 3.2)
	g.set_meta("height", 12.0 + (i % 3) * 3.5)
	g.set_meta("centre", Vector3(8, 0, 12) if i % 2 == 0 else Vector3(28, 0, 6))
	add_child(g)
	return g

func _audio() -> void:
	## Original, generated ambience (no sampled assets): filtered noise shaped
	## into surf, wind and rain. Volumes follow the weather.
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
	var surf_amp = 0.25 + 0.5 * w.wind
	for i in n:
		var white = randf() * 2.0 - 1.0
		_lp[0] += (white - _lp[0]) * 0.02                       # low rumble: surf
		_lp[1] += (white - _lp[1]) * 0.18                       # mid hiss: wind
		_t += 1.0 / 22050.0
		var swell = 0.55 + 0.45 * sin(_t * 0.9) * sin(_t * 0.31 + 1.0)
		var s = _lp[0] * 4.0 * surf_amp * swell + _lp[1] * (0.05 + 0.5 * w.wind) + white * 0.22 * w.rain
		_play.push_frame(Vector2(s, s))

func _process(dt: float) -> void:
	if village == null:
		return
	var w: Weather = village.weather
	var cam: Camera3D = village.camera_rig.cam if village.camera_rig else null
	if cam:
		rain.global_position = village.camera_rig.target + Vector3(0, 26, 0)
	rain.emitting = w.rain > 0.25
	rain.amount = int(lerpf(300.0, 1400.0, w.rain))
	var t = Time.get_ticks_msec() / 1000.0
	if _sea:
		_sea.set_shader_parameter("wave_height", 0.10 + 0.42 * w.wind)
		_sea.set_shader_parameter("storm", w.cloud)
	if _sway:
		_sway.set_shader_parameter("wind", 0.25 + w.wind)
	for b in _boat_y:
		if b.visual:
			var ph: float = b.home_pos.x * 0.7
			b.visual.position.y = _boat_y[b] + sin(t * 1.3 + ph) * (0.03 + 0.14 * w.wind)
			b.visual.rotation.x = sin(t * 1.1 + ph) * (0.02 + 0.08 * w.wind)
			b.visual.rotation.z = cos(t * 0.9 + ph) * (0.015 + 0.06 * w.wind)
	var fly = w.state != "storm"
	for g in gulls:
		g.visible = fly
		var ph2: float = g.get_meta("phase")
		var r: float = g.get_meta("radius")
		var c: Vector3 = g.get_meta("centre")
		var a = t * (0.22 + 0.02 * ph2) + ph2
		var p = c + Vector3(cos(a) * r, g.get_meta("height") + sin(t * 0.6 + ph2) * 1.5, sin(a) * r * 0.8)
		g.global_position = p
		g.rotation.y = -a - PI / 2
		var flap = sin(t * 7.0 + ph2) * 0.5
		g.get_node("WingL").rotation.y = flap
		g.get_node("WingR").rotation.y = -flap
	_fill_audio(w)
