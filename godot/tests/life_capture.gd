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
	# boats: photograph a rowed skiff and a motor boat while they are under way in open water
	for want in [["L03_rowing_skiff", false], ["L04_motor_boat", true]]:
		var got = null
		for i in 600:
			for b in village.boats.values():
				if b.engine == want[1] and b.boat_state in ["outbound", "inbound"] and b.crew != null and b.pos.length() > 24.0:
					got = b
					break
			if got:
				break
			village.sim.advance(1.0)
			await get_tree().process_frame
		if got == null:
			print("no boat for ", want[0])
			continue
		var crew = got.crew
		crew._react_t = 0.0
		crew.play(crew.fsm.current.anim)
		print("BOAT ", got.object_id, " state=", got.boat_state, " crew=", crew.display_name, " fsm=", crew.fsm.current_name,
			" anim=", crew.fsm.current.anim, " animator.current=", crew.animator.current, " tree=", crew.animator.playback.get_current_node(), " travel=", crew.animator.playback.get_travel_path(), " phase=", crew.animator.phase(),
			" gear=", got.gear.keys(), " variant=", crew.animator.variant)
		for v in village.villagers:
			if v.global_position.distance_to(got.visual_pos()) < 5.0:
				print("  NEAR ", v.display_name, " d=", snappedf(v.global_position.distance_to(got.visual_pos()), 0.01), " local=", got.visual.to_local(v.global_position).snapped(Vector3.ONE * 0.01),
					" at_sea=", v.at_sea, " fsm=", v.fsm.current_name, " anim=", v.animator.current if v.animator else "-", " react=", v._react_t)
		var hd: float = got.visual.rotation.y
		var bow := Vector3(cos(hd), 0, -sin(hd))
		var side := bow.cross(Vector3.UP)
		var out: Vector3 = Vector3(got.pos.x, 0, got.pos.z).normalized()
		var sea_side: Vector3 = side if side.dot(out) > 0.0 else -side
		var vp: Vector3 = got.visual_pos()
		await _shot(want[0], vp + sea_side * 4.0 + bow * 1.2 + Vector3(0, 2.2, 0), vp + Vector3(0, 0.6, 0))
	if "--boats-only" in OS.get_cmdline_user_args():
		get_tree().quit()
		return
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
		life.set_process(false)                  # hold the plane still for the photograph
		life.plane.global_position = Vector3(-10, 30, 70)
		await _shot("L09_plane_over_the_bay", Vector3(14, 5, 44), life.plane.global_position)
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
