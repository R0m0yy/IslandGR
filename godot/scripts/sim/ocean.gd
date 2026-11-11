class_name Ocean
extends RefCounted
## One wave model for looks and for physics. The sea shader evaluates the same
## sum of sines with the same numbers, driven by the same clock (`time`), so a
## boat sits on the surface the player sees. Sea state follows the wind; the
## tide moves the whole surface slowly.

const SCALE := 0.22
const SPEED := 0.55
const TIDE_RANGE := 0.22            # metres either side of mean sea level
const TIDE_PERIOD_MIN := 745.0      # ~12 h 25 min

var time: float = 0.0               # seconds of wave time (advances with the simulation)
var wind: float = 0.15

func advance(dt: float, wind_now: float) -> void:
	time += dt
	wind = wind_now

func amplitude() -> float:
	return 0.10 + 0.42 * wind

func tide() -> float:
	return TIDE_RANGE * sin(TAU * GameClock.total_minutes / TIDE_PERIOD_MIN)

func wave(x: float, z: float) -> float:
	var t := time * SPEED
	return amplitude() * (sin(x * SCALE + t) * 0.5 + sin(z * SCALE * 1.3 - t * 0.8) * 0.35 + sin((x + z) * SCALE * 2.1 + t * 1.7) * 0.15)

func height(x: float, z: float) -> float:
	return tide() + wave(x, z)

func slope(x: float, z: float) -> Vector2:
	## d(height)/dx, d(height)/dz - what a hull pitches and rolls to.
	var e := 0.6
	return Vector2((wave(x + e, z) - wave(x - e, z)) / (2.0 * e), (wave(x, z + e) - wave(x, z - e)) / (2.0 * e))

func roughness() -> float:
	## 0 calm .. 1 storm sea; used by boats and fishing.
	return clampf((amplitude() - 0.10) / 0.42, 0.0, 1.0)
