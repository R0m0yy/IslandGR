extends Node
## In-engine screenshots (needs a GL context, e.g. xvfb + Mesa llvmpipe):
##   xvfb-run -s "-screen 0 1600x900x24" godot --rendering-method gl_compatibility \
##       --rendering-driver opengl3 res://tests/capture.tscn -- --out=/abs/dir
## Software GL frames prove the project renders; they say nothing about
## frame rate or how the Forward+ renderer looks on real hardware.

func _ready() -> void:
	var out_dir := "user://"
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--out="):
			out_dir = a.substr(6)
	GameClock.reset(6.0)
	var village := Village.new()
	add_child(village)
	village.sim.auto = false
	var rig = village.camera_rig
	rig.set_process(false)
	rig.set_process_unhandled_input(false)
	village.hud.visible = false
	# name, hour to simulate to, target, yaw deg, pitch deg, distance, cutaway building, follow first villager in state
	var shots := [
		["G01_overview_morning", 9.0, Vector3(-4, 6, 0), 40.0, -30.0, 112.0, "", ""],
		["G02_harbour_midday", 12.5, Vector3(4, 2, 9), 32.0, -24.0, 40.0, "", ""],
		["G03_plaza_stairs", 13.0, Vector3(-13, 6, -5), 38.0, -28.0, 30.0, "", ""],
		["G04_pier_fishing", 13.5, Vector3(5.3, 1.6, 12.5), 55.0, -18.0, 9.0, "", "fish"],
		["G05_cutaway_H01", 14.0, Vector3(-10.5, 2.4, 24.0), 42.0, -42.0, 10.5, "H01", ""],
		["G06_villager_stairs", 14.2, Vector3(-11, 8, -10), 35.0, -25.0, 9.0, "", "climb_stairs"],
		["G07_overview_sunset", 19.0, Vector3(-4, 6, 0), 40.0, -24.0, 112.0, "", ""],
		["G08_harbour_night", 21.0, Vector3(2, 3, 6), 34.0, -24.0, 48.0, "", ""],
		["G09_cutaway_H11_evening", 20.2, Vector3(-27.0, 12.2, 5.2), 40.0, -38.0, 12.5, "H11", ""],
	]
	shots.sort_custom(func(a, b): return a[1] < b[1])
	for s in shots:
		var target_min: float = s[1] * 60.0
		while GameClock.total_minutes < target_min:
			village.sim.advance(10.0)
		var tgt: Vector3 = s[2]
		if s[7] != "":
			# wait (up to an hour of game time) for a villager in the wanted state
			for i in 360:
				var hit = null
				for v in village.villagers:
					if v.fsm.current_name == s[7]:
						hit = v
						break
				if hit:
					tgt = hit.global_position + Vector3(0, 1.0, 0)
					break
				village.sim.advance(1.0)
		rig.target = tgt
		rig.yaw = deg_to_rad(s[3])
		rig.pitch = deg_to_rad(s[4])
		rig.dist = s[5]
		rig._apply()
		if s[6] != "":
			village.buildings[s[6]].set_cutaway(true, village.cut_sides())
		village.day_night.apply(GameClock.hour())
		village.sim._update_lights()
		for i in 6:
			await get_tree().process_frame
		await RenderingServer.frame_post_draw
		var img := get_viewport().get_texture().get_image()
		var path := "%s/%s.png" % [out_dir, s[0]]
		img.save_png(path)
		print("saved ", path, " at ", GameClock.text())
		if s[6] != "":
			village.buildings[s[6]].set_cutaway(false)
	get_tree().quit()
