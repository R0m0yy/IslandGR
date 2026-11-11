class_name Bed
extends Interactable
## One sleeper, plus small children of the owner who share it until a bed of
## their own comes free. `owner_id` is the villager the bed is assigned to.

var owner_id: String = ""
var co_sleepers: Array = []          # ids of the owner's young children

func is_available(who = null) -> bool:
	if who != null and co_sleepers.has(who.villager_id):
		return true
	if owner_id != "" and who != null and who.villager_id != owner_id:
		return false
	return super.is_available(who)

func begin_use(who, action: String = "") -> bool:
	if who != null and co_sleepers.has(who.villager_id):
		if not users.has(who):
			users.append(who)
		_refresh()
		return true
	return super.begin_use(who, action)
