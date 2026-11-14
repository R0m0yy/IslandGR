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
var _last_us: int = 0
var _light_t: float = 0.0

func _process(delta: float) -> void:
	## Driven by rendered frames, not physics ticks: Godot caps physics catch-up per frame, so on a
	## slow device (a few frames per second) the village clock used to crawl at a fraction of its
	## speed. Up to one second of real time is caught up per frame.
	if not auto or village == null:
		return
	# wall-clock time, not `delta`: the engine clamps delta on slow frames (about 0.13 s), which is
	# exactly when the catch-up is needed
	var now := Time.get_ticks_usec()
	var real: float = delta if _last_us == 0 else (now - _last_us) / 1e6
	_last_us = now
	_acc += clampf(real, 0.0, 1.0) * time_scale
	var n := 0
	while _acc >= STEP and n < 400:
		step(STEP)
		_acc -= STEP
		n += 1
	if n >= 400:
		_acc = 0.0

func advance(seconds: float) -> void:
	var n := int(round(seconds / STEP))
	for i in n:
		step(STEP)

func step(dt: float) -> void:
	var minutes := GameClock.advance(dt)
	village.weather.tick(minutes)
	village.economy.daily(GameClock.day())
	village.society.tick(minutes)
	# waves run on real seconds (not sped up with the simulation); the tide follows game time
	village.ocean.advance(dt / maxf(1.0, time_scale) if auto else dt, village.weather.wind)
	village.ecosystem.tick(dt, minutes)
	for o in village.interactables:
		o.tick(minutes)
	for d in village.doors:
		d.process_door(dt)
	for v in village.villagers.duplicate():
		if is_instance_valid(v):
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
