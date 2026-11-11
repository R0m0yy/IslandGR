class_name Simulation
extends Node
## Fixed-step driver. Everything that changes the world is advanced from
## step(), so the headless tests can run days of village life in seconds by
## calling advance() directly, with no rendering and no frame timing.

const STEP := 0.1                   # real seconds per simulation step

var village = null
var time_scale: float = 1.0
var auto: bool = true
var steps: int = 0
var _acc: float = 0.0
var _light_t: float = 0.0

func _physics_process(delta: float) -> void:
	if not auto or village == null:
		return
	_acc += delta * time_scale
	var n := 0
	while _acc >= STEP and n < 400:
		step(STEP)
		_acc -= STEP
		n += 1

func advance(seconds: float) -> void:
	var n := int(round(seconds / STEP))
	for i in n:
		step(STEP)

func step(dt: float) -> void:
	var minutes := GameClock.advance(dt)
	for o in village.interactables:
		o.tick(minutes)
	for d in village.doors:
		d.process_door(dt)
	for v in village.villagers:
		v.tick(dt, minutes)
	steps += 1
	_light_t -= dt
	if _light_t <= 0.0:
		_light_t = 1.0
		_update_lights()

func _update_lights() -> void:
	var dark := GameClock.daylight() < 0.3
	var awake := {}
	for v in village.villagers:
		var b: String = v.inside_building()
		if b != "" and v.fsm.current_name != "sleep":
			awake[b] = true
	for id in village.buildings:
		village.buildings[id].set_lights(dark and awake.has(id))
	village.set_street_lamps(dark)
