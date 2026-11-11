class_name OpenDoorState
extends VillagerState
## Stops at a doorway, opens the door, waits for the swing, walks through.

var door: Door = null
var _phase: String = "reach"
var _t: float = 0.0

func _init(villager = null) -> void:
	super._init(villager)
	anim = "open_door"

func enter(args: Dictionary) -> void:
	door = args.get("door")
	_phase = "reach"
	_t = 0.0
	v.play("open_door")
	if door:
		door.request_open(v)
		v.stats["doors_opened"] += 1

func tick(dt: float, _minutes: float) -> void:
	_t += dt
	if _phase == "reach":
		if door:
			door.request_open(v)
		if door == null or door.is_open() or _t > 3.0:
			_phase = "through"
			v.play("walk")
	else:
		if door:
			door.request_open(v)          # hold it while passing
		if v.advance_segment(dt * 1.3):
			v.next_segment()
