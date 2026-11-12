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
var family_hh: String = ""              # follow a whole household
var cinematic: bool = false
var _wi := -1
var _cine_t := 0.0
var _cine_label := ""
var _fi := -1
var _bi := -1
var _saved_dist := 95.0
var touch_mode := false                  # true once a finger has touched the screen
var _touches := {}                       # finger index -> current position
var _tstart := {}                        # finger index -> [start pos, start ms, moved]
var _blocked := {}                       # fingers that began on a button or panel
var _pd := 0.0                           # last two-finger distance / angle / centre
var _pa := 0.0
var _pc := Vector2.ZERO

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
	family_hh = ""
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
	if ev is InputEventScreenTouch or ev is InputEventScreenDrag:
		_touch(ev)
		return
	if ev is InputEventMouse and ev.device == InputEvent.DEVICE_ID_EMULATION:
		return                           # mouse events synthesised from touch: the gestures below handle those fingers
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
				family_hh = ""
				cinematic = false
			KEY_C:
				village.toggle_cutaway(follow.inside_building() if follow is Villager else "")
			KEY_G:
				if follow is Villager:
					family_hh = follow.hh
					follow = null
					goal_dist = 24.0
			KEY_N:
				var ws: Array = village.atmosphere.watchables if village.atmosphere else []
				if not ws.is_empty():
					_wi = (_wi + 1) % ws.size()
					_clear_building()
					family_hh = ""
					follow = ws[_wi][1]
					_cine_label = ws[_wi][0]
					goal_dist = 14.0
					goal_pitch = deg_to_rad(-22.0)
			KEY_K:
				cinematic = not cinematic
				_cine_t = 0.0
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
	if cinematic:
		_cinema(dt)
	if follow and is_instance_valid(follow):
		goal_target = (follow.pos if follow is Boat else follow.global_position) + Vector3(0, 1.2, 0)
	elif family_hh != "":
		var c := Vector3.ZERO
		var n := 0
		for v in village.villagers:
			if v.hh == family_hh:
				c += v.global_position
				n += 1
		if n > 0:
			goal_target = c / n + Vector3(0, 1.2, 0)
	var k := 1.0 - exp(-dt * 6.0)
	target = target.lerp(goal_target, k)
	dist = lerpf(dist, goal_dist, k)
	yaw = lerp_angle(yaw, goal_yaw, k)
	pitch = lerpf(pitch, goal_pitch, k)
	_apply()

func release_follow() -> void:
	follow = null
	family_hh = ""
	cinematic = false

func _touch(ev: InputEvent) -> void:
	## One finger drags the map, a tap selects, two fingers pinch to zoom, twist to
	## rotate and slide up or down to tilt. Fingers that start on a button or panel
	## belong to the interface and are ignored here.
	touch_mode = true
	if ev is InputEventScreenTouch:
		if ev.pressed:
			if village and village.hud and village.hud.touch_blocks(ev.position):
				_blocked[ev.index] = true
				return
			_touches[ev.index] = ev.position
			_tstart[ev.index] = [ev.position, Time.get_ticks_msec(), false]
			if _touches.size() >= 2:
				_pinch_reset()
		else:
			if _blocked.erase(ev.index):
				return
			if _touches.has(ev.index):
				var st: Array = _tstart[ev.index]
				if _touches.size() == 1 and not st[2] and Time.get_ticks_msec() - int(st[1]) < 450 and ev.position.distance_to(st[0]) < 16.0 and village:
					pick(ev.position)
				_touches.erase(ev.index)
				_tstart.erase(ev.index)
				if _touches.size() >= 2:
					_pinch_reset()
		return
	if not _touches.has(ev.index):
		return
	_touches[ev.index] = ev.position
	if _touches.size() == 1:
		var st2: Array = _tstart[ev.index]
		if not st2[2] and ev.position.distance_to(st2[0]) > 16.0:
			st2[2] = true
		if st2[2]:
			release_follow()
			var b := Basis(Vector3.UP, yaw)
			goal_target += b * Vector3(-ev.relative.x, 0.0, -ev.relative.y) * dist * 0.0017
	else:
		for k in _tstart:
			_tstart[k][2] = true
		var keys: Array = _touches.keys()
		keys.sort()
		var a: Vector2 = _touches[keys[0]]
		var c: Vector2 = _touches[keys[1]]
		var d := a.distance_to(c)
		var ang := (c - a).angle()
		var ctr := (a + c) * 0.5
		if _pd > 8.0 and d > 8.0:
			goal_dist = clampf(goal_dist * (_pd / d), 5.0, 240.0)
			goal_yaw += angle_difference(_pa, ang)
			goal_pitch = clampf(goal_pitch - (ctr.y - _pc.y) * 0.005, deg_to_rad(-85), deg_to_rad(-8))
		_pd = d
		_pa = ang
		_pc = ctr

func _pinch_reset() -> void:
	var keys: Array = _touches.keys()
	keys.sort()
	var a: Vector2 = _touches[keys[0]]
	var c: Vector2 = _touches[keys[1]]
	_pd = a.distance_to(c)
	_pa = (c - a).angle()
	_pc = (a + c) * 0.5

func _cinema(dt: float) -> void:
	## Cinematic observer: a slow drift round the subject; every half minute it
	## cuts to the newest notable event in the journal, else to someone at random.
	goal_yaw += dt * 0.06
	_cine_t -= dt
	if _cine_t > 0.0:
		return
	_cine_t = 30.0
	_clear_building()
	family_hh = ""
	var q: Array = village.journal.notable_queue
	if not q.is_empty():
		var e: Dictionary = q.pop_back()
		for id in e["actors"]:
			var v = village.villager_by_id(id)
			if v:
				follow = v
				goal_dist = 16.0
				_cine_label = e["text"]
				return
		if e.has("where"):
			follow = null
			goal_target = Vector3(e["where"][0], e["where"][1], e["where"][2])
			goal_dist = 22.0
			_cine_label = e["text"]
			return
	if randf() < 0.5 and village.atmosphere and not village.atmosphere.watchables.is_empty():
		var w: Array = village.atmosphere.watchables[randi() % village.atmosphere.watchables.size()]
		follow = w[1]
		_cine_label = w[0]
		goal_dist = 14.0
	elif not village.villagers.is_empty():
		follow = village.villagers[randi() % village.villagers.size()]
		_cine_label = follow.display_name
		goal_dist = 18.0

func mode_text() -> String:
	if cinematic:
		return "cinematic: " + _cine_label.left(70)
	if family_hh != "":
		return "following " + village.household_name(family_hh)
	if follow is Boat:
		return "following " + follow.object_id
	if follow and not (follow is Villager) and _cine_label != "":
		return "watching " + _cine_label
	return ""

func snap() -> void:
	target = goal_target; dist = goal_dist; yaw = goal_yaw; pitch = goal_pitch
	_apply()

func _apply() -> void:
	var b := Basis(Vector3.UP, yaw) * Basis(Vector3.RIGHT, pitch)
	cam.global_position = target + b * Vector3(0, 0, dist)
	cam.look_at(target, Vector3.UP)
