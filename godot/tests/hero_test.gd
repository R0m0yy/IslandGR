extends Node
## Hero villagers in Godot: load checks + in-village screenshots.
##   xvfb-run -s "-screen 0 1600x900x24" godot --rendering-method gl_compatibility \
##       --rendering-driver opengl3 res://tests/hero_test.tscn -- --out=/abs/dir
## Checks print PASS/FAIL lines; screenshots: isometric game camera over the
## Harbour Stair and a close-up of each hero.

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
	GameClock.reset(9.5)
	var village := Village.new()
	add_child(village)
	village.sim.auto = false
	await get_tree().process_frame
	var hs = village.hero_showcase
	check("hero showcase built on the Harbour Stair", hs != null)
	if hs == null:
		print("RESULT: FAILED"); get_tree().quit(); return
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
		var sk: Skeleton3D = h.model.find_child("*", true, false) as Skeleton3D
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
		var tris := 0
		var headless := DisplayServer.get_name() == "headless"
		for mi in ([] if headless else h.model.find_children("*", "MeshInstance3D", true, false)):
			var m: Mesh = mi.mesh
			for si in m.get_surface_count():
				var arr := m.surface_get_arrays(si)
				tris += (arr[Mesh.ARRAY_INDEX].size() if arr[Mesh.ARRAY_INDEX] else arr[Mesh.ARRAY_VERTEX].size()) / 3
		if not headless:
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
		if DisplayServer.get_name() == "headless":
			hs._process(1.0 / 30.0)
	check("captain moves along the stair", hs.heroes.has("A") and hs._a_u > 0.0, snappedf(hs._a_u, 0.01))
	if out_dir != "":
		village.set_figures_visible(false)
		village.hud.visible = false
		var rig = village.camera_rig
		rig.set_process_unhandled_input(false)
		var mid: Vector3 = hs.stair_point(0.5)
		var shots := [["H01_harbour_stair_game_camera", mid + Vector3(0, 1, 0), 40.0, -32.0, 26.0]]
		for k in hs.heroes:
			var h: Node3D = hs.heroes[k]
			shots.append(["H_close_%s" % k, h.global_position + Vector3(0, 1.1 if k != "D" else 0.8, 0), rad_to_deg(h.rotation.y) + 20.0, -10.0, 3.4])
		for s in shots:
			rig.release()
			rig.goal_target = s[1]
			rig.goal_yaw = deg_to_rad(s[2])
			rig.goal_pitch = deg_to_rad(s[3])
			rig.goal_dist = s[4]
			rig.snap()
			village.day_night.apply(GameClock.hour())
			for i in 30:
				await get_tree().process_frame
			await RenderingServer.frame_post_draw
			var img := get_viewport().get_texture().get_image()
			img.save_png("%s/%s.png" % [out_dir, s[0]])
			print("saved ", s[0])
	print("RESULT: %s (%d passed, %d failed)" % ["PASSED" if fails == 0 else "FAILED", passes, fails])
	get_tree().quit()
