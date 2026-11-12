extends Node
## Hero villagers in Godot: load checks + in-village screenshots.
##   godot --headless res://tests/hero_test.tscn                      (checks only)
##   xvfb-run -s "-screen 0 1280x720x24" godot --rendering-method gl_compatibility \
##       --rendering-driver opengl3 res://tests/hero_test.tscn -- --out=/abs/dir
## Screenshots: the game's orbit camera over the Harbour Stair and a close
## camera in front of each hero.

var fails := 0
var passes := 0

func check(n: String, ok: bool, d = "") -> void:
	if ok:
		passes += 1
	else:
		fails += 1
	print(("PASS  " if ok else "FAIL  ") + n + "  " + str(d))

func _ready() -> void:
	var out_dir := ""
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--out="):
			out_dir = a.substr(6)
	var headless := DisplayServer.get_name() == "headless"
	GameClock.reset(9.5)
	var village := Village.new()
	add_child(village)
	village.sim.auto = false
	await get_tree().process_frame
	var hs = village.hero_showcase
	check("hero showcase built on the Harbour Stair", hs != null)
	if hs == null:
		_finish()
		return
	hs.set_process(false)          # the showcase script would override clips during the checks
	for k in ["A", "B", "C", "D"]:
		var h: HeroVillager = hs.heroes.get(k)
		check("%s loads (%s)" % [k, HeroVillager.TITLES[k]], h != null)
		if h == null:
			continue
		var missing := []
		for c in VillagerAnimator.CLIPS + ["run", HeroVillager.JOB[k]]:
			if not h.has_clip(c):
				missing.append(c)
		check("%s has every contract clip + run + %s" % [k, HeroVillager.JOB[k]], missing.is_empty(), missing if missing else h.clips().size())
		check("%s has facial blend shapes (blink, smile, mouth)" % k, h.face_meshes.size() > 0 and h.face_meshes[0].find_blend_shape_by_name("smile") >= 0
			and h.face_meshes[0].find_blend_shape_by_name("mouth_open") >= 0, h.face_meshes.size())
		var sk: Skeleton3D = null
		for n in h.model.find_children("*", "Skeleton3D", true, false):
			sk = n
		# held props (bucket, cane, net, fish, basket ...) import as extra skeleton nodes named <key>_<prop>;
		# glTF may add a "neutral_bone" for unweighted vertices. Neither is part of the rig.
		var nb := 0
		if sk:
			for bi in sk.get_bone_count():
				var bn := sk.get_bone_name(bi)
				if not (bn.begins_with(k + "_") or bn == "neutral_bone"):
					nb += 1
		check("%s shares the 53-bone game rig" % k, nb == 53, nb)
		if not headless:
			var tris := 0
			for mi in h.model.find_children("*", "MeshInstance3D", true, false):
				var m: Mesh = mi.mesh
				for si in m.get_surface_count():
					var arr := m.surface_get_arrays(si)
					tris += (arr[Mesh.ARRAY_INDEX].size() if arr[Mesh.ARRAY_INDEX] else arr[Mesh.ARRAY_VERTEX].size()) / 3
			check("%s game mesh within 20k triangles" % k, tris > 0 and tris <= 20000, tris)
		if h.player == null:
			check("%s switches clips" % k, false, "no AnimationPlayer")
			continue
		h.play("walk")
		await get_tree().process_frame
		check("%s switches clips" % k, h.player.current_animation == "walk", h.player.current_animation)
	# let the showcase run for a few seconds of animation
	hs.set_process(true)
	for i in 90:
		await get_tree().process_frame
		if headless:
			hs._process(1.0 / 30.0)
	check("captain moves along the stair", hs.heroes.has("A") and hs._a_u > 0.0, snappedf(hs._a_u, 0.01))
	if out_dir != "":
		await _screenshots(village, hs, out_dir)
	_finish()

func _finish() -> void:
	print("RESULT: %s (%d passed, %d failed)" % ["PASSED" if fails == 0 else "FAILED", passes, fails])
	get_tree().quit()

func _screenshots(village, hs, out_dir: String) -> void:
	village.set_figures_visible(false)
	village.hud.visible = false
	var rig = village.camera_rig
	rig.set_process_unhandled_input(false)
	var mid: Vector3 = hs.stair_point(0.5)
	# 1) the game's own orbit camera at its normal isometric angle over the Harbour Stair
	rig.release()
	rig.goal_target = mid + Vector3(0, 1, 0)
	rig.goal_yaw = deg_to_rad(40.0)
	rig.goal_pitch = deg_to_rad(-34.0)
	rig.goal_dist = 18.0
	rig.snap()
	await _shot(out_dir, "H01_harbour_stair_game_camera", village)
	# 2) a close camera in front of each hero (its own Camera3D, so walls cannot get in the way)
	var cam := Camera3D.new()
	cam.fov = 40.0
	add_child(cam)
	for k in hs.heroes:
		var h: Node3D = hs.heroes[k]
		if k == "A":
			hs.set_process(false)
			h.play("haul_rope")
		var fwd: Vector3 = -h.global_transform.basis.z
		var right: Vector3 = h.global_transform.basis.x
		var hgt := 0.85 if k == "D" else 1.15
		var look: Vector3 = h.global_position + Vector3(0, hgt, 0)
		cam.global_position = look + fwd * (2.1 if k != "D" else 1.7) + right * 0.55 + Vector3(0, 0.25, 0)
		cam.look_at(look, Vector3.UP)
		cam.current = true
		await _shot(out_dir, "H_close_%s" % k, village)
	cam.current = false

func _shot(out_dir: String, name_: String, village) -> void:
	village.day_night.apply(GameClock.hour())
	for i in 30:
		await get_tree().process_frame
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	img.save_png("%s/%s.png" % [out_dir, name_])
	print("saved ", name_)
