extends Node
## Screenshots of the living village (session 8): residents as characters, market
## stalls serving, rowing and motor boats, swimmers, surf, wildlife, the plane.
##   xvfb-run -s "-screen 0 1280x720x24" godot --rendering-method gl_compatibility \
##       --rendering-driver opengl3 res://tests/life_capture.tscn -- --out=/abs/dir

var village
var out_dir := ""
var cam: Camera3D

func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--out="):
			out_dir = a.substr(6)
	GameClock.reset(6.0)
	village = Village.new()
	add_child(village)
	village.sim.auto = false
	await get_tree().process_frame
	village.hud.visible = false
	village.camera_rig.set_process_unhandled_input(false)
	cam = Camera3D.new()
	cam.fov = 45.0
	add_child(cam)
	# morning: run the village to market time, keep the weather fine
	await _advance_to(9.6)
	await _shot("L01_market_stalls", Vector3(9.5, 3.4, 9.5), Vector3(9.5, 2.2, 2.6))
	await _shot("L02_village_crowd", Vector3(-4, 22, 34), Vector3(-2, 4, 4))
	# boats: find one being rowed and one under motor
	var rowed = null
	var motored = null
	for i in 400:
		for b in village.boats.values():
			if b.boat_state in ["outbound", "inbound"] and b.crew != null and b.pos.distance_to(b.home_pos) > 6.0:
				if b.engine and motored == null:
					motored = b
				if not b.engine and rowed == null:
					rowed = b
		if rowed and motored:
			break
		village.sim.advance(2.0)
		await get_tree().process_frame
	for pair in [["L03_rowing_skiff", rowed], ["L04_motor_boat", motored]]:
		var b = pair[1]
		if b == null:
			print("no boat for ", pair[0])
			continue
		var hd: float = b.visual.rotation.y
		var bow := Vector3(cos(hd), 0, -sin(hd))
		var side := bow.cross(Vector3.UP)
		await _shot(pair[0], b.pos + side * 5.5 + bow * 2.0 + Vector3(0, 2.6, 0), b.pos + Vector3(0, 0.6, 0))
	# a fine afternoon: some residents go for a swim off the spit
	await _advance_to(13.2)
	var n := 0
	for v in village.villagers:
		if n >= 4:
			break
		if v.age >= 8.0 and not v.at_sea and v.fsm.current_name in ["idle", "walk", "sit"]:
			v.at_node = "sp_2" if n % 2 == 0 else "sp_1"
			v.plan = [{"swim": 120.0}]
			v.path = []
			v.step_done()
			n += 1
	for i in 40:
		village.sim.advance(0.5)
		await get_tree().process_frame
	var spot: Vector3 = village.swim_spot("sp_2")
	await _shot("L05_swimmers", spot + Vector3(-6, 3.5, 6), spot + Vector3(0, 0, 0))
	await _shot("L06_surf_shore", Vector3(4, 4.5, 33), Vector3(4, 0.2, 25))
	# wildlife: the nearest flying bird and the dolphin pod
	var bird: Node3D = null
	for b in village.atmosphere._birds.values():
		if b.has_node("Fly") and b.get_node("Fly").visible:
			bird = b
			break
	if bird:
		await _shot("L07_bird_in_flight", bird.global_position + Vector3(2.5, 0.8, 2.5), bird.global_position)
	var pod: Node3D = village.atmosphere.get_node_or_null("Wildlife/DolphinPod")
	if pod:
		await _shot("L08_dolphins", pod.global_position + Vector3(6, 3, 6), pod.global_position)
	var life = village.village_life
	if life and life.plane:
		life._launch_plane()
		life.plane.global_position = Vector3(-40, 55, 40)
		for i in 3:
			await get_tree().process_frame
		await _shot("L09_plane_over_the_bay", Vector3(10, 4, 40), life.plane.global_position)
	get_tree().quit()

func _advance_to(hour: float) -> void:
	while GameClock.hour() < hour:
		village.sim.advance(5.0)
		if village.weather.state in ["light_rain", "heavy_rain", "storm"]:
			village.weather.force("clear")
		await get_tree().process_frame

func _shot(name_: String, from: Vector3, to: Vector3) -> void:
	cam.global_position = from
	cam.look_at(to, Vector3.UP)
	cam.current = true
	village.day_night.apply(GameClock.hour())
	for i in 30:
		await get_tree().process_frame
	await RenderingServer.frame_post_draw
	if out_dir != "":
		get_viewport().get_texture().get_image().save_png("%s/%s.png" % [out_dir, name_])
	print("saved ", name_, " at ", GameClock.text())
