extends Node
## Following a resident keeps them visible (audit finding: a followed resident indoors was
## hidden by an opaque roof). Also checks the web figure budget keeps everyone represented.
##   godot --headless res://tests/follow_test.tscn
##   xvfb-run ... godot --rendering-method gl_compatibility res://tests/follow_test.tscn -- --out=/abs/dir

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
	GameClock.reset(6.0)
	var village := Village.new()
	add_child(village)
	village.sim.auto = false
	await get_tree().process_frame
	var rig = village.camera_rig
	rig.set_process_unhandled_input(false)
	# 06:00: everyone is at home in bed
	var v = null
	for x in village.villagers:
		if x.inside_building() != "" and x.age >= 18.0:
			v = x
			break
	check("a resident is indoors at 06:00", v != null)
	var home: Building = village.buildings[v.inside_building()]
	rig.focus_villager(v)
	for i in 90:
		await get_tree().process_frame
	check("following indoors opens the building (roof and camera-facing walls)", home.cutaway, home.building_id)
	var sp: Vector2 = rig.cam.unproject_position(v.global_position + Vector3(0, 1.0, 0))
	var size: Vector2 = get_viewport().get_visible_rect().size
	check("the followed resident is framed inside the screen", not rig.cam.is_position_behind(v.global_position) and Rect2(size * 0.2, size * 0.6).has_point(sp), {"screen": sp.round(), "viewport": size})
	if out_dir != "":
		await RenderingServer.frame_post_draw
		get_viewport().get_texture().get_image().save_png(out_dir + "/F01_followed_indoors.png")
	# the day begins: follow them out of the door
	var left := false
	for i in 400:
		village.sim.advance(60.0)
		await get_tree().process_frame
		if v.inside_building() == "":
			left = true
			break
	for i in 5:
		await get_tree().process_frame
	check("the resident leaves home during the morning", left, GameClock.text())
	check("the building closes again once they are outside", not home.cutaway)
	if out_dir != "":
		for i in 60:
			await get_tree().process_frame
		await RenderingServer.frame_post_draw
		get_viewport().get_texture().get_image().save_png(out_dir + "/F02_followed_outdoors.png")
	rig.focus_villager(v)
	rig.release()
	for i in 3:
		await get_tree().process_frame
	check("releasing the follow leaves no building open", village.buildings.values().all(func(b): return not b.cutaway))
	# web / phone budget: everyone stays represented, the followed resident in full detail
	village.low_quality = true
	village.figure_budget = 6
	var far = village.villagers[0]
	var worst := 0.0
	for x in village.villagers:
		var d: float = x.global_position.distance_to(rig.cam.global_position)
		if d > worst and x.animator and x.animator.rig:
			worst = d
			far = x
	rig.focus_villager(far)
	village.apply_figure_budget()
	var full := 0
	var standin := 0
	var nothing := 0
	for x in village.villagers:
		if x.animator == null or x.animator.rig == null:
			continue
		if x.animator.detailed:
			full += 1
		elif x.animator.impostor != null and x.animator.impostor.visible:
			standin += 1
		else:
			nothing += 1
	check("budget: full characters capped, everyone else drawn as a stand-in, nobody invisible", full == 6 and nothing == 0 and standin == village.villagers.size() - 6, {"full": full, "stand_in": standin, "invisible": nothing})
	check("budget: the followed resident is always a full character", far.animator.detailed)
	print("RESULT: %s (%d passed, %d failed)" % ["PASSED" if fails == 0 else "FAILED", passes, fails])
	get_tree().quit(1 if fails else 0)
