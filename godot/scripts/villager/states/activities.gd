## The concrete activity states. One small class each so new activities can be
## added without touching the villager. Every effect goes through the Ledger
## or the villager's needs - an animation alone never changes the world.

class SleepState extends UseObjectState:
	func _init(villager = null) -> void:
		super._init(villager)
		anim = "sleep"
	func act(minutes: float) -> bool:
		v.needs["energy"] = minf(100.0, v.needs["energy"] + 13.0 * minutes / 60.0)
		var h := GameClock.hour()
		var morning: bool = h >= 5.5 + v.wake_offset and h < 21.0
		var urgent: bool = (v.needs["hunger"] > 86.0 or v.needs["thirst"] > 90.0) and elapsed > 45.0
		if urgent:
			v.brain.cooldown["sleep"] = GameClock.total_minutes + 120.0
		return (v.needs["energy"] >= 96.0 and morning) or urgent
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
		if cs and cs.finish(v.world.ledger, v.hh):
			v.stats["meals_cooked"] += CookingStation.MEALS_PER_FISH

class EatState extends UseObjectState:
	const DURATION := 20.0
	var _ate: bool = false
	var out: bool = false
	func _init(villager = null) -> void:
		super._init(villager)
		anim = "eat"
	func enter(args: Dictionary) -> void:
		out = args.get("out", false)
		super.enter(args)
	func begin() -> void:
		if out:
			_ate = v.world.economy.buy_meal(v)
		else:
			_ate = v.world.ledger.consume(v.hh, "meal", 1, "eaten")
	func act(minutes: float) -> bool:
		if not _ate:
			return true
		v.needs["hunger"] = maxf(0.0, v.needs["hunger"] - 70.0 * minutes / DURATION)
		v.needs["thirst"] = maxf(0.0, v.needs["thirst"] - 30.0 * minutes / DURATION)
		return elapsed >= DURATION
	func finish() -> void:
		if _ate:
			v.stats["meals_eaten"] += 1
		else:
			v.brain.cooldown["eat_out" if out else "eat"] = GameClock.total_minutes + 30.0

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
		return caught >= target or elapsed > 200.0 or v.needs["hunger"] > 90.0 or v.needs["energy"] < 15.0 \
			or v.world.weather.unsafe_at_sea()
	func on_catch() -> void:
		caught += 1

class FishTripState extends UseObjectState:
	## A full boat trip: cast off, sail the lane, fish the ground, sail home,
	## unload and sell. Bad weather turns the boat round with whatever is aboard.
	var boat: Boat = null
	var _roll: float = 0.0
	var _fishing: float = 0.0
	var _unload: float = 0.0
	func _init(villager = null) -> void:
		super._init(villager)
		anim = "sit"
	func begin() -> void:
		boat = obj as Boat
		_roll = 0.0; _fishing = 0.0; _unload = 0.0
		v.at_sea = true
		boat.start_trip()
		v.stats["boat_trips"] += 1
	func tick(dt: float, minutes: float) -> void:
		if obj == null:
			return
		elapsed += minutes
		var w: Weather = v.world.weather
		match boat.boat_state:
			"outbound":
				if w.unsafe_at_sea():
					boat.aborted += 1
					v.note("storm: turning back")
					boat.turn_back()
				elif boat.sail(dt, w.boat_speed_factor()):
					boat.boat_state = "fishing"
					v.play("fish")
			"fishing":
				_fishing += minutes
				_roll += minutes
				var l: Ledger = v.world.ledger
				while _roll >= 10.0:
					_roll -= 10.0
					var room: int = boat.capacity_fish() - l.qty(boat.object_id, "fish")
					var n: int = mini(mini(1 + v.rng.randi() % 2, room), int(boat.ground["stock"]))
					if n > 0 and v.rng.randf() < 0.62 * boat.ground["richness"]:
						l.mint(boat.object_id, "fish", n, "boat_catch")
						boat.ground["stock"] -= n
						v.stats["fish_caught"] += n
				var full: bool = l.qty(boat.object_id, "fish") >= boat.capacity_fish()
				if full or _fishing > 170.0 or w.unsafe_at_sea() or v.needs["hunger"] > 88.0 or v.needs["energy"] < 14.0 or boat.ground["stock"] <= 0:
					if w.unsafe_at_sea():
						boat.aborted += 1
						v.note("storm: heading home with %d fish" % l.qty(boat.object_id, "fish"))
					boat.turn_back()
					v.play("sit")
			"inbound":
				if boat.sail(dt, w.boat_speed_factor()):
					boat.boat_state = "unloading"
					v.play("work")
			"unloading":
				_unload += minutes
				if _unload >= 15.0:
					v.world.economy.land_catch(v, boat)
					boat.moor()
					v.step_done()
					return
		v.global_position = boat.pos + Vector3(0, 0.45, 0)
	func exit() -> void:
		if boat and boat.boat_state != "moored":
			boat.moor()                      # interrupted: the boat is brought home, cargo stays aboard
		v.at_sea = false
		super.exit()

class WorkState extends UseObjectState:
	var duration: float = 90.0
	func _init(villager = null) -> void:
		super._init(villager)
		anim = "work"
	func enter(args: Dictionary) -> void:
		duration = args.get("minutes", 90.0)
		super.enter(args)
	func act(_minutes: float) -> bool:
		return elapsed >= duration or v.needs["hunger"] > 68.0 or v.needs["energy"] < 18.0 or v.needs["thirst"] > 80.0
	func finish() -> void:
		if elapsed >= duration * 0.6 and v.job != null:
			v.stats["work_blocks"] += 1
			v.world.economy.work_done(v, obj)

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
	func _init(villager = null) -> void:
		super._init(villager)
		anim = "idle"
	func act(_minutes: float) -> bool:
		return elapsed >= 6.0
	func finish() -> void:
		if v.world.economy.buy_fish(v) == 0:
			v.brain.cooldown["buy_food"] = GameClock.total_minutes + 60.0

class DrinkState extends UseObjectState:
	func _init(villager = null) -> void:
		super._init(villager)
		anim = "eat"
	func act(_minutes: float) -> bool:
		return elapsed >= 3.0
	func finish() -> void:
		v.needs["thirst"] = 0.0
		v.stats["drinks"] += 1

class WashState extends UseObjectState:
	func _init(villager = null) -> void:
		super._init(villager)
		anim = "cook"
	func act(_minutes: float) -> bool:
		return elapsed >= 8.0
	func finish() -> void:
		v.needs["hygiene"] = 100.0
		v.stats["washes"] += 1
