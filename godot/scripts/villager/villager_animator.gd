class_name VillagerAnimator
extends Node3D
## TEMPORARY CHARACTER. Final character art is undecided, so this builds a
## placeholder figure from primitives and - more importantly - defines the
## reusable animation contract:
##
##   idle walk climb_stairs climb_ladder open_door cook eat sit sleep fish work
##
## An AnimationPlayer holds one clip per name and an AnimationTree runs an
## AnimationNodeStateMachine over them. A real character replaces the rig and
## the clips; nothing else in the game refers to bones or meshes.

const CLIPS := ["idle", "walk", "climb_stairs", "climb_ladder", "open_door", "cook", "eat", "sit", "sleep", "fish", "work", "wave"]
## clips the character models add (blender/livingtides/characters/anim.py)
const EXTRA := ["run", "give", "carry", "row", "steer", "swim", "cast", "haul_net", "sweep", "talk", "play"]
const LOOPING := ["idle", "walk", "climb_stairs", "climb_ladder", "cook", "eat", "sit", "sleep", "fish", "work", "wave",
	"run", "give", "carry", "row", "steer", "swim", "cast", "haul_net", "sweep", "talk", "play"]
## character variants (godot/assets/characters/V*.glb) by age group and look
const POOLS := {
	"child": ["V13", "V14"],
	"elder_m": ["V09", "V10"], "elder_f": ["V11", "V12"],
	"m": ["V01", "V02", "V03", "V04"], "f": ["V05", "V06", "V07", "V08"],
	"fisher_m": ["V01", "V01", "V04"], "fisher_f": ["V07"],
	"trade_m": ["V04", "V02"], "trade_f": ["V05", "V06"],
	"cook_f": ["V08", "V05"], "cook_m": ["V02"],
}
const SHADER := preload("res://shaders/hero_character.gdshader")
static var _sm_cache := {}          # clip list -> shared AnimationNodeStateMachine

var model: Node3D = null
var skel: Skeleton3D = null
var variant: String = ""
var props := {}                     # name -> Node3D under a BoneAttachment3D
var face_meshes: Array = []
var _blink_in: float = 2.0
var _blink_t: float = -1.0
var _brng := RandomNumberGenerator.new()
var _prop_timer := {}               # name -> seconds left (handover props)
var lane: float = 0.0               # personal sideways offset while walking (people do not share one line)
var _ground_dy: float = 0.0
var _ray_tick: int = 0
var _yaw: float = 0.0
var _yaw_init := false
const WALKING := ["walk", "climb_stairs", "run", "carry", "cross_bridge"]

var player: AnimationPlayer
var tree: AnimationTree
var playback: AnimationNodeStateMachinePlayback
var current: String = ""
var rig: Node3D

func build(_tint: Color = Color.WHITE) -> void:
	## NEUTRAL TEMPORARY FIGURE. Character design is frozen until the owner
	## approves a direction: one plain mannequin for everyone, no faces, hair,
	## outfits or individual colours. It exists only so that movement and
	## interactions can be seen and tested.
	rig = Node3D.new()
	rig.name = "Rig"
	add_child(rig)
	var grey := Color(0.78, 0.76, 0.72)
	_part("Body", CapsuleMesh.new(), Vector3(0, 1.0, 0), grey, {"radius": 0.17, "height": 0.86})
	_part("Head", SphereMesh.new(), Vector3(0, 1.58, 0), grey, {"radius": 0.115, "height": 0.23})
	_limb("ArmL", Vector3(-0.24, 1.32, 0), Vector3(0.08, 0.56, 0.08), grey.darkened(0.08))
	_limb("ArmR", Vector3(0.24, 1.32, 0), Vector3(0.08, 0.56, 0.08), grey.darkened(0.08))
	_limb("LegL", Vector3(-0.09, 0.64, 0), Vector3(0.1, 0.64, 0.1), grey.darkened(0.16))
	_limb("LegR", Vector3(0.09, 0.64, 0), Vector3(0.1, 0.64, 0.1), grey.darkened(0.16))
	# fishing rod, shown only by the `fish` clip
	var rod := MeshInstance3D.new()
	rod.name = "Rod"
	var cm := CylinderMesh.new()
	cm.top_radius = 0.008
	cm.bottom_radius = 0.016
	cm.height = 2.2
	rod.mesh = cm
	rod.position = Vector3(0.2, 1.45, -0.9)
	rod.rotation = Vector3(deg_to_rad(-62), 0, 0)
	rod.visible = false
	rod.material_override = _mat(Color(0.45, 0.32, 0.2))
	rig.add_child(rod)
	player = AnimationPlayer.new()
	player.name = "AnimationPlayer"
	add_child(player)
	var lib := AnimationLibrary.new()
	for clip in CLIPS:
		lib.add_animation(clip, _clip(clip))
	player.add_animation_library("", lib)
	tree = AnimationTree.new()
	tree.name = "AnimationTree"
	var sm := AnimationNodeStateMachine.new()
	var i := 0
	for clip in CLIPS:
		var an := AnimationNodeAnimation.new()
		an.animation = clip
		sm.add_node(clip, an, Vector2(160 * (i % 4), 90 * (i / 4)))
		i += 1
	for a in CLIPS:
		for b in CLIPS:
			if a != b:
				var tr := AnimationNodeStateMachineTransition.new()
				tr.xfade_time = 0.18
				sm.add_transition(a, b, tr)
	tree.tree_root = sm
	add_child(tree)
	tree.anim_player = tree.get_path_to(player)
	tree.active = true
	playback = tree.get("parameters/playback")
	play("idle")

static func pick_variant(villager_id: String, age: float, role: String) -> String:
	var h: int = absi(hash(villager_id))
	var look: String = "f" if h % 2 == 1 else "m"
	var pool_key: String = look
	if age < 13.0:
		pool_key = "child"
	elif age >= 62.0:
		pool_key = "elder_" + look
	elif role == "fisher":
		pool_key = "fisher_" + look
	elif role in ["fishmonger", "market_clerk", "shopkeeper", "shop_hand", "storekeeper"]:
		pool_key = "trade_" + look
	elif role in ["cook", "server"]:
		pool_key = "cook_" + look
	var pool: Array = POOLS.get(pool_key, POOLS[look])
	var key: String = pool[(h / 7) % pool.size()]
	return key if ResourceLoader.exists("res://assets/characters/%s.glb" % key) else ""

func build_for(villager) -> void:
	## A real character for this resident when the variant models exist, otherwise the mannequin.
	var role: String = villager.job["role"] if villager.job != null else ""
	var key := pick_variant(villager.villager_id, villager.age, role)
	if key == "":
		build()
		return
	build_model(key, villager.villager_id)

func build_model(key: String, seed_id: String) -> void:
	variant = key
	_brng.seed = hash(seed_id)
	lane = (float(absi(hash(seed_id)) % 5) - 2.0) * 0.13
	rig = Node3D.new()
	rig.name = "Rig"
	add_child(rig)
	model = load("res://assets/characters/%s.glb" % key).instantiate()
	model.rotation.y = PI            # Blender -Y forward imports as +Z; the figures face -Z
	rig.add_child(model)
	player = model.find_child("AnimationPlayer", true, false)
	for n in player.get_animation_list():
		var a: Animation = player.get_animation(n)
		a.loop_mode = Animation.LOOP_LINEAR if LOOPING.has(String(n)) else Animation.LOOP_NONE
	for sk in model.find_children("*", "Skeleton3D", true, false):
		skel = sk
	# per-resident colours: clothing hue / value and skin tone ride on the vertex alpha tag
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(seed_id + "_look")
	var hue := rng.randf_range(-0.5, 0.5) if rng.randf() < 0.8 else 0.0
	var val := rng.randf_range(0.82, 1.12)
	var tone := rng.randf_range(0.82, 1.18)
	var mats := {}
	for mi in model.find_children("*", "MeshInstance3D", true, false):
		var m: MeshInstance3D = mi
		if m.mesh == null:
			continue
		if m.find_blend_shape_by_name("blink") >= 0:
			face_meshes.append(m)
		var part := String(m.name).substr(String(m.name).find("_") + 1)
		var mode := 0
		if part == "body":
			mode = 1
		else:
			for pre in ["top", "bottom", "apron", "vest", "collar", "sleeve_roll", "skirt", "hat", "headwrap", "shirt", "trousers", "shorts"]:
				if part.begins_with(pre) and not part.ends_with("_band"):
					mode = 2
					break
		for si in m.mesh.get_surface_count():
			var src = m.mesh.surface_get_material(si)
			var key2 := [src, mode]
			if not mats.has(key2):
				var d := ShaderMaterial.new()
				d.shader = SHADER
				if src is StandardMaterial3D:
					d.set_shader_parameter("roughness_v", src.roughness)
					d.set_shader_parameter("metallic_v", src.metallic)
				d.set_shader_parameter("cloth_hue", hue)
				d.set_shader_parameter("cloth_val", val)
				d.set_shader_parameter("skin_tone", tone)
				d.set_shader_parameter("tag_mode", mode)
				mats[key2] = d
			m.set_surface_override_material(si, mats[key2])
	_make_props()
	# state machine over every clip the model has (one shared resource per clip list)
	var names: Array = []
	for c in CLIPS + EXTRA:
		if player.has_animation(c):
			names.append(c)
	var ck := ",".join(names)
	if not _sm_cache.has(ck):
		var sm := AnimationNodeStateMachine.new()
		var i := 0
		for c in names:
			var an := AnimationNodeAnimation.new()
			an.animation = c
			sm.add_node(c, an, Vector2(160 * (i % 6), 90 * (i / 6)))
			i += 1
		for a in names:
			for b in names:
				if a != b:
					var tr := AnimationNodeStateMachineTransition.new()
					tr.xfade_time = 0.22
					sm.add_transition(a, b, tr)
		_sm_cache[ck] = sm
	tree = AnimationTree.new()
	tree.name = "AnimationTree"
	tree.tree_root = _sm_cache[ck]
	model.add_child(tree)              # so its root node (..) is the model, like the imported player
	tree.anim_player = tree.get_path_to(player)
	tree.active = true
	playback = tree.get("parameters/playback")
	play("idle")

# ------------------------------------------------------------------ props in hands
func _attach(name_: String, bone: String, node: Node3D) -> void:
	if skel == null or skel.find_bone(bone) < 0:
		return
	var ba := BoneAttachment3D.new()
	ba.bone_name = bone
	skel.add_child(ba)
	ba.add_child(node)
	node.visible = false
	props[name_] = node

func _mesh(m: Mesh, c: Color, pos: Vector3, rot: Vector3 = Vector3.ZERO) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.mesh = m
	mi.position = pos
	mi.rotation = rot
	var mat := StandardMaterial3D.new()
	mat.albedo_color = c
	mat.roughness = 0.7
	mi.material_override = mat
	return mi

func _make_props() -> void:
	# bone space: Y runs along the bone (towards the fingers)
	var rod := Node3D.new()
	var cm := CylinderMesh.new(); cm.top_radius = 0.006; cm.bottom_radius = 0.014; cm.height = 2.2
	rod.add_child(_mesh(cm, Color(0.42, 0.3, 0.18), Vector3(0, 0.05, 0.9), Vector3(PI / 2 - 0.3, 0, 0)))
	_attach("rod", "hand_r", rod)
	var fish := Node3D.new()
	var fm := CapsuleMesh.new(); fm.radius = 0.035; fm.height = 0.3
	fish.add_child(_mesh(fm, Color(0.55, 0.62, 0.68), Vector3(0, 0.16, 0.0)))
	_attach("fish", "hand_r", fish)
	var fruit := Node3D.new()
	var sm := SphereMesh.new(); sm.radius = 0.045; sm.height = 0.08
	fruit.add_child(_mesh(sm, Color(0.95, 0.55, 0.12), Vector3(0, 0.1, -0.03)))
	_attach("fruit", "hand_r", fruit)
	var bread := Node3D.new()
	var bm := CapsuleMesh.new(); bm.radius = 0.04; bm.height = 0.2
	bread.add_child(_mesh(bm, Color(0.85, 0.62, 0.32), Vector3(0, 0.1, 0), Vector3(0, 0, PI / 2)))
	_attach("bread", "hand_r", bread)
	var crate := Node3D.new()
	var bx := BoxMesh.new(); bx.size = Vector3(0.42, 0.24, 0.3)
	crate.add_child(_mesh(bx, Color(0.62, 0.45, 0.28), Vector3(-0.2, 0.12, -0.12)))
	_attach("crate", "hand_r", crate)
	var broom := Node3D.new()
	var brm := CylinderMesh.new(); brm.top_radius = 0.012; brm.bottom_radius = 0.012; brm.height = 1.3
	broom.add_child(_mesh(brm, Color(0.55, 0.4, 0.25), Vector3(0, 0.05, 0.25), Vector3(PI / 2 + 0.5, 0, 0)))
	_attach("broom", "hand_r", broom)

func show_prop(name_: String, on: bool, seconds: float = -1.0) -> void:
	if props.has(name_):
		props[name_].visible = on
		if on and seconds > 0.0:
			_prop_timer[name_] = seconds
		elif not on:
			_prop_timer.erase(name_)

func phase() -> float:
	## 0..1 position in the current clip (boats sync their oars to the rower).
	if player == null or player.current_animation == "":
		return 0.0
	var a: Animation = player.get_animation(player.current_animation)
	return fposmod(player.current_animation_position / maxf(0.01, a.length), 1.0)

func _physics_process(_dt: float) -> void:
	## Feet on the real surface: the walk graph is straight lines between nodes, the
	## stairs, decks and rock are not. Only the figure moves; the simulation keeps its position.
	if model == null or not visible or not is_inside_tree():
		return
	_ray_tick = (_ray_tick + 1) % 3
	if _ray_tick != 0:
		return
	var target := 0.0
	if current in WALKING:
		var p := global_position
		var q := PhysicsRayQueryParameters3D.create(p + Vector3(0, 0.7, 0), p + Vector3(0, -0.9, 0))
		var hit := get_world_3d().direct_space_state.intersect_ray(q)
		if not hit.is_empty():
			target = clampf(hit["position"].y - p.y, -0.45, 0.45)
	_ground_dy = target

func _process(dt: float) -> void:
	if model == null:
		return
	# smooth the figure toward the simulation pose: ground height, walking lane, turning
	var walking := current in WALKING
	rig.position.y = lerpf(rig.position.y, _ground_dy, clampf(dt * 10.0, 0.0, 1.0))
	rig.position.x = lerpf(rig.position.x, lane if walking else 0.0, clampf(dt * 3.0, 0.0, 1.0))
	var parent_yaw: float = get_parent().rotation.y if get_parent() is Node3D else 0.0
	if not _yaw_init:
		_yaw = parent_yaw; _yaw_init = true
	_yaw = lerp_angle(_yaw, parent_yaw, clampf(dt * 8.0, 0.0, 1.0))
	rig.rotation.y = angle_difference(parent_yaw, _yaw)
	for k in _prop_timer.keys():
		_prop_timer[k] -= dt
		if _prop_timer[k] <= 0.0:
			show_prop(k, false)
	if not visible:
		return
	if current == "sleep":
		_set_shape("blink", 1.0)
		return
	if _blink_t >= 0.0:
		_blink_t += dt
		var u: float = _blink_t / 0.16
		_set_shape("blink", sin(clampf(u, 0.0, 1.0) * PI))
		if u >= 1.0:
			_blink_t = -1.0
			_set_shape("blink", 0.0)
	else:
		_blink_in -= dt
		if _blink_in <= 0.0:
			_blink_t = 0.0
			_blink_in = _brng.randf_range(2.0, 6.0)

func _set_shape(shape: String, v: float) -> void:
	for m in face_meshes:
		var i: int = m.find_blend_shape_by_name(shape)
		if i >= 0:
			m.set_blend_shape_value(i, v)

func play(clip: String) -> void:
	if model != null:
		if clip == current:
			return
		var c: String = clip if player.has_animation(clip) else ({"cross_bridge": "walk", "shop": "idle", "drink": "eat", "wash": "cook",
			"mend_nets": "work", "shoo": "wave"}.get(clip, "idle"))
		current = clip
		show_prop("rod", c in ["fish", "cast"])
		show_prop("broom", c == "sweep")
		if playback:
			if playback.get_current_node() == &"":
				playback.start(c)
			else:
				playback.travel(c)
		return
	if clip == current or not CLIPS.has(clip):
		return
	current = clip
	if playback:
		if playback.get_current_node() == &"":
			playback.start(clip)
		else:
			playback.travel(clip)

func _mat(c: Color) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = c
	m.roughness = 0.9
	return m

func _part(n: String, mesh: PrimitiveMesh, pos: Vector3, c: Color, props: Dictionary) -> void:
	for k in props:
		mesh.set(k, props[k])
	var mi := MeshInstance3D.new()
	mi.name = n
	mi.mesh = mesh
	mi.position = pos
	mi.material_override = _mat(c)
	rig.add_child(mi)

func _limb(n: String, pivot: Vector3, size: Vector3, c: Color) -> void:
	var p := Node3D.new()
	p.name = n
	p.position = pivot
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = size
	mi.mesh = bm
	mi.position = Vector3(0, -size.y / 2, 0)
	mi.material_override = _mat(c)
	p.add_child(mi)
	rig.add_child(p)

# ---- clip authoring: {track path: [[time, value], ...]}
func _clip(n: String) -> Animation:
	var a := Animation.new()
	a.loop_mode = Animation.LOOP_LINEAR
	var L := 1.0
	var T := {}
	var rest := {"Rig:position": Vector3.ZERO, "Rig:rotation": Vector3.ZERO, "Rig/ArmL:rotation": Vector3.ZERO,
		"Rig/ArmR:rotation": Vector3.ZERO, "Rig/LegL:rotation": Vector3.ZERO, "Rig/LegR:rotation": Vector3.ZERO, "Rig/Rod:visible": false}
	match n:
		"idle":
			L = 3.0
			T = {"Rig/ArmL:rotation": [[0, Vector3(0.04, 0, 0.05)], [1.5, Vector3(-0.04, 0, 0.08)], [3, Vector3(0.04, 0, 0.05)]],
				"Rig/ArmR:rotation": [[0, Vector3(-0.04, 0, -0.05)], [1.5, Vector3(0.04, 0, -0.08)], [3, Vector3(-0.04, 0, -0.05)]],
				"Rig:position": [[0, Vector3.ZERO], [1.5, Vector3(0, 0.012, 0)], [3, Vector3.ZERO]]}
		"walk":
			L = 0.8
			T = _gait(L, 0.62, 0.55, 0.03, 0.0)
		"climb_stairs":
			L = 1.0
			T = _gait(L, 0.95, 0.4, 0.06, -0.16)
		"climb_ladder":
			L = 1.1
			T = {"Rig/ArmL:rotation": [[0, Vector3(-2.7, 0, 0)], [0.55, Vector3(-2.0, 0, 0)], [1.1, Vector3(-2.7, 0, 0)]],
				"Rig/ArmR:rotation": [[0, Vector3(-2.0, 0, 0)], [0.55, Vector3(-2.7, 0, 0)], [1.1, Vector3(-2.0, 0, 0)]],
				"Rig/LegL:rotation": [[0, Vector3(-0.9, 0, 0)], [0.55, Vector3(-0.1, 0, 0)], [1.1, Vector3(-0.9, 0, 0)]],
				"Rig/LegR:rotation": [[0, Vector3(-0.1, 0, 0)], [0.55, Vector3(-0.9, 0, 0)], [1.1, Vector3(-0.1, 0, 0)]]}
		"open_door":
			L = 1.2
			T = {"Rig/ArmR:rotation": [[0, Vector3.ZERO], [0.3, Vector3(-1.45, 0, 0)], [0.8, Vector3(-1.3, 0.3, 0)], [1.2, Vector3(-1.45, 0, 0)]],
				"Rig:rotation": [[0, Vector3.ZERO], [0.4, Vector3(-0.08, 0, 0)], [1.2, Vector3(-0.08, 0, 0)]]}
		"cook":
			L = 1.4
			T = {"Rig/ArmR:rotation": [[0, Vector3(-1.2, 0.25, 0)], [0.35, Vector3(-1.3, -0.2, 0)], [0.7, Vector3(-1.1, -0.3, 0)], [1.05, Vector3(-1.05, 0.2, 0)], [1.4, Vector3(-1.2, 0.25, 0)]],
				"Rig/ArmL:rotation": [[0, Vector3(-0.9, 0, 0)], [1.4, Vector3(-0.9, 0, 0)]],
				"Rig:rotation": [[0, Vector3(-0.1, 0, 0)], [1.4, Vector3(-0.1, 0, 0)]]}
		"sit", "eat":
			L = 1.6
			T = {"Rig:position": [[0, Vector3(0, -0.38, 0)], [L, Vector3(0, -0.38, 0)]],
				"Rig/LegL:rotation": [[0, Vector3(-1.5, 0, 0)], [L, Vector3(-1.5, 0, 0)]],
				"Rig/LegR:rotation": [[0, Vector3(-1.5, 0, 0)], [L, Vector3(-1.5, 0, 0)]]}
			if n == "eat":
				T["Rig/ArmR:rotation"] = [[0, Vector3(-0.9, 0, 0)], [0.5, Vector3(-2.2, 0, -0.4)], [0.9, Vector3(-2.2, 0, -0.4)], [1.6, Vector3(-0.9, 0, 0)]]
				T["Rig/ArmL:rotation"] = [[0, Vector3(-0.8, 0, 0)], [L, Vector3(-0.8, 0, 0)]]
		"sleep":
			L = 4.0
			T = {"Rig:rotation": [[0, Vector3(-PI / 2, 0, 0)], [L, Vector3(-PI / 2, 0, 0)]],
				"Rig:position": [[0, Vector3(0, 0.02, 0.9)], [2, Vector3(0, 0.035, 0.9)], [L, Vector3(0, 0.02, 0.9)]]}
		"fish":
			L = 3.0
			T = {"Rig/ArmL:rotation": [[0, Vector3(-1.15, 0, 0.1)], [1.5, Vector3(-1.25, 0, 0.1)], [3, Vector3(-1.15, 0, 0.1)]],
				"Rig/ArmR:rotation": [[0, Vector3(-1.15, 0, -0.1)], [1.5, Vector3(-1.25, 0, -0.1)], [3, Vector3(-1.15, 0, -0.1)]],
				"Rig/Rod:visible": [[0, true], [3, true]]}
		"wave":
			L = 0.8
			T = {"Rig/ArmR:rotation": [[0, Vector3(0, 0, -2.6)], [0.2, Vector3(0, 0, -2.2)], [0.4, Vector3(0, 0, -2.7)], [0.6, Vector3(0, 0, -2.2)], [0.8, Vector3(0, 0, -2.6)]]}
		"work":
			L = 0.9
			T = {"Rig/ArmR:rotation": [[0, Vector3(-2.1, 0, 0)], [0.3, Vector3(-0.9, 0, 0)], [0.9, Vector3(-2.1, 0, 0)]],
				"Rig/ArmL:rotation": [[0, Vector3(-0.9, 0, 0)], [0.9, Vector3(-0.9, 0, 0)]],
				"Rig:rotation": [[0, Vector3(-0.06, 0, 0)], [0.3, Vector3(-0.14, 0, 0)], [0.9, Vector3(-0.06, 0, 0)]]}
	a.length = L
	# every clip keys every track, so blending between clips never leaves a limb behind
	for path in rest:
		var keys: Array = T.get(path, [[0.0, rest[path]], [L, rest[path]]])
		var idx := a.add_track(Animation.TYPE_VALUE)
		a.track_set_path(idx, NodePath(path))
		if typeof(rest[path]) == TYPE_BOOL:
			a.value_track_set_update_mode(idx, Animation.UPDATE_DISCRETE)
		for k in keys:
			a.track_insert_key(idx, float(k[0]), k[1])
	return a

func _gait(L: float, leg: float, arm: float, bob: float, lean: float) -> Dictionary:
	var h := L / 2.0
	return {
		"Rig/LegL:rotation": [[0, Vector3(leg, 0, 0)], [h, Vector3(-leg, 0, 0)], [L, Vector3(leg, 0, 0)]],
		"Rig/LegR:rotation": [[0, Vector3(-leg, 0, 0)], [h, Vector3(leg, 0, 0)], [L, Vector3(-leg, 0, 0)]],
		"Rig/ArmL:rotation": [[0, Vector3(-arm, 0, 0)], [h, Vector3(arm, 0, 0)], [L, Vector3(-arm, 0, 0)]],
		"Rig/ArmR:rotation": [[0, Vector3(arm, 0, 0)], [h, Vector3(-arm, 0, 0)], [L, Vector3(arm, 0, 0)]],
		"Rig:position": [[0, Vector3.ZERO], [h / 2, Vector3(0, bob, 0)], [h, Vector3.ZERO], [h * 1.5, Vector3(0, bob, 0)], [L, Vector3.ZERO]],
		"Rig:rotation": [[0, Vector3(lean, 0, 0)], [L, Vector3(lean, 0, 0)]],
	}
