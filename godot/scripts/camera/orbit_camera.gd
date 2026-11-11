extends Node3D
## Diorama camera: orbit (right mouse drag), zoom (wheel), pan (WASD / middle
## drag), follow a villager (Tab cycles, Esc releases).

var village = null
var cam: Camera3D
var target := Vector3(-4, 6, 2)
var yaw := deg_to_rad(40.0)             # default view from the south-east (WORLD_LAYOUT.md)
var pitch := deg_to_rad(-32.0)
var dist := 95.0
var follow = null
var _fi := -1

func _ready() -> void:
	cam = Camera3D.new()
	cam.name = "Camera"
	cam.fov = 38.0
	cam.far = 900.0
	add_child(cam)
	cam.current = true
	_apply()

func _unhandled_input(ev: InputEvent) -> void:
	if ev is InputEventMouseMotion:
		if ev.button_mask & MOUSE_BUTTON_MASK_RIGHT:
			yaw -= ev.relative.x * 0.005
			pitch = clampf(pitch - ev.relative.y * 0.005, deg_to_rad(-85), deg_to_rad(-5))
		elif ev.button_mask & MOUSE_BUTTON_MASK_MIDDLE:
			var r := cam.global_transform.basis
			target += (-r.x * ev.relative.x + r.y * ev.relative.y) * dist * 0.0012
	elif ev is InputEventMouseButton and ev.pressed:
		if ev.button_index == MOUSE_BUTTON_WHEEL_UP:
			dist = maxf(4.0, dist * 0.9)
		elif ev.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			dist = minf(260.0, dist * 1.1)
	elif ev is InputEventKey and ev.pressed and not ev.echo:
		match ev.keycode:
			KEY_TAB:
				if village and not village.villagers.is_empty():
					_fi = (_fi + 1) % village.villagers.size()
					follow = village.villagers[_fi]
					dist = minf(dist, 22.0)
			KEY_ESCAPE:
				follow = null
			KEY_C:
				if village:
					village.toggle_cutaway(follow.inside_building() if follow else "")

func _process(dt: float) -> void:
	var mv := Vector3.ZERO
	if Input.is_key_pressed(KEY_W): mv.z -= 1
	if Input.is_key_pressed(KEY_S): mv.z += 1
	if Input.is_key_pressed(KEY_A): mv.x -= 1
	if Input.is_key_pressed(KEY_D): mv.x += 1
	if mv != Vector3.ZERO:
		follow = null
		target += Basis(Vector3.UP, yaw) * mv.normalized() * dist * 0.6 * dt
	if follow and is_instance_valid(follow):
		target = target.lerp(follow.global_position + Vector3(0, 1.2, 0), minf(1.0, dt * 4.0))
	_apply()

func _apply() -> void:
	var b := Basis(Vector3.UP, yaw) * Basis(Vector3.RIGHT, pitch)
	cam.global_position = target + b * Vector3(0, 0, dist)
	cam.look_at(target, Vector3.UP)
