class_name UseObjectState
extends VillagerState
## Base for every "use an object" state: reserve -> align -> act -> apply
## effects -> release (VILLAGER_AI.md "Execution"). Subclasses override
## begin(), act() and finish().

var obj: Interactable = null
var elapsed: float = 0.0            # game minutes in this state

func enter(args: Dictionary) -> void:
	obj = args.get("obj")
	elapsed = 0.0
	if obj == null or not obj.begin_use(v, state_name):
		v.stats["failed_uses"] += 1
		v.fail_plan("object unavailable: %s" % state_name)
		return
	v.snap_to(obj.use_position + _offset(), obj.facing, obj.pose)
	v.play(anim)
	begin()

func _offset() -> Vector3:
	return Vector3.ZERO

func exit() -> void:
	if obj:
		obj.release(v)
	obj = null
	v.unsnap()

func tick(_dt: float, minutes: float) -> void:
	if obj == null:
		return
	elapsed += minutes
	if act(minutes):
		finish()
		v.step_done()

func begin() -> void:
	pass

func act(_minutes: float) -> bool:
	return true

func finish() -> void:
	pass
