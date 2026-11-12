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
	var _caught: int = 0
	var _species := {}
	var _stood_down: bool = false
	func begin() -> void:
		boat = obj as Boat
		_roll = 0.0; _fishing = 0.0; _unload = 0.0; _caught = 0; _species = {}
		_stood_down = false
		# a last look at the sky at the mooring: the weather may have turned on the walk down
		if v.world.weather.unsafe_at_sea():
			_stood_down = true
			v.stats["stayed_ashore"] += 1
			v.note("reached the boat in a storm: not casting off")
			v.world.journal.add("fishing", [v.villager_id], "%s got down to %s, saw the sea and did not cast off." % [v.display_name, boat.object_id], "storm broke while walking to the harbour")
			return
		v.world.ledger.consume(v.hh, "bait", 1, "used_at_sea")       # gear and bait go aboard
		v.at_sea = true
		boat.crew = v
		v.play("steer" if boat.engine else "row")
		boat.start_trip()
		v.stats["boat_trips"] += 1
	func tick(dt: float, minutes: float) -> void:
		if obj == null:
			return
		if _stood_down:
			v.brain.cooldown["boat_trip"] = GameClock.total_minutes + 60.0
			v.step_done()
			return
		elapsed += minutes
		var w: Weather = v.world.weather
		var eco: Ecosystem = v.world.ecosystem
		var gpos: Vector3 = boat.ground["pos"]
		match boat.boat_state:
			"outbound":
				if w.unsafe_at_sea():
					boat.aborted += 1
					v.note("storm: turning back")
					v.remember("storm", "caught by a storm on the way out and turned back", -5.0)
					v.world.journal.add("fishing", [v.villager_id], "%s turned %s back as the storm broke." % [v.display_name, boat.object_id], "storm at sea", true, boat.pos)
					boat.turn_back()
				elif boat.sail(dt, w.boat_speed_factor()):
					boat.boat_state = "fishing"
					v.play("cast")
			"fishing":
				_fishing += minutes
				_roll += minutes
				v.play("cast" if int(_fishing / 25.0) % 2 == 0 else "haul_net")      # line, then the net, in turns
				var l: Ledger = v.world.ledger
				var bio: float = eco.biomass_near(gpos)
				while _roll >= 10.0:
					_roll -= 10.0
					var room: int = boat.capacity_fish() - l.qty(boat.object_id, "fish")
					# the catch depends on the fish actually there, the hand on the line, and the sea
					var chance: float = clampf(bio / 80.0, 0.05, 1.0) * (0.55 + 0.7 * v.skills["fishing"]) * (1.0 - 0.45 * v.world.ocean.roughness())
					if room > 0 and v.rng.randf() < chance:
						var got: Dictionary = eco.take_fish(gpos, mini(1 + v.rng.randi() % 2, room))
						var n := 0
						for sp in got:
							n += got[sp]
							_species[sp] = int(_species.get(sp, 0)) + got[sp]
						if n > 0:
							l.mint(boat.object_id, "fish", n, "boat_catch")
							_caught += n
							v.stats["fish_caught"] += n
							v.skills["fishing"] = minf(1.0, v.skills["fishing"] + 0.003 * n)
				var full: bool = l.qty(boat.object_id, "fish") >= boat.capacity_fish()
				var patience: float = 170.0 + (40.0 if v.ambition == "sea" else 0.0)
				var barren: bool = _fishing > 70.0 and _caught == 0
				if full or _fishing > patience or barren or w.unsafe_at_sea() or v.needs["hunger"] > 88.0 or v.needs["energy"] < 14.0:
					if w.unsafe_at_sea():
						boat.aborted += 1
						v.note("storm: heading home with %d fish" % l.qty(boat.object_id, "fish"))
						v.remember("storm", "ran for harbour ahead of a storm", -3.0)
					boat.turn_back()
					v.play("steer" if boat.engine else "row")
			"inbound":
				if boat.sail(dt, w.boat_speed_factor()):
					boat.boat_state = "unloading"
					v.play("carry")
					if v.animator:
						v.animator.show_prop("crate", true, 12.0)
			"unloading":
				_unload += minutes
				if _unload >= 15.0:
					var before: int = v.world.ledger.money(v.hh)
					var aboard: int = v.world.ledger.qty(boat.object_id, "fish")
					v.world.economy.land_catch(v, boat)
					var earned: int = v.world.ledger.money(v.hh) - before
					if boat.wear_extra > 0.0:
						v.remember("sea", "rough water knocked the boat about", -2.0)
					boat.moor()
					if _caught == 0:
						v.stats["empty_trips"] += 1
						v.remember("fishing", "came home with an empty boat", -4.0)
						v.world.journal.add("fishing", [v.villager_id], "%s came home with an empty boat." % v.display_name, "few fish on the ground (%d near %s)" % [int(eco.biomass_near(gpos)), boat.ground["name"]], false, boat.pos)
					elif _caught >= int(boat.capacity_fish() * 0.8):
						v.remember("fishing", "a full boat: %d fish" % _caught, 5.0)
						v.world.journal.add("fishing", [v.villager_id], "%s landed a full boat: %d fish (%s), %d sold for %d." % [v.display_name, _caught, str(_species), aboard, earned], "good shoals at %s" % boat.ground["name"], true, boat.pos)
					v.step_done()
					return
		if boat.boat_state in ["outbound", "inbound", "fishing"] and v.world.ocean.roughness() > 0.6:
			boat.wear_extra += 0.0004 * minutes                     # heavy seas strain the hull
		# aboard: rowers sit amidships facing the stern, the motor man sits by the outboard facing the bow
		var hd: float = boat.visual.rotation.y if boat.visual else 0.0
		var bow := Vector3(cos(hd), 0, -sin(hd))
		var seat := -0.15 if not boat.engine else -1.2
		if boat.boat_state == "fishing":
			seat = 0.4
		v.global_position = boat.pos + bow * seat + Vector3(0, 0.45 + v.world.ocean.height(boat.pos.x, boat.pos.z), 0)
		var face := -bow if (not boat.engine and boat.boat_state in ["outbound", "inbound"]) else bow
		if boat.boat_state == "fishing":
			face = bow.cross(Vector3.UP)            # over the side
		v.rotation.y = atan2(-face.x, -face.z)
	func exit() -> void:
		if boat and boat.boat_state != "moored" and not _stood_down:
			boat.moor()                      # interrupted: the boat is brought home, cargo stays aboard
		if boat and boat.crew == v:
			boat.crew = null
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
	var what: String = "fish"
	func _init(villager = null) -> void:
		super._init(villager)
		anim = "idle"
	func enter(args: Dictionary) -> void:
		what = args.get("what", "fish")
		super.enter(args)
	func begin() -> void:
		# the buyer reaches across the counter; whoever is serving takes a fish from the
		# ice box and hands it over (seen, not teleported)
		v.play("give")
		var seller = _seller()
		if seller and seller.animator:
			seller.react("give", 2.6)
			seller.animator.show_prop("fish" if what == "fish" else "bread", true, 1.5)
	func _seller():
		if obj == null:
			return null
		for o in v.world.villagers:
			if o != v and o.fsm.current is WorkState and o.fsm.current.obj != null and o.global_position.distance_to(v.global_position) < 6.0:
				return o
		return null
	func act(_minutes: float) -> bool:
		return elapsed >= 6.0
	func finish() -> void:
		var got := 0
		if what == "bait":
			got = v.world.economy.buy_bait(v)
			if got == 0:
				v.brain.cooldown["buy_bait"] = GameClock.total_minutes + 90.0
		else:
			got = v.world.economy.buy_fish(v)
			if got == 0:
				v.brain.cooldown["buy_food"] = GameClock.total_minutes + 60.0
		if got > 0 and v.animator:
			v.animator.show_prop("fish", true, 45.0)     # carried home in the hand

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

class MendNetsState extends UseObjectState:
	## A day ashore: mending nets and gear keeps the boat in trim.
	var duration: float = 60.0
	func _init(villager = null) -> void:
		super._init(villager)
		anim = "work"
	func enter(args: Dictionary) -> void:
		duration = args.get("minutes", 60.0)
		super.enter(args)
	func act(_minutes: float) -> bool:
		return elapsed >= duration or v.needs["hunger"] > 70.0
	func finish() -> void:
		var b = v.world.boats.get(v.job["place"]) if v.job != null else null
		if b:
			b.condition = minf(1.0, b.condition + 0.08)
		v.stats["nets_mended"] += 1
		v.skills["fishing"] = minf(1.0, v.skills["fishing"] + 0.002)


class SwimState extends VillagerState:
	## A swim off the beach on a fine day: wade out, swim slow loops in the shallows
	## (front crawl at the waterline), come back. Washes, and lifts the mood.
	var minutes_left: float = 30.0
	var spot: Vector3
	var _a: float = 0.0
	var _r: float = 2.5
	var _dir: float = 1.0
	func _init(villager = null) -> void:
		super._init(villager)
		anim = "swim"
	func enter(args: Dictionary) -> void:
		minutes_left = args.get("minutes", 30.0)
		spot = v.world.swim_spot(v.at_node)
		_a = v.rng.randf() * TAU
		_r = v.rng.randf_range(1.6, 3.4)
		_dir = 1.0 if v.rng.randf() < 0.5 else -1.0
		v.play("swim")
	func tick(dt: float, minutes: float) -> void:
		minutes_left -= minutes
		_a += _dir * dt * 0.35 / maxf(_r, 0.5)          # ~0.35 m/s
		var p := spot + Vector3(cos(_a), 0, sin(_a)) * _r
		p.y = v.world.ocean.height(p.x, p.z)
		v.global_position = p
		v.face(Vector3(-sin(_a), 0, cos(_a)) * _dir)
		if minutes_left <= 0.0:
			v.needs["hygiene"] = 100.0
			v.needs["social"] = minf(100.0, v.needs["social"] + 15.0)
			v.stats["swims"] = int(v.stats.get("swims", 0)) + 1
			v.brain.cooldown["swim"] = GameClock.total_minutes + 1440.0
			v.unsnap()
			v.step_done()
