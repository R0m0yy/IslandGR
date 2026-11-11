class_name IdleState
extends VillagerState
## Stands for `seconds`, then asks the villager for its next step.

var _left: float = 0.0

func enter(args: Dictionary) -> void:
	_left = args.get("seconds", 1.0)
	v.play(args.get("anim", "idle"))

func tick(dt: float, _minutes: float) -> void:
	_left -= dt
	if _left <= 0.0:
		v.step_done()
