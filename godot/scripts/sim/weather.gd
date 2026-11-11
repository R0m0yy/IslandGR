class_name Weather
extends RefCounted
## Weather state machine. Changes on the hour with a seeded RNG, eases between
## states, and exposes numbers the rest of the game reads: boats will not sail
## (and turn back) in a storm, villagers avoid outdoor leisure in rain.

const STATES := ["clear", "cloudy", "rain", "storm"]
const NEXT := {   # hourly transition weights
	"clear": {"clear": 0.90, "cloudy": 0.10},
	"cloudy": {"clear": 0.22, "cloudy": 0.60, "rain": 0.18},
	"rain": {"cloudy": 0.30, "rain": 0.55, "storm": 0.15},
	"storm": {"rain": 0.45, "storm": 0.55},
}
const TARGET := {"clear": [0.05, 0.0, 0.15], "cloudy": [0.6, 0.0, 0.3], "rain": [0.85, 0.6, 0.5], "storm": [1.0, 1.0, 1.0]}

signal changed(state: String)

var state: String = "clear"
var cloud: float = 0.05
var rain: float = 0.0
var wind: float = 0.15           # also the sea state 0..1
var rng := RandomNumberGenerator.new()
var hours_in: Dictionary = {"clear": 0, "cloudy": 0, "rain": 0, "storm": 0}
var _hour: int = -1

func _init(seed_: int = 7) -> void:
	rng.seed = seed_

func tick(minutes: float) -> void:
	var h := int(GameClock.total_minutes / 60.0)
	if h != _hour:
		_hour = h
		hours_in[state] += 1
		var r := rng.randf()
		var accu := 0.0
		for k in NEXT[state]:
			accu += NEXT[state][k]
			if r <= accu:
				if k != state:
					state = k
					changed.emit(state)
				break
	var t: Array = TARGET[state]
	var k2 := clampf(minutes / 40.0, 0.0, 1.0)
	cloud = lerpf(cloud, t[0], k2)
	rain = lerpf(rain, t[1], k2)
	wind = lerpf(wind, t[2], k2)

func force(s: String) -> void:
	state = s
	changed.emit(s)

func unsafe_at_sea() -> bool:
	return state == "storm"

func outdoor_factor() -> float:
	## Multiplier on the appeal of outdoor leisure and shore fishing.
	return {"clear": 1.0, "cloudy": 0.9, "rain": 0.35, "storm": 0.0}[state]

func boat_speed_factor() -> float:
	return lerpf(1.0, 0.55, wind)

func to_dict() -> Dictionary:
	return {"state": state, "cloud": cloud, "rain": rain, "wind": wind, "rng": rng.state, "seed": rng.seed, "hours_in": hours_in, "hour": _hour}

func from_dict(d: Dictionary) -> void:
	state = d["state"]; cloud = d["cloud"]; rain = d["rain"]; wind = d["wind"]
	rng.seed = int(d["seed"]); rng.state = int(d["rng"])
	_hour = int(d["hour"])
	for k in d["hours_in"]:
		hours_in[k] = int(d["hours_in"][k])
