extends Node3D
## Diorama camera. Orbit, zoom and pan are eased; clicking selects a resident
## (follow), a boat (follow) or a building (focus + cutaway). All motion goes
## through goal values so there are no snaps.

var village = null
var cam: Camera3D
var target := Vector3(-4, 6, 2)
var yaw := deg_to_rad(40.0)              # default view from the south-east (WORLD_LAYOUT.md)
var pitch := deg_to_rad(-32.0)
var dist := 95.0
var goal_target := Vector3(-4, 6, 2)
var goal_dist := 95.0
var goal_yaw := deg_to_rad(40.0)
var goal_pitch := deg_to_rad(-32.0)
var follow = null                        # Villager or Boat
var selected_building: Building = null
var _fi := -1
var _bi := -1
var _saved_dist := 95.0

func _ready() -> void:
	cam = Camera3D.new()
	cam.name = "Camera"
	cam.fov = 38.0
	cam.far = 900.0
	add_child(cam)
	cam.current = true
	_apply()

func focus_villager(v) -> void:
	_clear_building()
	follow = v
	goal_dist = minf(goal_dist, 20.0)

func focus_boat(b) -> void:
	_clear_building()
	follow = b
	goal_dist = minf(goal_dist, 30.0)

func focus_building(b: Building) -> void:
	_clear_building()
	follow = null
	selected_building = b
	_saved_dist = goal_dist
	var r: Dictionary = b.record
	goal_target = Vector3(r["cx"], r["y"] + 1.2, r["cz"])
	goal_dist = 15.0 + 2.0 * float(r["storeys"])
	goal_pitch = deg_to_rad(-42.0)
	b.set_cutaway(true, village.cut_sides())

func release() -> void:
	follow = null
	if selected_building:
		goal_dist = _saved_dist
		goal_pitch = deg_to_rad(-32.0)
	_clear_building()

func _clear_building() -> void:
	if selected_building:
		selected_building.set_cutaway(false)
		selected_building = null

func pick(screen: Vector2) -> void:
	## Nearest resident, then boat, then building to the click, in screen space.
	var best = null
	var bd := 26.0
	for v in village.villagers:
		if cam.is_position_behind(v.global_position):
			continue
		var d := cam.unproject_position(v.global_position + Vector3(0, 1.0, 0)).distance_to(screen)
		if d < bd:
			bd = d
			best = v
	if best:
		focus_villager(best)
		return
	bd = 40.0
	for b in village.boats.values():
		var d2 := cam.unproject_position(b.pos + Vector3(0, 0.6, 0)).distance_to(screen)
		if d2 < bd:
			bd = d2
			best = b
	if best:
		focus_boat(best)
		return
	bd = 70.0
	var bb: Building = null
	for id in village.buildings:
		var r: Dictionary = village.buildings[id].record
		var c := Vector3(r["cx"], r["y"] + 1.5, r["cz"])
		if cam.is_position_behind(c):
			continue
		var d3 := cam.unproject_position(c).distance_to(screen)
		if d3 < bd:
			bd = d3
			bb = village.buildings[id]
	if bb:
		focus_building(bb)
	else:
		release()

func _unhandled_input(ev: InputEvent) -> void:
	if ev is InputEventMouseMotion:
		if ev.button_mask & MOUSE_BUTTON_MASK_RIGHT:
			goal_yaw -= ev.relative.x * 0.005
			goal_pitch = clampf(goal_pitch - ev.relative.y * 0.005, deg_to_rad(-85), deg_to_rad(-8))
		elif ev.button_mask & MOUSE_BUTTON_MASK_MIDDLE:
			var r := cam.global_transform.basis
			goal_target += (-r.x * ev.relative.x + r.y * ev.relative.y) * dist * 0.0012
	elif ev is InputEventMouseButton and ev.pressed:
		if ev.button_index == MOUSE_BUTTON_WHEEL_UP:
			goal_dist = maxf(5.0, goal_dist * 0.88)
		elif ev.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			goal_dist = minf(240.0, goal_dist * 1.12)
		elif ev.button_index == MOUSE_BUTTON_LEFT and village:
			pick(ev.position)
	elif ev is InputEventKey and ev.pressed and not ev.echo and village:
		match ev.keycode:
			KEY_TAB:
				if not village.villagers.is_empty():
					_fi = (_fi + 1) % village.villagers.size()
					focus_villager(village.villagers[_fi])
			KEY_B:
				var bs: Array = village.boats.values()
				if not bs.is_empty():
					_bi = (_bi + 1) % bs.size()
					focus_boat(bs[_bi])
			KEY_ESCAPE:
				release()
			KEY_C:
				village.toggle_cutaway(follow.inside_building() if follow is Villager else "")
			KEY_Q: goal_yaw += deg_to_rad(45.0)
			KEY_E: goal_yaw -= deg_to_rad(45.0)

func _process(dt: float) -> void:
	var mv := Vector3.ZERO
	if Input.is_key_pressed(KEY_W): mv.z -= 1
	if Input.is_key_pressed(KEY_S): mv.z += 1
	if Input.is_key_pressed(KEY_A): mv.x -= 1
	if Input.is_key_pressed(KEY_D): mv.x += 1
	if mv != Vector3.ZERO:
		follow = null
		goal_target += Basis(Vector3.UP, yaw) * mv.normalized() * dist * 0.6 * dt
	if follow and is_instance_valid(follow):
		goal_target = (follow.pos if follow is Boat else follow.global_position) + Vector3(0, 1.2, 0)
	var k := 1.0 - exp(-dt * 6.0)
	target = target.lerp(goal_target, k)
	dist = lerpf(dist, goal_dist, k)
	yaw = lerp_angle(yaw, goal_yaw, k)
	pitch = lerpf(pitch, goal_pitch, k)
	_apply()

func snap() -> void:
	target = goal_target; dist = goal_dist; yaw = goal_yaw; pitch = goal_pitch
	_apply()

func _apply() -> void:
	var b := Basis(Vector3.UP, yaw) * Basis(Vector3.RIGHT, pitch)
	cam.global_position = target + b * Vector3(0, 0, dist)
	cam.look_at(target, Vector3.UP)
