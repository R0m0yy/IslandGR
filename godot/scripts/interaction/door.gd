class_name Door
extends Interactable
## Hinged door. The leaf is the `DOOR_main` node of the building GLB, whose
## pivot sits on the hinge axis. States: closed -> opening -> open -> closing.
## A villager calls request_open() and walks through once is_open() is true;
## the door closes by itself when the doorway has been clear for a moment.

const OPEN_TIME := 0.55            # real seconds for the swing
const HOLD_TIME := 2.2             # seconds the door stays open after the last request

var leaf: Node3D = null
var open_angle: float = deg_to_rad(100.0)
var door_state: String = "closed"
var _t: float = 0.0                # 0 closed .. 1 open
var _hold: float = 0.0
var _closed_basis: Basis = Basis.IDENTITY
var open_count: int = 0

func setup(leaf_node: Node3D, open_deg: float) -> void:
	leaf = leaf_node
	open_angle = deg_to_rad(open_deg)
	if leaf:
		_closed_basis = leaf.transform.basis
	kind = "door"
	capacity = 99

func request_open(_who = null) -> void:
	_hold = HOLD_TIME
	if door_state == "closed" or door_state == "closing":
		door_state = "opening"
		open_count += 1
		_emit()

func is_open() -> bool:
	return door_state == "open"

func process_door(dt: float) -> void:
	match door_state:
		"opening":
			_t = minf(1.0, _t + dt / OPEN_TIME)
			if _t >= 1.0:
				door_state = "open"
				_emit()
		"open":
			_hold -= dt
			if _hold <= 0.0:
				door_state = "closing"
				_emit()
		"closing":
			_t = maxf(0.0, _t - dt / OPEN_TIME)
			if _t <= 0.0:
				door_state = "closed"
				_emit()
	if leaf:
		var k := _t * _t * (3.0 - 2.0 * _t)
		leaf.transform.basis = _closed_basis * Basis(Vector3.UP, open_angle * k)

func _emit() -> void:
	if building:
		building.state["door_open"] = door_state != "closed"
	state_changed.emit(self, door_state)
