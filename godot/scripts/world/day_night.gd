extends Node3D
## Sun, sky and ambient light driven by GameClock (ART_BIBLE §6 lighting table).

var sun: DirectionalLight3D
var env: Environment
var sky_mat: ProceduralSkyMaterial
var village = null
var moon: DirectionalLight3D
var light_level: float = 1.0          # read by the sea shader so water darkens with the scene
var moon_disc: MeshInstance3D
var stars: MultiMeshInstance3D
const MOON_DAYS := 29.5

const KEYS := [   # hour, sun colour, sun energy, sky top, sky horizon, ambient energy
	[0.0, Color(0.45, 0.55, 0.95), 0.03, Color(0.02, 0.03, 0.09), Color(0.05, 0.07, 0.16), 0.12],
	[5.0, Color(0.45, 0.55, 0.95), 0.03, Color(0.03, 0.04, 0.12), Color(0.10, 0.10, 0.20), 0.14],
	[6.5, Color(1.0, 0.72, 0.5), 0.9, Color(0.30, 0.45, 0.75), Color(0.98, 0.72, 0.55), 0.6],
	[9.0, Color(1.0, 0.95, 0.86), 1.0, Color(0.25, 0.50, 0.88), Color(0.72, 0.86, 0.96), 0.6],
	[13.0, Color(1.0, 0.97, 0.9), 1.1, Color(0.22, 0.48, 0.90), Color(0.70, 0.86, 0.98), 0.65],
	[17.0, Color(1.0, 0.9, 0.75), 0.95, Color(0.26, 0.46, 0.82), Color(0.86, 0.82, 0.80), 0.6],
	[19.0, Color(1.0, 0.55, 0.28), 0.8, Color(0.28, 0.22, 0.48), Color(1.0, 0.55, 0.35), 0.55],
	[20.5, Color(0.5, 0.55, 0.95), 0.05, Color(0.05, 0.05, 0.16), Color(0.22, 0.14, 0.28), 0.16],
	[24.0, Color(0.45, 0.55, 0.95), 0.03, Color(0.02, 0.03, 0.09), Color(0.05, 0.07, 0.16), 0.12],
]

func _ready() -> void:
	sun = DirectionalLight3D.new()
	sun.name = "Sun"
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 220.0
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_4_SPLITS
	add_child(sun)
	sky_mat = ProceduralSkyMaterial.new()
	var sky := Sky.new()
	sky.sky_material = sky_mat
	env = Environment.new()
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.ssao_enabled = true
	env.ssao_radius = 1.6
	env.ssao_intensity = 2.2
	env.glow_enabled = true
	env.glow_intensity = 0.5
	env.glow_hdr_threshold = 1.3
	env.fog_enabled = true
	env.fog_density = 0.00035
	env.fog_aerial_perspective = 0.3
	var we := WorldEnvironment.new()
	we.name = "WorldEnvironment"
	we.environment = env
	add_child(we)
	moon = DirectionalLight3D.new()
	moon.name = "Moon"
	moon.light_color = Color(0.62, 0.72, 1.0)
	moon.shadow_enabled = true
	moon.sky_mode = DirectionalLight3D.SKY_MODE_LIGHT_ONLY
	add_child(moon)
	moon_disc = MeshInstance3D.new()
	moon_disc.name = "MoonDisc"
	var q := QuadMesh.new()
	q.size = Vector2(46, 46)
	moon_disc.mesh = q
	var mm := ShaderMaterial.new()
	mm.shader = load("res://shaders/moon.gdshader")
	moon_disc.material_override = mm
	moon_disc.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(moon_disc)
	stars = MultiMeshInstance3D.new()
	stars.name = "Stars"
	var multi := MultiMesh.new()
	multi.transform_format = MultiMesh.TRANSFORM_3D
	multi.use_colors = true
	multi.instance_count = 700
	var sq := QuadMesh.new()
	sq.size = Vector2(2.2, 2.2)
	multi.mesh = sq
	var rng := RandomNumberGenerator.new()
	rng.seed = 99
	for i in multi.instance_count:
		var az := rng.randf() * TAU
		var el := asin(rng.randf_range(0.05, 1.0))
		var d := Vector3(cos(el) * cos(az), sin(el), cos(el) * sin(az)) * 780.0
		var tr := Transform3D(Basis.looking_at(-d, Vector3.UP), d).scaled_local(Vector3.ONE * rng.randf_range(0.5, 1.6))
		multi.set_instance_transform(i, tr)
		multi.set_instance_color(i, Color(rng.randf_range(0.35, 1.0), 0, 0))
	stars.multimesh = multi
	var sm := ShaderMaterial.new()
	sm.shader = load("res://shaders/stars.gdshader")
	stars.material_override = sm
	stars.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(stars)
	apply(GameClock.hour())

func moon_phase() -> float:
	## 0 new .. 0.5 full .. 1 new, from the calendar.
	return fposmod(GameClock.total_minutes / 1440.0 / MOON_DAYS + 0.42, 1.0)

func moon_illumination() -> float:
	return 0.5 * (1.0 - cos(moon_phase() * TAU))

func phase_name() -> String:
	var p := moon_phase()
	if p < 0.04 or p > 0.96: return "new moon"
	if p < 0.21: return "waxing crescent"
	if p < 0.29: return "first quarter"
	if p < 0.46: return "waxing gibbous"
	if p < 0.54: return "full moon"
	if p < 0.71: return "waning gibbous"
	if p < 0.79: return "last quarter"
	return "waning crescent"

func _process(_dt: float) -> void:
	apply(GameClock.hour())

func apply(h: float) -> void:
	var a = KEYS[0]
	var b = KEYS[KEYS.size() - 1]
	for i in range(KEYS.size() - 1):
		if h >= KEYS[i][0] and h <= KEYS[i + 1][0]:
			a = KEYS[i]
			b = KEYS[i + 1]
			break
	var k: float = clampf((h - a[0]) / maxf(b[0] - a[0], 0.001), 0.0, 1.0)
	sun.light_color = a[1].lerp(b[1], k)
	sun.light_energy = lerpf(a[2], b[2], k)
	sky_mat.sky_top_color = a[3].lerp(b[3], k)
	sky_mat.sky_horizon_color = a[4].lerp(b[4], k)
	sky_mat.ground_horizon_color = a[4].lerp(b[4], k)
	sky_mat.ground_bottom_color = a[3].lerp(b[3], k).darkened(0.3)
	env.ambient_light_energy = lerpf(a[5], b[5], k)
	env.fog_light_color = a[4].lerp(b[4], k)
	if village:
		# weather on screen: cloud dims and greys the light, rain thickens the air
		var w: Weather = village.weather
		var grey := Color(0.55, 0.58, 0.62) * (0.25 + 0.75 * clampf(sun.light_energy, 0.0, 1.0))
		sun.light_energy *= 1.0 - 0.65 * w.cloud
		sky_mat.sky_top_color = sky_mat.sky_top_color.lerp(grey.darkened(0.25), w.cloud * 0.85)
		sky_mat.sky_horizon_color = sky_mat.sky_horizon_color.lerp(grey, w.cloud * 0.85)
		sky_mat.ground_horizon_color = sky_mat.sky_horizon_color
		env.fog_density = 0.00035 + 0.006 * w.rain
		env.fog_light_color = env.fog_light_color.lerp(grey, w.cloud)
	# sun path: rises in the east (+x), high in the south (+z) so the village,
	# which faces the south-east camera, is front-lit for most of the day
	var day := h > 5.5 and h < 19.5
	var t := (h - 5.5) / 14.0 if day else fposmod(h - 19.5, 24.0) / 10.0
	var elev := sin(t * PI) * deg_to_rad(62.0) + deg_to_rad(8.0)
	var azim := lerpf(deg_to_rad(-80.0), deg_to_rad(80.0), t)
	var dir := Vector3(-sin(azim) * cos(elev), sin(elev), cos(azim) * cos(elev))     # toward the light
	sun.look_at_from_position(dir * 100.0, Vector3.ZERO, Vector3.UP)
	if moon == null:
		return
	# the moon runs ~phase x 24 h behind the sun: full moon rises at sunset
	var mh := fposmod(h - moon_phase() * 24.0, 24.0)
	var mt := (mh - 5.5) / 14.0
	var m_up := mt > 0.0 and mt < 1.0
	var m_el := sin(clampf(mt, 0.0, 1.0) * PI) * deg_to_rad(58.0) + deg_to_rad(6.0)
	var m_az := lerpf(deg_to_rad(-80.0), deg_to_rad(80.0), clampf(mt, 0.0, 1.0))
	var mdir := Vector3(-sin(m_az) * cos(m_el), sin(m_el), cos(m_az) * cos(m_el))
	moon.look_at_from_position(mdir * 100.0, Vector3.ZERO, Vector3.UP)
	var night_k := clampf(1.0 - sun.light_energy / 0.35, 0.0, 1.0)
	var cloud: float = village.weather.cloud if village else 0.0
	moon.light_energy = (0.11 * moon_illumination() * night_k * (1.0 - 0.8 * cloud)) if m_up else 0.0
	moon.visible = moon.light_energy > 0.01
	var cam: Camera3D = get_viewport().get_camera_3d() if is_inside_tree() else null
	var c: Vector3 = cam.global_position if cam != null else Vector3.ZERO
	moon_disc.visible = m_up and moon_illumination() > 0.03
	moon_disc.global_position = c + mdir * 640.0
	moon_disc.look_at(c, Vector3.UP)
	var mmat: ShaderMaterial = moon_disc.material_override
	mmat.set_shader_parameter("phase", moon_phase())
	mmat.set_shader_parameter("brightness", lerpf(0.55, 1.6, night_k) * (1.0 - 0.7 * cloud))
	stars.global_position = c
	(stars.material_override as ShaderMaterial).set_shader_parameter("visibility", night_k * (1.0 - cloud) * 1.4)
	light_level = clampf(sun.light_energy / 1.0 + moon.light_energy * 2.0, 0.12, 1.0)
	env.ambient_light_energy += 0.12 * moon.light_energy
