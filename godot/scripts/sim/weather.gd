class_name Weather
extends RefCounted
## Weather state machine. Changes on the hour with a seeded RNG, eases between
## states, and exposes numbers the rest of the game reads: boats will not sail
## (and turn back) in a storm, villagers avoid outdoor leisure in rain.

const STATES := ["clear", "cloudy", "light_rain", "heavy_rain", "storm"]
const NEXT := {   # hourly transition weights
	"clear": {"clear": 0.90, "cloudy": 0.10},
	"cloudy": {"clear": 0.22, "cloudy": 0.58, "light_rain": 0.20},
	"light_rain": {"cloudy": 0.30, "light_rain": 0.45, "heavy_rain": 0.25},
	"heavy_rain": {"light_rain": 0.35, "heavy_rain": 0.45, "storm": 0.20},
	"storm": {"heavy_rain": 0.50, "storm": 0.50},
}
const TARGET := {"clear": [0.05, 0.0, 0.15], "cloudy": [0.6, 0.0, 0.3], "light_rain": [0.8, 0.35, 0.38], "heavy_rain": [0.93, 0.75, 0.62], "storm": [1.0, 1.0, 1.0]}

signal changed(state: String)

var state: String = "clear"
var cloud: float = 0.05
var rain: float = 0.0
var wind: float = 0.15           # also the sea state 0..1
var rng := RandomNumberGenerator.new()
var hours_in: Dictionary = {"clear": 0, "cloudy": 0, "light_rain": 0, "heavy_rain": 0, "storm": 0}
var _hour: int = -1
var locked: bool = false
var _rolled: int = -1            # scenarios / tests: hold the current state

func _init(seed_: int = 7) -> void:
	rng.seed = seed_

func tick(minutes: float) -> void:
	var h := int(GameClock.total_minutes / 60.0)
	if h != _hour:
		_hour = h
		hours_in[state] += 1
	if h == _hour and not locked and _rolled != h:
		_rolled = h
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
	return {"clear": 1.0, "cloudy": 0.9, "light_rain": 0.6, "heavy_rain": 0.15, "storm": 0.0}[state]

func shelter_needed() -> bool:
	return state == "heavy_rain" or state == "storm"

func storm_risk(hours: int = 4) -> float:
	## True chance of a storm within the next `hours`, from the transition table.
	var dist := {state: 1.0}
	var hit := 0.0
	for h in hours:
		var nd := {}
		for a in dist:
			for b in NEXT[a]:
				var pr: float = dist[a] * NEXT[a][b]
				if b == "storm":
					hit += pr                    # absorbed: a storm happened
				else:
					nd[b] = nd.get(b, 0.0) + pr
		dist = nd
	return 1.0 if state == "storm" else hit

func forecast(skill: float, r: RandomNumberGenerator) -> float:
	## What one resident reads in the sky: the true risk blurred by inexperience.
	return clampf(storm_risk() + r.randf_range(-0.22, 0.22) * (1.0 - skill), 0.0, 1.0)

func boat_speed_factor() -> float:
	return lerpf(1.0, 0.55, wind)

func to_dict() -> Dictionary:
	return {"state": state, "cloud": cloud, "rain": rain, "wind": wind, "rng": rng.state, "seed": rng.seed, "hours_in": hours_in, "hour": _hour}

func from_dict(d: Dictionary) -> void:
	state = d["state"] if STATES.has(d["state"]) else "light_rain"; cloud = d["cloud"]; rain = d["rain"]; wind = d["wind"]
	rng.seed = int(d["seed"]); rng.state = int(d["rng"])
	_hour = int(d["hour"])
	_rolled = _hour
	for k in d["hours_in"]:
		if hours_in.has(k):
			hours_in[k] = int(d["hours_in"][k])
