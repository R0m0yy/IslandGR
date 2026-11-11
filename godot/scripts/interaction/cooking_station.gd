class_name CookingStation
extends Interactable
## Stove. Object state: cold -> lit -> cooking -> cold (embers fade).
## Cooking turns one raw fish from the household pantry into meals.

const HEAT_MIN := 5.0              # game minutes from lighting to cooking heat
const COOK_MIN := 25.0
const MEALS_PER_FISH := 3

var stove_state: String = "cold"
var progress: float = 0.0          # game minutes into the current phase
var light: OmniLight3D = null
var meals_cooked: int = 0
var _cook = null

func _on_begin_use(who, _action: String) -> void:
	_cook = who
	stove_state = "lit"
	progress = 0.0
	_update_light()
	state_changed.emit(self, stove_state)

func _on_end_use(_who) -> void:
	_cook = null
	stove_state = "cold"
	_update_light()
	state_changed.emit(self, stove_state)

func tick(minutes: float) -> void:
	if stove_state == "cold":
		return
	progress += minutes
	if stove_state == "lit" and progress >= HEAT_MIN:
		stove_state = "cooking"
		progress = 0.0
		state_changed.emit(self, stove_state)

func is_done() -> bool:
	return stove_state == "cooking" and progress >= COOK_MIN

func finish(ledger: Ledger, hh: String) -> bool:
	## Called by the cook when is_done(). One raw fish leaves the pantry, meals enter it.
	if not ledger.consume(hh, "fish", 1, "cooked"):
		return false
	ledger.mint(hh, "meal", MEALS_PER_FISH, "cooked")
	meals_cooked += MEALS_PER_FISH
	return true

func _update_light() -> void:
	if light:
		light.visible = stove_state != "cold"
