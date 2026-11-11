extends Node
## Autoload. World time. One real second = `minutes_per_second` game minutes
## (scaled by `speed`). Simulation code only ever asks the clock; it never
## reads the OS time, so a run is reproducible when stepped with advance().

signal hour_changed(hour: int)
signal day_changed(day: int)

var minutes_per_second: float = 1.0
var speed: float = 1.0
var paused: bool = false
var total_minutes: float = 6.0 * 60.0      # start at 06:00 on day 0

func advance(real_dt: float) -> float:
	## Moves the clock; returns elapsed game minutes.
	if paused:
		return 0.0
	var before_h := int(total_minutes / 60.0)
	var dm := real_dt * minutes_per_second * speed
	total_minutes += dm
	var after_h := int(total_minutes / 60.0)
	if after_h != before_h:
		hour_changed.emit(after_h % 24)
		if after_h / 24 != before_h / 24:
			day_changed.emit(after_h / 24)
	return dm

func hour() -> float:
	return fmod(total_minutes / 60.0, 24.0)

func day() -> int:
	return int(total_minutes / 1440.0)

func is_night() -> bool:
	var h := hour()
	return h >= 19.5 or h < 5.5

func daylight() -> float:
	## 0 at night, 1 at midday, smooth through dawn and dusk.
	var h := hour()
	return clampf(sin((h - 5.5) / 14.0 * PI) * 1.6, 0.0, 1.0) if h > 5.5 and h < 19.5 else 0.0

func text() -> String:
	var h := int(hour())
	var m := int(fmod(total_minutes, 60.0))
	return "Day %d  %02d:%02d" % [day() + 1, h, m]

func reset(start_hour: float = 6.0) -> void:
	total_minutes = start_hour * 60.0
	paused = false
	speed = 1.0
