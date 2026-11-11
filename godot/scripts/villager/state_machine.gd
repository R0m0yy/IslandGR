class_name StateMachine
extends RefCounted
## Small reusable finite state machine. States are VillagerState objects
## registered by name; the owner drives it with tick().

signal changed(from: String, to: String)

var states: Dictionary = {}
var current: VillagerState = null
var current_name: String = ""
var history: Array = []

func add(state_name: String, st: VillagerState) -> void:
	st.state_name = state_name
	st.machine = self
	states[state_name] = st

func change(state_name: String, args: Dictionary = {}) -> void:
	if not states.has(state_name):
		push_error("StateMachine: unknown state %s" % state_name)
		return
	var prev := current_name
	if current:
		current.exit()
	current = states[state_name]
	current_name = state_name
	history.append(state_name)
	if history.size() > 24:
		history.pop_front()
	current.enter(args)
	changed.emit(prev, state_name)

func tick(dt: float, minutes: float) -> void:
	if current:
		current.tick(dt, minutes)
