class_name FishingSpot
extends Interactable
## A place on a pier or the shore where villagers fish with a hand line.
## A bite is rolled every CHECK_MIN game minutes per angler (seeded RNG).

const CHECK_MIN := 12.0
const BITE_CHANCE := 0.38

var rng := RandomNumberGenerator.new()
var catches: int = 0
var _acc: Dictionary = {}

func _ready() -> void:
	kind = "fishing"

func _on_begin_use(who, _action: String) -> void:
	_acc[who] = 0.0

func _on_end_use(who) -> void:
	_acc.erase(who)

func tick(minutes: float) -> void:
	for who in users:
		_acc[who] = _acc.get(who, 0.0) + minutes
		while _acc[who] >= CHECK_MIN:
			_acc[who] -= CHECK_MIN
			if rng.randf() < BITE_CHANCE:
				catches += 1
				if who.has_method("on_catch"):
					who.on_catch(self)

func slot_offset(who) -> Vector3:
	var i := slot_index(who)
	var side := facing.cross(Vector3.UP).normalized()
	return side * (float(i) - float(capacity - 1) * 0.5) * 1.1
