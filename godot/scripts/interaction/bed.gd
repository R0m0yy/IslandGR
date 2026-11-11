class_name Bed
extends Interactable
## One sleeper. `owner_id` is the villager the bed is assigned to; others may
## only use it if it has no owner.

var owner_id: String = ""

func is_available(who = null) -> bool:
	if owner_id != "" and who != null and who.villager_id != owner_id:
		return false
	return super.is_available(who)
