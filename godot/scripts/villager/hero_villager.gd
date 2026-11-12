class_name HeroVillager
extends Node3D
## A hero villager exported by blender/build_characters.py: one GLB with the
## shared 53-bone rig, facial blend shapes and every animation clip.
##
## It honours the same contract as VillagerAnimator (play(clip) with the clip
## names in VillagerAnimator.CLIPS), plus `run` and one job clip per character,
## and adds life the clips cannot carry: random blinks and expressions.

const LOOPING := ["idle", "walk", "climb_stairs", "climb_ladder", "cook", "eat", "sit", "sleep", "fish", "work", "wave", "run",
	"haul_rope", "hand_fruit", "mend_net", "run_play"]
const JOB := {"A": "haul_rope", "B": "hand_fruit", "C": "mend_net", "D": "run_play"}
const TITLES := {"A": "Fisher captain", "B": "Market vendor", "C": "Elder net-mender", "D": "Harbour child"}

var key: String = ""
var model: Node3D
var player: AnimationPlayer
var current: String = ""
var face_meshes: Array = []          # MeshInstance3D with the facial blend shapes (body, brows, beard ...)
var _blink_in: float = 2.0
var _blink_t: float = -1.0
var _rng := RandomNumberGenerator.new()

static func path_for(k: String) -> String:
	return "res://assets/characters/%s.glb" % k

static func available(k: String) -> bool:
	return ResourceLoader.exists(path_for(k))

func setup(k: String) -> bool:
	key = k
	name = "Hero_" + k
	_rng.seed = hash(k)
	if not available(k):
		return false
	model = load(path_for(k)).instantiate()
	# Blender characters face -Y, which glTF imports as +Z; the game's figures face -Z.
	model.rotation.y = PI
	add_child(model)
	player = model.find_child("AnimationPlayer", true, false)
	if player:
		for n in player.get_animation_list():
			var a: Animation = player.get_animation(n)
			a.loop_mode = Animation.LOOP_LINEAR if LOOPING.has(String(n)) else Animation.LOOP_NONE
	for mi in model.find_children("*", "MeshInstance3D", true, false):
		var m: MeshInstance3D = mi
		if m.mesh and m.find_blend_shape_by_name("blink") >= 0:
			face_meshes.append(m)
	play("idle")
	return true

func clips() -> Array:
	return Array(player.get_animation_list()) if player else []

func has_clip(c: String) -> bool:
	return player != null and player.has_animation(c)

func play(clip: String, blend: float = 0.25) -> void:
	if clip == current or not has_clip(clip):
		return
	current = clip
	player.play(clip, blend)

func set_shape(shape: String, v: float) -> void:
	for m in face_meshes:
		var i: int = m.find_blend_shape_by_name(shape)
		if i >= 0:
			m.set_blend_shape_value(i, v)

func _process(dt: float) -> void:
	# blink every 2-6 s, 0.16 s long; sleeping keeps the eyes closed
	if current == "sleep":
		set_shape("blink", 1.0)
		return
	if _blink_t >= 0.0:
		_blink_t += dt
		var u: float = _blink_t / 0.16
		set_shape("blink", sin(clampf(u, 0.0, 1.0) * PI))
		if u >= 1.0:
			_blink_t = -1.0
			set_shape("blink", 0.0)
	else:
		_blink_in -= dt
		if _blink_in <= 0.0:
			_blink_t = 0.0
			_blink_in = _rng.randf_range(2.0, 6.0)
	# a friendly face while waving or handing something over
	var smile := 1.0 if current in ["wave", "hand_fruit", "run_play"] else 0.0
	for m in face_meshes:
		var i: int = m.find_blend_shape_by_name("smile")
		if i >= 0:
			m.set_blend_shape_value(i, lerpf(m.get_blend_shape_value(i), smile, clampf(dt * 4.0, 0.0, 1.0)))
