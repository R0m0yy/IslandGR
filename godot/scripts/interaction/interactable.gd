class_name Interactable
extends Node3D
## Base class for everything a villager can use. Implements the contract in
## ARCHITECTURE.md: free -> reserved -> in_use -> free, with timeout release.
## Subclasses add their own object state (door open, stove lit, ...).

signal state_changed(obj: Interactable, state: String)
signal used(obj: Interactable, by: Node, action: String)

@export var object_id: String = ""
@export var kind: String = ""              # anchor type from the layout (bed, stove, ...)
@export var pose: String = "stand"         # stand | sit | lie
@export var capacity: int = 1

var building = null                        # Building or null (outdoor objects)
var nav_node: String = ""                  # walk-graph node where the user stands
var use_position: Vector3 = Vector3.ZERO   # world position while using
var facing: Vector3 = Vector3.FORWARD      # world direction while using
var state: String = "free"
var users: Array = []
var reservations: Dictionary = {}          # villager -> game-minute timestamp
const RESERVE_TIMEOUT_MIN := 240.0

func is_available(who = null) -> bool:
	_expire()
	if who != null and (reservations.has(who) or users.has(who)):
		return true
	return users.size() + reservations.size() < capacity

func reserve(who) -> bool:
	if not is_available(who):
		return false
	if not users.has(who):
		reservations[who] = GameClock.total_minutes
	_refresh()
	return true

func release(who) -> void:
	reservations.erase(who)
	if users.has(who):
		users.erase(who)
		_on_end_use(who)
	_refresh()

func begin_use(who, action: String = "") -> bool:
	if not is_available(who):
		return false
	reservations.erase(who)
	if not users.has(who):
		users.append(who)
	_on_begin_use(who, action)
	used.emit(self, who, action)
	_refresh()
	return true

func slot_index(who) -> int:
	return maxi(users.find(who), 0)

func tick(_minutes: float) -> void:
	pass

func _on_begin_use(_who, _action: String) -> void:
	pass

func _on_end_use(_who) -> void:
	pass

func _expire() -> void:
	for who in reservations.keys():
		if not is_instance_valid(who) or GameClock.total_minutes - reservations[who] > RESERVE_TIMEOUT_MIN:
			reservations.erase(who)

func _refresh() -> void:
	var s := "free"
	if not users.is_empty():
		s = "in_use"
	elif not reservations.is_empty():
		s = "reserved"
	_set_state(s)

func _set_state(s: String) -> void:
	if s != state:
		state = s
		state_changed.emit(self, s)
