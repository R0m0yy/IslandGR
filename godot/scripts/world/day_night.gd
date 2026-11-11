extends Node3D
## Sun, sky and ambient light driven by GameClock (ART_BIBLE §6 lighting table).

var sun: DirectionalLight3D
var env: Environment
var sky_mat: ProceduralSkyMaterial
var village = null

const KEYS := [   # hour, sun colour, sun energy, sky top, sky horizon, ambient energy
	[0.0, Color(0.45, 0.55, 0.95), 0.10, Color(0.02, 0.03, 0.09), Color(0.05, 0.07, 0.16), 0.12],
	[5.0, Color(0.45, 0.55, 0.95), 0.10, Color(0.03, 0.04, 0.12), Color(0.10, 0.10, 0.20), 0.14],
	[6.5, Color(1.0, 0.72, 0.5), 0.9, Color(0.30, 0.45, 0.75), Color(0.98, 0.72, 0.55), 0.6],
	[9.0, Color(1.0, 0.95, 0.86), 1.0, Color(0.25, 0.50, 0.88), Color(0.72, 0.86, 0.96), 0.6],
	[13.0, Color(1.0, 0.97, 0.9), 1.1, Color(0.22, 0.48, 0.90), Color(0.70, 0.86, 0.98), 0.65],
	[17.0, Color(1.0, 0.9, 0.75), 0.95, Color(0.26, 0.46, 0.82), Color(0.86, 0.82, 0.80), 0.6],
	[19.0, Color(1.0, 0.55, 0.28), 0.8, Color(0.28, 0.22, 0.48), Color(1.0, 0.55, 0.35), 0.55],
	[20.5, Color(0.5, 0.55, 0.95), 0.12, Color(0.05, 0.05, 0.16), Color(0.22, 0.14, 0.28), 0.16],
	[24.0, Color(0.45, 0.55, 0.95), 0.10, Color(0.02, 0.03, 0.09), Color(0.05, 0.07, 0.16), 0.12],
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
	apply(GameClock.hour())

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
