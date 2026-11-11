extends Node
## In-engine screenshots (needs a GL context, e.g. xvfb + Mesa llvmpipe):
##   xvfb-run -s "-screen 0 1600x900x24" godot --rendering-method gl_compatibility \
##       --rendering-driver opengl3 res://tests/capture.tscn -- --out=/abs/dir
## Two sets: E* environment presentation (temporary figures hidden, no UI) and
## T* technical frames showing navigation / interaction / inspectors with the
## neutral temporary figures. Software GL frames prove the project renders;
## they say nothing about frame rate or the Forward+ look on real hardware.

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
	# name, hour, target, yaw, pitch, dist, mode
	#   mode: "" plain | "storm" | "boat" follow a boat at sea | "resident:<state>" | "building:<ID>" | "village"
	var shots := [
		["E01_overview_morning", 8.5, Vector3(-4, 6, 0), 40.0, -30.0, 112.0, ""],
		["E02_harbour_midday", 12.0, Vector3(4, 2, 9), 32.0, -24.0, 40.0, ""],
		["E03_district_boardwalk", 12.2, Vector3(-2, 2.5, 18.5), 38.0, -20.0, 21.0, ""],
		["E04_district_cottage_stair", 12.4, Vector3(-10, 3.2, 19), 52.0, -22.0, 22.0, ""],
		["E05_sea_arch", 12.6, Vector3(35, 4.5, 8.5), 82.0, -9.0, 30.0, ""],
		["E06_cliffs_west", 12.8, Vector3(-30, 8, 6), -70.0, -16.0, 58.0, ""],
		["E07_shoreline_beach", 13.0, Vector3(4, 0.8, 25.5), 30.0, -20.0, 16.0, ""],
		["T01_boat_at_sea", 9.5, Vector3.ZERO, 30.0, -24.0, 26.0, "boat"],
		["T02_resident_inspector_stairs", 13.2, Vector3.ZERO, 35.0, -25.0, 10.0, "resident:climb_stairs"],
		["T03_building_cutaway_H01", 13.6, Vector3.ZERO, 42.0, -42.0, 12.0, "building:H01"],
		["T04_market_inspector", 13.8, Vector3.ZERO, 30.0, -40.0, 20.0, "building:P01"],
		["T05_village_inspector", 14.0, Vector3(-4, 6, 0), 40.0, -30.0, 112.0, "village"],
		["E08_storm_harbour", 15.0, Vector3(4, 2, 9), 32.0, -22.0, 44.0, "storm"],
		["E09_golden_hour", 18.7, Vector3(-4, 6, 0), 40.0, -22.0, 105.0, ""],
		["E10_harbour_night", 21.0, Vector3(2, 3, 6), 34.0, -24.0, 48.0, ""],
		["T06_cutaway_H11_evening", 20.3, Vector3.ZERO, 40.0, -38.0, 12.5, "building:H11"],
	]
	shots.sort_custom(func(a, b): return a[1] < b[1])
	for s in shots:
		var mode: String = s[6]
		while GameClock.total_minutes < s[1] * 60.0:
			village.sim.advance(10.0)
			if mode != "storm" and village.weather.state in ["rain", "storm"]:
				village.weather.force("cloudy")
		var env_shot: bool = String(s[0]).begins_with("E")
		village.set_figures_visible(not env_shot)
		village.hud.visible = not env_shot
		village.hud.show_village = false
		rig.release()
		rig.goal_target = s[2]
		if mode == "storm":
			village.weather.force("storm")
			for i in 30:
				village.sim.advance(10.0)
				village.weather.state = "storm"
		elif mode == "boat":
			for i in 900:
				var hit = null
				for b in village.boats.values():
					if b.boat_state in ["outbound", "fishing"] and b.pos.distance_to(b.home_pos) > 14.0:
						hit = b
				if hit:
					rig.focus_boat(hit)
					rig.goal_target = hit.pos + Vector3(0, 1.2, 0)
					break
				village.sim.advance(2.0)
		elif mode.begins_with("resident:"):
			for i in 600:
				var hv = null
				for v in village.villagers:
					if v.fsm.current_name == mode.substr(9):
						hv = v
						break
				if hv:
					rig.focus_villager(hv)
					rig.goal_target = hv.global_position + Vector3(0, 1.2, 0)
					break
				village.sim.advance(1.0)
		elif mode == "village":
			village.hud.show_village = true
		rig.goal_yaw = deg_to_rad(s[3])
		rig.goal_pitch = deg_to_rad(s[4])
		rig.goal_dist = s[5]
		rig.snap()
		if mode.begins_with("building:"):
			rig.focus_building(village.buildings[mode.substr(9)])
			rig.goal_yaw = deg_to_rad(s[3])
			rig.snap()
		village.day_night.apply(GameClock.hour())
		village.sim._update_lights()
		for i in 20:
			await get_tree().process_frame
		await RenderingServer.frame_post_draw
		var img := get_viewport().get_texture().get_image()
		var path := "%s/%s.png" % [out_dir, s[0]]
		img.save_png(path)
		print("saved ", path, " at ", GameClock.text(), " weather ", village.weather.state)
		if mode == "storm":
			village.weather.force("clear")
			village.weather.cloud = 0.05; village.weather.rain = 0.0; village.weather.wind = 0.15
	get_tree().quit()
