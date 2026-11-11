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

func play(clip: String) -> void:
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
