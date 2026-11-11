extends Node
## Short gameplay recording:  godot --write-movie out.avi --fixed-fps 24 --quit-after 288 res://tests/record.tscn
## Twelve seconds of the harbour in the morning at x30 speed with a slow orbit.

var village: Village
var t := 0.0

func _ready() -> void:
	GameClock.reset(6.0)
	village = Village.new()
	add_child(village)
	village.sim.auto = false
	village.sim.advance(150.0 * 60.0 / 60.0 * 60.0)          # to 08:30
	village.weather.force("clear")
	village.sim.auto = true
	village.sim.time_scale = 30.0
	var rig = village.camera_rig
	rig.set_process_unhandled_input(false)
	rig.goal_target = Vector3(5, 2, 11)
	rig.goal_dist = 46.0
	rig.goal_pitch = deg_to_rad(-24.0)
	rig.snap()

func _process(dt: float) -> void:
	t += dt
	village.camera_rig.goal_yaw = deg_to_rad(28.0 + t * 2.2)
	village.camera_rig.goal_dist = 46.0 - t * 0.9
	village.hud.hidden_ui = t < 6.0
	village.hud.journal_mode = 2 if t >= 6.0 else 0
