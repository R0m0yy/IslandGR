class_name VillagerState
extends RefCounted
## Base state. `anim` is the animation the state asks the animator to play;
## the names are the reusable animation contract (see villager_animator.gd).

var state_name: String = ""
var machine: StateMachine = null
var v = null                        # Villager
var anim: String = "idle"

func _init(villager = null) -> void:
	v = villager

func enter(_args: Dictionary) -> void:
	v.play(anim)

func exit() -> void:
	pass

func tick(_dt: float, _minutes: float) -> void:
	pass
