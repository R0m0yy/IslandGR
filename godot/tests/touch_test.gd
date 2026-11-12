extends Node
## Touch controls test: injects Godot touch events (the same events an iPad produces) and checks the camera and HUD.
##   xvfb-run -s "-screen 0 820x1180x24" godot --rendering-method gl_compatibility --resolution 820x1180 res://tests/touch_test.tscn
## (needs a real window so the interface lays out at tablet size)

var fails := 0
func check(n: String, ok: bool, d = "") -> void:
	print("%s  %s  %s" % ["PASS" if ok else "FAIL", n, str(d)])
	if not ok:
		fails += 1

func touch(i: int, pos: Vector2, down: bool) -> void:
	var e := InputEventScreenTouch.new()
	e.index = i
	e.position = pos
	e.pressed = down
	Input.parse_input_event(e)
	Input.flush_buffered_events()

func drag(i: int, pos: Vector2, rel: Vector2) -> void:
	var e := InputEventScreenDrag.new()
	e.index = i
	e.position = pos
	e.relative = rel
	Input.parse_input_event(e)
	Input.flush_buffered_events()

func _ready() -> void:
	GameClock.reset(9.0)
	var v := Village.new()
	add_child(v)
	v.sim.auto = false
	await get_tree().process_frame
	await get_tree().process_frame
	var rig = v.camera_rig
	rig.snap()
	var hud = v.hud
	var vp := get_viewport().get_visible_rect().size
	check("viewport has a size", vp.x > 100, vp)
	# ---- one finger: pan
	var t0: Vector3 = rig.goal_target
	touch(0, Vector2(400, 300), true)
	for k in 10:
		drag(0, Vector2(400 + 12 * (k + 1), 300), Vector2(12, 0))
	touch(0, Vector2(520, 300), false)
	var moved: Vector3 = rig.goal_target - t0
	check("one-finger drag pans the map", moved.length() > 3.0, moved)
	check("dragging right moves the view left (grab the map)", moved.dot(Basis(Vector3.UP, rig.yaw) * Vector3.RIGHT) < 0.0)
	check("touch mode switches the interface on", rig.touch_mode)
	# ---- drag vertically
	var t1: Vector3 = rig.goal_target
	touch(0, Vector2(400, 300), true)
	for k in 10:
		drag(0, Vector2(400, 300 + 12 * (k + 1)), Vector2(0, 12))
	touch(0, Vector2(400, 420), false)
	var fwd: Vector3 = Basis(Vector3.UP, rig.yaw) * Vector3(0, 0, -1)
	check("dragging down moves the view forward", (rig.goal_target - t1).dot(fwd) > 3.0, rig.goal_target - t1)
	# ---- pinch zoom
	var d0: float = rig.goal_dist
	touch(0, Vector2(400, 300), true)
	touch(1, Vector2(500, 300), true)
	for k in 8:
		drag(1, Vector2(500 + 20 * (k + 1), 300), Vector2(20, 0))
	var d_out: float = rig.goal_dist
	check("pinching apart zooms in", d_out < d0 * 0.7, [d0, d_out])
	for k in 8:
		drag(1, Vector2(660 - 20 * (k + 1), 300), Vector2(-20, 0))
	check("pinching back zooms out again", rig.goal_dist > d_out * 1.3, [d_out, rig.goal_dist])
	touch(1, Vector2(500, 300), false)
	touch(0, Vector2(400, 300), false)
	# ---- twist rotates
	var y0: float = rig.goal_yaw
	touch(0, Vector2(500, 300), true)
	touch(1, Vector2(700, 300), true)
	for k in 10:
		var a := 0.05 * (k + 1)
		var p1 := Vector2(600, 300) + Vector2(cos(a), sin(a)) * 100.0
		drag(1, p1, Vector2.ZERO)
	check("twisting two fingers rotates the view", absf(angle_difference(y0, rig.goal_yaw)) > 0.2, snappedf(rig.goal_yaw - y0, 0.01))
	touch(1, Vector2(700, 300), false)
	touch(0, Vector2(500, 300), false)
	# ---- two-finger vertical slide tilts
	var p0: float = rig.goal_pitch
	touch(0, Vector2(500, 300), true)
	touch(1, Vector2(600, 300), true)
	for k in 8:
		drag(0, Vector2(500, 300 + 15 * (k + 1)), Vector2(0, 15))
		drag(1, Vector2(600, 300 + 15 * (k + 1)), Vector2(0, 15))
	check("two fingers sliding down tilt the camera", absf(rig.goal_pitch - p0) > 0.1, snappedf(rig.goal_pitch - p0, 0.01))
	touch(1, Vector2(600, 300), false)
	touch(0, Vector2(500, 300), false)
	# ---- tap selects (nearest resident / boat / building in screen space)
	var cam: Camera3D = rig.cam
	var vv = v.villagers[0]
	rig.snap()
	rig.goal_target = vv.global_position
	rig.goal_dist = 25.0
	rig.snap()
	var sp := cam.unproject_position(vv.global_position + Vector3(0, 1.0, 0))
	touch(0, sp, true)
	touch(0, sp, false)
	check("a tap selects the person under the finger", rig.follow == vv, [vv.display_name, rig.follow])
	# ---- a drag does not select
	rig.release()
	touch(0, sp, true)
	drag(0, sp + Vector2(60, 0), Vector2(60, 0))
	touch(0, sp + Vector2(60, 0), false)
	check("a drag is not a tap", rig.follow == null)
	# ---- buttons: fingers on the bar belong to the interface
	hud._process(1.0)
	hud._t = 0.0
	hud._process(1.0)
	check("button bar is shown after touch", hud.touch_bar.visible)
	var br: Rect2 = hud.touch_bar.get_global_rect()
	var z0: float = rig.goal_dist
	var tp := br.position + Vector2(40, 30)
	touch(0, tp, true)
	for k in 5:
		drag(0, tp + Vector2(0, -30 * (k + 1)), Vector2(0, -30))
	touch(0, tp, false)
	check("a finger that starts on the bar does not move the map", absf(rig.goal_dist - z0) < 0.001 and not rig.follow)
	# ---- buttons press the real commands
	var s0: bool = v.sim.auto
	hud._press(KEY_SPACE)
	await get_tree().process_frame
	check("Pause button toggles the simulation", v.sim.auto != s0)
	hud._press(KEY_SPACE)
	var sc0: float = v.sim.time_scale
	hud.speed_btn.pressed.emit()
	check("Speed button cycles x1 -> x4", v.sim.time_scale == 4.0 and sc0 == 1.0, v.sim.time_scale)
	hud.speed_btn.pressed.emit(); hud.speed_btn.pressed.emit(); hud.speed_btn.pressed.emit()
	check("Speed cycles back to x1", v.sim.time_scale == 1.0)
	var jm: int = hud.journal_mode
	hud._press(KEY_J)
	await get_tree().process_frame
	check("Journal button opens the journal", hud.journal_mode != jm)
	hud._press(KEY_H)
	await get_tree().process_frame
	hud._t = 0.0
	hud._process(1.0)
	var hb = v.buildings.values()[0]
	check("building exterior is merged into one mesh (fewer draw calls)", hb.merged != null and hb.merged.visible and hb.merged.mesh.get_surface_count() <= 6, hb.merged.mesh.get_surface_count() if hb.merged else -1)
	hb.set_cutaway(true)
	var cut_ok: bool = not hb.merged.visible and not hb.groups["ROOF"].visible and hb.groups["WALL_N"].visible and not hb.groups["WALL_S"].visible
	hb.set_cutaway(false)
	check("merged building: cutaway shows the inside, then restores the merged exterior", cut_ok and hb.merged.visible and not hb.groups["ROOF"].visible)
	check("Hide UI hides the bar and shows the small Show UI button", not hud.touch_bar.visible and hud.show_btn.visible)
	hud.show_btn.pressed.emit()
	hud._t = 0.0
	hud._process(1.0)
	check("Show UI brings it back", hud.touch_bar.visible and not hud.show_btn.visible)
	# ---- buttons fit a real iPad (portrait 820 x 1180 pt) : bar height
	check("bar stays within 3 rows at iPad portrait width", hud.touch_bar.size.y <= 140.0, hud.touch_bar.size)
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--shot="):
			rig.release()
			rig.goal_target = Vector3(-4, 6, 0); rig.goal_dist = 105.0; rig.goal_yaw = deg_to_rad(40.0); rig.goal_pitch = deg_to_rad(-30.0); rig.snap()
			var f: Villager = v.villagers[3]
			rig.focus_villager(f)
			rig.goal_dist = 14.0
			rig.snap()
			hud._t = 0.0
			hud._process(1.0)
			for i in 20:
				await get_tree().process_frame
			await RenderingServer.frame_post_draw
			get_viewport().get_texture().get_image().save_png(a.substr(7))
	print("RESULT: %s" % ("PASSED" if fails == 0 else "FAILED (%d)" % fails))
	get_tree().quit(0 if fails == 0 else 1)
