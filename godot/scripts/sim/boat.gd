class_name Boat
extends Interactable
## A fishing boat. Logical state lives here; `visual` is the node from
## boats.glb that is moved to match. Cargo is a Ledger account (the boat's id).
## States: moored -> outbound -> fishing -> inbound -> unloading -> moored.

const SPEED := 3.4                 # m/s in calm water
const CAPACITY := {"skiff": 10, "fishing_boat": 22}
const TRIP_WEAR := 0.05
const REPAIR_BELOW := 0.6
const REPAIR_COST := 12

var boat_kind: String = "skiff"
var boat_state: String = "moored"
var condition: float = 1.0
var visual: Node3D = null
var home_pos: Vector3
var home_yaw: float = 0.0
var route: Array = []              # world points from the mooring to the ground
var ground: Dictionary = {}        # fishing ground record (shared, has "stock")
var trips: int = 0
var landed: int = 0
var aborted: int = 0
var wear_extra: float = 0.0
var pos: Vector3
var _targets: Array = []
var _passed: int = 0
var _dir: int = 1
var _bob: float = 0.0

func capacity_fish() -> int:
	return CAPACITY.get(boat_kind, 10)

func place(p: Vector3, heading: Vector3 = Vector3.ZERO) -> void:
	pos = p
	if visual:
		visual.global_position = Vector3(p.x, visual.global_position.y, p.z)
		if heading.length_squared() > 1e-6:
			visual.rotation.y = atan2(-heading.z, heading.x)       # bow is +x in the model

func sail(dt: float, speed_factor: float) -> bool:
	## Advances toward the next waypoint; true when the last one is reached.
	if _targets.is_empty():
		return true
	var tgt: Vector3 = _targets[0]
	var d := tgt - pos
	d.y = 0.0
	var step := SPEED * speed_factor * dt
	if d.length() <= step:
		place(tgt, d)
		_targets.pop_front()
		_passed += _dir
		return _targets.is_empty()
	place(pos + d.normalized() * step, d)
	return false

func start_trip() -> void:
	boat_state = "outbound"
	_targets = route.slice(1)
	_passed = 0
	_dir = 1
	trips += 1
	state_changed.emit(self, boat_state)

func turn_back() -> void:
	boat_state = "inbound"
	_targets = []
	for i in range(mini(_passed, route.size() - 1), -1, -1):
		_targets.append(route[i])
	_dir = -1
	state_changed.emit(self, boat_state)

func moor() -> void:
	boat_state = "moored"
	_targets = []
	_passed = 0
	pos = home_pos
	if visual:
		visual.global_position = Vector3(home_pos.x, visual.global_position.y, home_pos.z)
		visual.rotation.y = home_yaw
	condition = maxf(0.0, condition - TRIP_WEAR - wear_extra)
	wear_extra = 0.0
	state_changed.emit(self, boat_state)
