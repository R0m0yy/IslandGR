class_name Ecosystem
extends RefCounted
## Marine life and birds as simulated animals (tropical reef coast - no seals
## or sea lions, which do not belong here). Every animal has a position, a
## state, hunger or size, and rules of its own. The sea's fish are the same
## fish the boats catch: a poor reef means poor landings.
##
## Fish schools  scad (small, many), snapper (reef), mackerel (open water):
##               travel a ring of sea waypoints, grow back slowly, bolt from
##               predators and boats, go deep in rough water.
## Predators     barracuda hunt schools; a dolphin pod patrols offshore, feeds
##               and breaches; turtles travel and surface to breathe.
## Shore         ghost crabs come out on the spit at dusk and bolt for their
##               holes when someone comes near; sandpipers work the tideline.
## Birds         gulls scavenge and steal exposed fish; pelicans and terns
##               dive on schools; a frigatebird robs other birds in the air.

const RING := [Vector3(22, 0, 22), Vector3(10, 0, 36), Vector3(-20, 0, 45), Vector3(-60, 0, 25), Vector3(-62, 0, -20),
	Vector3(-30, 0, -50), Vector3(20, 0, -52), Vector3(58, 0, -30), Vector3(46, 0, 9), Vector3(55, 0, 32), Vector3(30, 0, 48)]
const SPECIES := {   # cap, regrowth per hour (fraction of cap), speed m/s, depth
	"scad": {"cap": 90.0, "grow": 0.030, "speed": 1.6, "depth": 0.6},
	"snapper": {"cap": 45.0, "grow": 0.018, "speed": 0.9, "depth": 1.6},
	"mackerel": {"cap": 60.0, "grow": 0.024, "speed": 2.3, "depth": 1.0},
}
const ROOSTS := [Vector3(9, 5.6, -1), Vector3(-10.5, 6.8, 17.5), Vector3(2.7, 4.6, 17.2), Vector3(19.5, 5.0, -2), Vector3(35, 14.2, 16), Vector3(5.2, 2.0, 13.4)]
const SCRAP_HEAP := Vector3(12.0, 1.6, 3.6)       # by the market, on the quay
const BEACH := [Vector3(-3.5, 0.8, 26.2), Vector3(12.5, 0.8, 26.0)]       # the spit

var village = null
var rng := RandomNumberGenerator.new()
var schools: Array = []
var hunters: Array = []          # barracuda
var dolphins: Array = []
var turtles: Array = []
var crabs: Array = []
var birds: Array = []
var stats := {"thefts": 0, "theft_attempts": 0, "scavenged": 0, "bird_dives": 0, "bird_catches": 0, "robbed_in_air": 0, "predator_kills": 0,
	"dolphin_feeds": 0, "school_flights": 0, "crab_bolts": 0, "caught_by_boats": {"scad": 0, "snapper": 0, "mackerel": 0}}
var fertility: float = 1.0        # scales regrowth; lowered by the "poor season" scenario

func setup(v, seed_: int = 23) -> void:
	village = v
	rng.seed = seed_
	var i := 0
	for sp in ["scad", "scad", "scad", "snapper", "snapper", "mackerel", "mackerel", "scad"]:
		var at := i % RING.size()
		schools.append({"id": "S%d" % i, "sp": sp, "pos": RING[at] + Vector3(rng.randf_range(-4, 4), 0, rng.randf_range(-4, 4)), "to": (at + 1) % RING.size(),
			"dir": 1 if i % 2 == 0 else -1, "size": SPECIES[sp]["cap"] * rng.randf_range(0.6, 0.95), "state": "travel", "t": 0.0, "home": at})
		i += 3
	for k in 2:
		hunters.append({"id": "barracuda%d" % k, "pos": RING[(k * 5 + 2) % RING.size()], "state": "prowl", "hunger": 40.0 + 30.0 * k, "to": (k * 5 + 3) % RING.size(), "t": 0.0})
	for k in 4:
		dolphins.append({"id": "dolphin%d" % k, "off": Vector3(k * 1.8, 0, (k % 2) * 2.0), "air": 0.0})
	for k in 2:
		turtles.append({"id": "turtle%d" % k, "pos": RING[k * 4 + 1], "to": k * 4 + 2, "breath": 60.0 + 80.0 * k, "state": "dive"})
	for k in 7:
		var p := BEACH[0].lerp(BEACH[1], (k + 0.5) / 7.0) + Vector3(0, 0, rng.randf_range(-0.8, 0.8))
		crabs.append({"id": "crab%d" % k, "hole": p, "pos": p, "state": "hidden", "t": rng.randf() * 60.0, "to": p})
	var kinds := ["gull", "gull", "gull", "gull", "gull", "pelican", "pelican", "tern", "tern", "tern", "frigatebird", "sandpiper", "sandpiper", "sandpiper"]
	for k in kinds.size():
		var r: Vector3 = ROOSTS[k % ROOSTS.size()]
		if kinds[k] == "sandpiper":
			r = BEACH[0].lerp(BEACH[1], rng.randf())
		birds.append({"id": "%s%d" % [kinds[k], k], "kind": kinds[k], "pos": r, "roost": r, "state": "roost", "hunger": rng.randf_range(20, 70),
			"t": rng.randf() * 30.0, "to": r, "carry": false, "cool": 0.0, "phase": rng.randf() * TAU})
	_pod = {"pos": RING[7], "to": 8, "state": "travel", "hunger": 30.0}

var _pod: Dictionary = {}

# ------------------------------------------------------------------ queries used by fishing
func biomass_near(p: Vector3, radius: float = 20.0) -> float:
	var b := 0.0
	for s in schools:
		if s["pos"].distance_to(p) < radius:
			b += s["size"]
	return b

func take_fish(p: Vector3, n: int, radius: float = 20.0) -> Dictionary:
	## A boat's gear takes n fish from the schools near p. Returns {species: n}.
	var got := {}
	for i in n:
		var best = null
		for s in schools:
			if s["pos"].distance_to(p) < radius and s["size"] >= 1.0 and (best == null or s["size"] > best["size"]):
				best = s
		if best == null:
			break
		best["size"] -= 1.0
		got[best["sp"]] = int(got.get(best["sp"], 0)) + 1
		stats["caught_by_boats"][best["sp"]] += 1
	return got

func total_fish() -> float:
	var b := 0.0
	for s in schools:
		b += s["size"]
	return b

# ------------------------------------------------------------------ tick
func tick(dt: float, minutes: float) -> void:
	var w: Weather = village.weather
	var hour := GameClock.hour()
	var night := hour >= 19.5 or hour < 5.5
	_tick_schools(dt, minutes, w)
	_tick_hunters(dt, minutes)
	_tick_pod(dt, minutes)
	_tick_turtles(dt, minutes)
	_tick_crabs(dt, minutes, w, hour)
	_tick_birds(dt, minutes, w, night)

func _toward(pos: Vector3, to: Vector3, step: float) -> Vector3:
	var d := to - pos
	d.y = 0.0
	if d.length() <= step:
		return Vector3(to.x, pos.y, to.z)
	return pos + d.normalized() * step

func _tick_schools(dt: float, minutes: float, w: Weather) -> void:
	for s in schools:
		var sp: Dictionary = SPECIES[s["sp"]]
		s["size"] = minf(sp["cap"], s["size"] + sp["cap"] * sp["grow"] * fertility * (minutes / 60.0) * (1.0 - s["size"] / sp["cap"] * 0.5))
		var speed: float = sp["speed"] * (2.4 if s["state"] == "flee" else 1.0)
		var tgt: Vector3 = RING[s["to"]]
		s["pos"] = _toward(s["pos"], tgt, speed * dt)
		s["t"] -= dt
		if s["state"] == "flee" and s["t"] <= 0.0:
			s["state"] = "travel"
		if s["pos"].distance_to(tgt) < 1.0:
			# reef fish hold near their home ground; open-water fish keep travelling
			if s["sp"] == "snapper" and rng.randf() < 0.6:
				s["dir"] = -s["dir"]
			s["to"] = posmod(s["to"] + s["dir"], RING.size())
		# boats under way scatter a school
		for b in village.boats.values():
			if b.boat_state in ["outbound", "inbound"] and b.pos.distance_to(s["pos"]) < 5.0 and s["state"] != "flee":
				_spook(s)
		s["deep"] = w.wind > 0.6

func _spook(s: Dictionary) -> void:
	s["state"] = "flee"
	s["t"] = 25.0
	s["dir"] = -s["dir"]
	s["to"] = posmod(s["to"] + s["dir"], RING.size())
	stats["school_flights"] += 1

func _tick_hunters(dt: float, minutes: float) -> void:
	for h in hunters:
		h["hunger"] = minf(100.0, h["hunger"] + 5.0 * minutes / 60.0)
		var prey = null
		var bd := 28.0
		if h["hunger"] > 55.0:
			for s in schools:
				var d: float = s["pos"].distance_to(h["pos"])
				if d < bd and s["size"] > 4.0:
					bd = d
					prey = s
		if prey:
			h["state"] = "hunt"
			h["pos"] = _toward(h["pos"], prey["pos"], 3.6 * dt)
			if bd < 9.0 and prey["state"] != "flee":
				_spook(prey)
			if bd < 1.5:
				var n := minf(prey["size"], 3.0)
				prey["size"] -= n
				h["hunger"] = maxf(0.0, h["hunger"] - 22.0 * n)
				stats["predator_kills"] += int(n)
		else:
			h["state"] = "prowl"
			h["pos"] = _toward(h["pos"], RING[h["to"]], 1.1 * dt)
			if h["pos"].distance_to(RING[h["to"]]) < 1.0:
				h["to"] = posmod(h["to"] + (1 if rng.randf() < 0.7 else -1), RING.size())

func _tick_pod(dt: float, minutes: float) -> void:
	_pod["hunger"] = minf(100.0, _pod["hunger"] + 6.0 * minutes / 60.0)
	var prey = null
	if _pod["hunger"] > 60.0:
		for s in schools:
			if s["sp"] != "snapper" and s["pos"].distance_to(_pod["pos"]) < 30.0 and s["size"] > 8.0:
				prey = s
	if prey:
		_pod["state"] = "feed"
		_pod["pos"] = _toward(_pod["pos"], prey["pos"], 4.2 * dt)
		if _pod["pos"].distance_to(prey["pos"]) < 3.0:
			var n := minf(prey["size"] - 2.0, 6.0)
			prey["size"] -= n
			_pod["hunger"] = maxf(0.0, _pod["hunger"] - 9.0 * n)
			stats["dolphin_feeds"] += 1
			_spook(prey)
	else:
		_pod["state"] = "travel"
		_pod["pos"] = _toward(_pod["pos"], RING[_pod["to"]], 2.6 * dt)
		if _pod["pos"].distance_to(RING[_pod["to"]]) < 1.5:
			_pod["to"] = posmod(_pod["to"] + 1, RING.size())
	for d in dolphins:
		d["air"] = maxf(0.0, d["air"] - dt)
		if d["air"] <= 0.0 and rng.randf() < dt * (0.10 if _pod["state"] == "travel" else 0.25):
			d["air"] = 1.3                                   # a breach: 1.3 s arc

func pod_pos() -> Vector3:
	return _pod["pos"]

func _tick_turtles(dt: float, minutes: float) -> void:
	for t in turtles:
		t["breath"] -= minutes
		if t["state"] == "dive" and t["breath"] <= 0.0:
			t["state"] = "surface"
			t["breath"] = 1.5                                # minutes at the surface
		elif t["state"] == "surface" and t["breath"] <= 0.0:
			t["state"] = "dive"
			t["breath"] = rng.randf_range(25.0, 50.0)
		if t["state"] == "dive":
			t["pos"] = _toward(t["pos"], RING[t["to"]], 0.7 * dt)
			if t["pos"].distance_to(RING[t["to"]]) < 1.0:
				t["to"] = posmod(t["to"] + (1 if rng.randf() < 0.5 else -1), RING.size())

func _someone_near(p: Vector3, r: float) -> bool:
	for v in village.villagers:
		if not v.at_sea and v.global_position.distance_to(p) < r:
			return true
	return false

func _tick_crabs(dt: float, minutes: float, w: Weather, hour: float) -> void:
	var active := (hour >= 17.5 or hour < 6.5) and w.rain < 0.5
	for c in crabs:
		c["t"] -= dt
		var scared: bool = c["state"] != "hidden" and _someone_near(c["pos"], 3.0)
		if c["state"] == "hidden":
			if active and c["t"] <= 0.0 and not _someone_near(c["hole"], 4.0):
				c["state"] = "forage"
				c["t"] = rng.randf_range(20.0, 60.0)
				c["to"] = c["hole"] + Vector3(rng.randf_range(-2.5, 2.5), 0, rng.randf_range(-0.9, 0.9))
		elif scared or not active:
			if c["state"] != "bolt":
				c["state"] = "bolt"
				if scared:
					stats["crab_bolts"] += 1
			c["pos"] = _toward(c["pos"], c["hole"], 2.6 * dt)
			if c["pos"].distance_to(c["hole"]) < 0.1:
				c["state"] = "hidden"
				c["t"] = rng.randf_range(15.0, 50.0)
		else:
			c["pos"] = _toward(c["pos"], c["to"], 0.45 * dt)       # sideways shuffle
			if c["t"] <= 0.0 or c["pos"].distance_to(c["to"]) < 0.1:
				c["t"] = rng.randf_range(8.0, 30.0)
				c["to"] = c["hole"] + Vector3(rng.randf_range(-2.5, 2.5), 0, rng.randf_range(-0.9, 0.9))

# ------------------------------------------------------------------ birds
func exposed_fish() -> Array:
	## Places where fish lie in the open right now: [{account, pos, guarded, who}]
	var out := []
	var l: Ledger = village.ledger
	for b in village.boats.values():
		if b.boat_state == "unloading" and l.qty(b.object_id, "fish") > 0:
			out.append({"account": b.object_id, "pos": b.pos + Vector3(0, 0.6, 0), "guarded": true, "who": b.users[0] if not b.users.is_empty() else null})
	if l.qty(Economy.MARKET, "fish") > 0 and village.buildings.has("P01"):
		var mp: Vector3 = village.buildings["P01"].global_position + Vector3(0, 1.0, 0)
		var staff = null
		for v in village.villagers:
			if v.inside_building() == "P01" and v.fsm.current_name == "work":
				staff = v
		out.append({"account": Economy.MARKET, "pos": mp, "guarded": staff != null, "who": staff})
	if l.qty(Economy.SCRAPS, "fish") > 0:
		out.append({"account": Economy.SCRAPS, "pos": SCRAP_HEAP, "guarded": false, "who": null})
	return out

func _fly(b: Dictionary, to: Vector3, speed: float, dt: float) -> bool:
	var d: Vector3 = to - b["pos"]
	var step := speed * dt
	if d.length() <= step:
		b["pos"] = to
		return true
	b["pos"] += d.normalized() * step
	return false

func _tick_birds(dt: float, minutes: float, w: Weather, night: bool) -> void:
	var storm := w.state == "storm" or w.rain > 0.75
	var exposed := exposed_fish()
	for b in birds:
		b["hunger"] = minf(100.0, b["hunger"] + (7.0 if b["state"] != "roost" else 2.5) * minutes / 60.0)
		b["t"] -= dt
		b["cool"] = maxf(0.0, b["cool"] - dt)
		var kind: String = b["kind"]
		if (night and kind != "sandpiper") or storm:
			if b["state"] != "roost":                       # shelter: every bird heads for its roost
				b["state"] = "to_roost"
				if _fly(b, b["roost"], 9.0, dt):
					b["state"] = "roost"
					b["carry"] = false
			continue
		match kind:
			"gull": _gull(b, dt, exposed)
			"pelican", "tern": _diver(b, dt)
			"frigatebird": _frigate(b, dt)
			"sandpiper": _sandpiper(b, dt)

func _gull(b: Dictionary, dt: float, exposed: Array) -> void:
	match b["state"]:
		"roost":
			if b["hunger"] > 45.0 and b["t"] <= 0.0:
				b["state"] = "patrol"
				b["t"] = rng.randf_range(20.0, 60.0)
		"patrol":
			# circle the harbour looking for an opening
			b["phase"] += dt * 0.35
			var c := Vector3(7, 9.0 + 2.0 * sin(b["phase"] * 0.7), 9) + Vector3(cos(b["phase"]) * 14.0, 0, sin(b["phase"]) * 10.0)
			_fly(b, c, 7.0, dt)
			if b["hunger"] > 55.0 and b["cool"] <= 0.0:
				var pick = null
				for e in exposed:
					if e["pos"].distance_to(b["pos"]) < 45.0 and (pick == null or (pick["guarded"] and not e["guarded"])):
						pick = e
				if pick != null:
					b["state"] = "raid"
					b["target"] = pick
			if b["t"] <= 0.0 and b["hunger"] < 50.0:
				b["state"] = "to_roost"
		"raid":
			var e: Dictionary = b["target"]
			if _fly(b, e["pos"], 11.0, dt):
				_attempt_theft(b, e)
		"flee":
			if _fly(b, b["roost"] + Vector3(0, 6, 0), 10.0, dt):
				b["state"] = "to_roost"
		"to_roost":
			if _fly(b, b["roost"], 7.0, dt):
				b["state"] = "roost"
				b["t"] = rng.randf_range(30.0, 120.0)
				if b["carry"]:
					b["carry"] = false                      # eaten at the roost
					b["hunger"] = maxf(0.0, b["hunger"] - 55.0)

func _attempt_theft(b: Dictionary, e: Dictionary) -> void:
	var l: Ledger = village.ledger
	if e["account"] == Economy.SCRAPS:
		# thrown-out fish on the heap: no one minds, the gulls squabble over it
		if l.consume(Economy.SCRAPS, "fish", 1, "eaten_by_gulls"):
			stats["scavenged"] += 1
			b["hunger"] = maxf(0.0, b["hunger"] - 50.0)
		b["state"] = "to_roost"
		b["cool"] = 40.0
		return
	stats["theft_attempts"] += 1
	var chance := 0.32 if e["guarded"] else 0.8
	chance += 0.12 * (b["hunger"] - 55.0) / 45.0             # a hungrier bird is bolder
	if l.qty(e["account"], "fish") > 0 and rng.randf() < chance:
		l.consume(e["account"], "fish", 1, "stolen_by_gull")
		b["carry"] = true
		b["state"] = "flee"
		stats["thefts"] += 1
		var who = e["who"]
		var where: String = "the market stalls" if e["account"] == Economy.MARKET else "the catch on %s" % e["account"]
		var names := []
		if who != null and is_instance_valid(who):
			who.remember("theft", "a gull stole a fish from %s" % where, -4.0)
			who.react("shoo", 3.0)
			who.stats["thefts_suffered"] += 1
			names.append(who.villager_id)
		village.journal.add("wildlife", names, "A gull snatched a fish from %s%s." % [where, (" while %s was unloading" % who.display_name) if who != null and e["account"] != Economy.MARKET else ""],
			"hungry gull (%d), %s fish in the open" % [int(b["hunger"]), "guarded" if e["guarded"] else "unattended"], true, e["pos"])
		# the commotion draws the others
		for o in birds:
			if o["kind"] == "gull" and o != b and o["state"] in ["patrol", "roost"] and o["pos"].distance_to(e["pos"]) < 40.0:
				o["hunger"] = minf(100.0, o["hunger"] + 12.0)
				if o["state"] == "roost":
					o["state"] = "patrol"
					o["t"] = 40.0
	else:
		b["state"] = "flee"
		b["cool"] = 90.0
		var who2 = e["who"]
		if who2 != null and is_instance_valid(who2):
			who2.react("shoo", 2.0)

func _diver(b: Dictionary, dt: float) -> void:
	var tern: bool = b["kind"] == "tern"
	match b["state"]:
		"roost":
			if b["hunger"] > 40.0 and b["t"] <= 0.0:
				b["state"] = "search"
		"search":
			var best = null
			var bd := 1e9
			for s in schools:
				var d: float = s["pos"].distance_to(b["pos"])
				if d < bd and s["size"] > 5.0 and not s.get("deep", false) and (not tern or s["sp"] == "scad"):
					bd = d
					best = s
			if best == null:
				b["state"] = "to_roost"
			elif _fly(b, best["pos"] + Vector3(0, 7.0 if not tern else 5.0, 0), 9.0 if not tern else 11.0, dt):
				b["state"] = "dive"
				b["target"] = best
		"dive":
			var s2: Dictionary = b["target"]
			if _fly(b, s2["pos"] + Vector3(0, 0.1, 0), 16.0, dt):
				stats["bird_dives"] += 1
				if rng.randf() < (0.55 if not tern else 0.4) and s2["size"] >= 1.0:
					var n := 2.0 if not tern else 1.0
					s2["size"] = maxf(0.0, s2["size"] - n)
					b["hunger"] = maxf(0.0, b["hunger"] - (40.0 if not tern else 30.0))
					b["carry"] = tern
					stats["bird_catches"] += 1
				b["state"] = "to_roost" if b["hunger"] < 35.0 else "climb"
				b["t"] = 4.0
		"climb":
			_fly(b, b["pos"] + Vector3(0, 6, 0), 6.0, dt)
			if b["t"] <= 0.0:
				b["state"] = "search"
		"to_roost":
			if _fly(b, b["roost"], 8.0, dt):
				b["state"] = "roost"
				b["carry"] = false
				b["t"] = rng.randf_range(60.0, 240.0)

func _frigate(b: Dictionary, dt: float) -> void:
	# soars high; robs a bird that is carrying a fish
	b["phase"] += dt * 0.12
	var victim = null
	if b["hunger"] > 50.0:
		for o in birds:
			if o != b and o["carry"] and o["pos"].distance_to(b["pos"]) < 60.0:
				victim = o
	if victim:
		b["state"] = "chase"
		if _fly(b, victim["pos"], 15.0, dt):
			victim["carry"] = false
			b["hunger"] = maxf(0.0, b["hunger"] - 45.0)
			stats["robbed_in_air"] += 1
			village.journal.add("wildlife", [], "A frigatebird harried a %s into dropping its fish and caught it in the air." % victim["kind"], "frigatebird hungry (%d)" % int(b["hunger"] + 45.0), false, b["pos"])
	else:
		b["state"] = "soar"
		_fly(b, Vector3(10, 30, 5) + Vector3(cos(b["phase"]) * 45.0, 4.0 * sin(b["phase"] * 2.0), sin(b["phase"]) * 35.0), 8.0, dt)
		if b["hunger"] > 85.0:
			b["hunger"] = 60.0                             # feeds far offshore, out of view

func _sandpiper(b: Dictionary, dt: float) -> void:
	if _someone_near(b["pos"], 4.0) and b["state"] != "flush":
		b["state"] = "flush"
		b["to"] = BEACH[0].lerp(BEACH[1], rng.randf()) + Vector3(0, 3.0, rng.randf_range(1.0, 2.5))
	if b["state"] == "flush":
		if _fly(b, b["to"], 8.0, dt):
			b["state"] = "roost"
			b["pos"].y = 0.8
			b["t"] = 3.0
	elif b["t"] <= 0.0:
		# run along the tideline, stop, probe
		b["state"] = "forage"
		b["to"] = BEACH[0].lerp(BEACH[1], rng.randf()) + Vector3(0, 0, rng.randf_range(0.8, 1.6))
		b["t"] = rng.randf_range(3.0, 9.0)
		b["hunger"] = maxf(0.0, b["hunger"] - 6.0)
	elif b["state"] == "forage":
		_fly(b, Vector3(b["to"].x, 0.8, b["to"].z), 1.8, dt)

func to_dict() -> Dictionary:
	return {"schools": schools.map(func(s): return {"id": s["id"], "size": s["size"], "pos": [s["pos"].x, s["pos"].z], "to": s["to"], "dir": s["dir"]}),
		"birds": birds.map(func(b): return {"id": b["id"], "hunger": b["hunger"]}), "stats": stats.duplicate(true), "fertility": fertility,
		"seed": rng.seed, "rng": rng.state}

func from_dict(d: Dictionary) -> void:
	for r in d.get("schools", []):
		for s in schools:
			if s["id"] == r["id"]:
				s["size"] = float(r["size"]); s["pos"] = Vector3(r["pos"][0], 0, r["pos"][1]); s["to"] = int(r["to"]); s["dir"] = int(r["dir"])
	for r in d.get("birds", []):
		for b in birds:
			if b["id"] == r["id"]:
				b["hunger"] = float(r["hunger"])
	fertility = float(d.get("fertility", 1.0))
	for k in d.get("stats", {}):
		if typeof(d["stats"][k]) == TYPE_DICTIONARY:
			for q in d["stats"][k]:
				stats[k][q] = int(d["stats"][k][q])
		else:
			stats[k] = int(d["stats"][k])
	rng.seed = int(d.get("seed", 23)); rng.state = int(d.get("rng", 0))
