class_name LocomotionState
extends VillagerState
## Shared by walk / climb_stairs / climb_ladder / cross_bridge: advances the
## villager along the current walk-graph link at `speed` m/s.

var speed: float = 1.5

func _init(villager = null, anim_name: String = "walk", metres_per_second: float = 1.5) -> void:
	super._init(villager)
	anim = anim_name
	speed = metres_per_second

func tick(dt: float, _minutes: float) -> void:
	if v.advance_segment(dt * speed):
		v.next_segment()
