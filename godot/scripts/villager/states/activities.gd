## The concrete activity states. One small class each so new activities can be
## added without touching the villager.

class SleepState extends UseObjectState:
	func _init(villager = null) -> void:
		super._init(villager)
		anim = "sleep"
	func act(minutes: float) -> bool:
		v.needs["energy"] = minf(100.0, v.needs["energy"] + 13.0 * minutes / 60.0)
		var h := GameClock.hour()
		var morning := h >= 5.5 and h < 21.0
		var starving: bool = v.needs["hunger"] > 86.0 and elapsed > 45.0
		if starving:
			v.brain.cooldown["sleep"] = GameClock.total_minutes + 120.0
		return (v.needs["energy"] >= 96.0 and morning) or starving
	func finish() -> void:
		if elapsed >= 120.0:
			v.stats["sleeps"] += 1

class CookState extends UseObjectState:
	func _init(villager = null) -> void:
		super._init(villager)
		anim = "cook"
	func act(_minutes: float) -> bool:
		var cs := obj as CookingStation
		return cs == null or cs.is_done() or elapsed > 90.0
	func finish() -> void:
		var cs := obj as CookingStation
		if cs and cs.finish(v.household):
			v.stats["meals_cooked"] += CookingStation.MEALS_PER_FISH

class EatState extends UseObjectState:
	const DURATION := 20.0
	var _ate: bool = false
	func _init(villager = null) -> void:
		super._init(villager)
		anim = "eat"
	func begin() -> void:
		_ate = false
		if v.household.get("meals", 0) > 0:
			v.household["meals"] -= 1
			_ate = true
	func act(minutes: float) -> bool:
		if not _ate:
			return true
		v.needs["hunger"] = maxf(0.0, v.needs["hunger"] - 70.0 * minutes / DURATION)
		return elapsed >= DURATION
	func finish() -> void:
		if _ate:
			v.stats["meals_eaten"] += 1

class FishState extends UseObjectState:
	var target: int = 2
	var caught: int = 0
	func _init(villager = null) -> void:
		super._init(villager)
		anim = "fish"
	func enter(args: Dictionary) -> void:
		target = args.get("target", 2)
		caught = 0
		super.enter(args)
	func _offset() -> Vector3:
		var fs := obj as FishingSpot
		return fs.slot_offset(v) if fs else Vector3.ZERO
	func act(_minutes: float) -> bool:
		return caught >= target or elapsed > 200.0 or v.needs["hunger"] > 90.0 or v.needs["energy"] < 15.0
	func on_catch() -> void:
		caught += 1

class WorkState extends UseObjectState:
	var duration: float = 90.0
	func _init(villager = null) -> void:
		super._init(villager)
		anim = "work"
	func enter(args: Dictionary) -> void:
		duration = args.get("minutes", 90.0)
		super.enter(args)
	func act(_minutes: float) -> bool:
		return elapsed >= duration or v.needs["hunger"] > 68.0 or v.needs["energy"] < 18.0
	func finish() -> void:
		v.stats["work_blocks"] += 1

class SitState extends UseObjectState:
	var duration: float = 30.0
	func _init(villager = null) -> void:
		super._init(villager)
		anim = "sit"
	func enter(args: Dictionary) -> void:
		duration = args.get("minutes", 30.0)
		super.enter(args)
	func act(_minutes: float) -> bool:
		return elapsed >= duration

class ShopState extends UseObjectState:
	## Buys raw fish at the market. Stock only ever moves between the market
	## and a household pantry; nothing is created here.
	func _init(villager = null) -> void:
		super._init(villager)
		anim = "idle"
	func act(_minutes: float) -> bool:
		return elapsed >= 6.0
	func finish() -> void:
		var n: int = mini(2, v.world.market_stock)
		if n > 0:
			v.world.market_stock -= n
			v.household["raw_fish"] = v.household.get("raw_fish", 0) + n
			v.stats["fish_bought"] += n
