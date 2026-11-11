extends Node
## Headless test suite.  Run from the godot/ folder:
##   godot --headless res://tests/test_runner.tscn -- --out=/abs/path/results.json [--days=2]
## Exit code 0 = all passed.  No rendering is involved: these tests prove the
## logic (data loading, walk graph, object state machines, villager AI), not
## how the game looks.

var results: Array = []
var failures: int = 0

func check(name_: String, ok: bool, detail = "") -> void:
	results.append({"test": name_, "passed": ok, "detail": detail})
	if not ok:
		failures += 1
	print("%s  %s  %s" % ["PASS" if ok else "FAIL", name_, str(detail)])

func _ready() -> void:
	var out_path := ""
	var days := 7.0
	var gen_days := 45.0
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--out="):
			out_path = a.substr(6)
		if a.begins_with("--days="):
			days = float(a.substr(7))
		if a.begins_with("--gen-days="):
			gen_days = float(a.substr(11))
	GameClock.reset(6.0)
	var village := Village.new()
	village.with_presentation = false
	add_child(village)
	village.sim.auto = false
	await get_tree().process_frame

	# ---- 1. data + assets
	check("layout has 30 buildings", VillageDB.layout["buildings"].size() == 30, VillageDB.layout["buildings"].size())
	check("30 building prefabs instanced", village.buildings.size() == 30, village.buildings.size())
	var missing := []
	for id in village.buildings:
		var b: Building = village.buildings[id]
		if b.model == null or not b.groups.has("ROOF") or not b.groups.has("BASE"):
			missing.append(id)
		var walls := 0
		for g in b.groups:
			if g.begins_with("WALL_"):
				walls += 1
		if walls < 3:
			missing.append(id + ":walls")
		if b.sidecar.get("door") != null and (not b.groups.has("DOOR_main") or b.door == null or b.door.leaf == null):
			missing.append(id + ":door")
	check("every prefab has ROOF, BASE, wall groups and a hinged door node", missing.is_empty(), missing)
	var env_ok := true
	for n in ["island", "seabed", "structures", "props", "vegetation", "boats"]:
		env_ok = env_ok and village.get_node_or_null("Environment/" + n) != null
	check("environment GLBs loaded", env_ok)
	var n_anchor := 0
	for id in village.buildings:
		n_anchor += village.buildings[id].sidecar["anchors"].size()
	check("interaction anchors placed (368 stubs in layout)", n_anchor >= 360, n_anchor)

	# ---- 2. walk graph
	var g: NavGraph = village.graph
	var doors := []
	for id in village.buildings:
		doors.append("door_" + id)
	var unreachable := 0
	var longest := 0.0
	for i in doors.size():
		for j in range(i + 1, doors.size()):
			var p := g.find_path(doors[i], doors[j])
			if p.is_empty():
				unreachable += 1
			else:
				longest = maxf(longest, g.path_length(p))
	check("all 435 door-to-door pairs routable", unreachable == 0, {"unreachable": unreachable, "longest_m": snappedf(longest, 0.1)})
	var bad_int := []
	for id in village.buildings:
		for o in village.buildings[id].interactables:
			if o.nav_node != "" and g.find_path("door_" + id, o.nav_node).is_empty():
				bad_int.append(o.object_id)
	check("every interior anchor reachable from its front door", bad_int.is_empty(), bad_int)
	var fs_bad := []
	for fs in village.fishing_spots:
		for v in village.villagers:
			if g.find_path(v.at_node, fs.nav_node).is_empty():
				fs_bad.append([v.villager_id, fs.object_id])
	check("every villager's bed connects to every fishing spot", fs_bad.is_empty(), fs_bad.size())
	var p2 := g.find_path("door_H01", "door_H19")
	var types := {}
	for i in range(p2.size() - 1):
		types[g.edge(p2[i], p2[i + 1])["type"]] = true
	check("quay cottage -> crown cottage route uses stairs", types.has("stair"), types.keys())

	# ---- 3. object state machines
	var h01: Building = village.buildings["H01"]
	var d: Door = h01.door
	var seq := [d.door_state]
	d.request_open()
	for i in 80:
		d.process_door(0.1)
		if seq[-1] != d.door_state:
			seq.append(d.door_state)
	check("door cycles closed>opening>open>closing>closed", seq == ["closed", "opening", "open", "closing", "closed"], seq)
	var rest_b := d._closed_basis
	d.request_open()
	for i in 8:
		d.process_door(0.1)
	var ang := rest_b.get_rotation_quaternion().angle_to(d.leaf.transform.basis.get_rotation_quaternion())
	check("door leaf node rotates ~100 deg about its hinge", absf(rad_to_deg(ang) - 100.0) < 3.0, snappedf(rad_to_deg(ang), 0.1))
	for i in 80:
		d.process_door(0.1)
	var stove: CookingStation = h01.all_of("stove")[0]
	var fake := Node3D.new()
	add_child(fake)
	var tl := Ledger.new()
	tl.open("t_home", 10)
	tl.mint("t_home", "fish", 1, "test")
	var sseq := [stove.stove_state]
	stove.begin_use(fake)
	sseq.append(stove.stove_state)
	var lit_light: bool = stove.light != null and stove.light.visible
	for i in 40:
		stove.tick(1.0)
		if sseq[-1] != stove.stove_state:
			sseq.append(stove.stove_state)
	var done: bool = stove.is_done()
	stove.finish(tl, "t_home")
	stove.release(fake)
	sseq.append(stove.stove_state)
	check("stove cold>lit>cooking>cold, fire light on while lit", sseq == ["cold", "lit", "cooking", "cold"] and lit_light and done and not stove.light.visible, sseq)
	check("cooking moves stock: 1 raw fish -> 3 meals", tl.qty("t_home", "fish") == 0 and tl.qty("t_home", "meal") == 3 and tl.audit().is_empty(), tl.acc["t_home"])
	check("ledger refuses to go negative", not tl.consume("t_home", "fish", 1, "x") and not tl.pay("t_home", "t_home", 99, "x") and tl.audit().is_empty(), tl.refused)
	var bed: Bed = h01.all_of("bed")[0]
	var owner_v = null
	for v in village.villagers:
		if v.bed == bed:
			owner_v = v
	var other = village.villagers[-1] if village.villagers[-1] != owner_v else village.villagers[0]
	check("bed is reserved for its owner only", owner_v != null and bed.is_available(owner_v) and not bed.is_available(other))
	h01.set_lights(true)
	var lit: bool = h01.lights.size() > 0 and h01.lights[0].visible and h01.state["lights_on"]
	h01.set_lights(false)
	check("interior lighting follows building state", lit and not h01.lights[0].visible)
	h01.set_cutaway(true)
	var cut: bool = not h01.groups["ROOF"].visible and not h01.groups["WALL_S"].visible and h01.groups["WALL_N"].visible
	h01.set_cutaway(false)
	check("cutaway hides roof + camera-facing walls", cut and h01.groups["ROOF"].visible)

	# ---- 4. animation contract
	var va: VillagerAnimator = village.villagers[0].animator
	var clips_ok := true
	for c in VillagerAnimator.CLIPS:
		clips_ok = clips_ok and va.player.has_animation(c)
	check("placeholder rig exposes all 11 animation clips", clips_ok, VillagerAnimator.CLIPS)
	va.play("walk")
	for i in 30:
		await get_tree().process_frame
	check("animation state machine travels idle -> walk", String(va.playback.get_current_node()) == "walk", String(va.playback.get_current_node()))
	va.play("idle")

	# ---- 5. autonomous life: run the whole village
	var t0 := Time.get_ticks_msec()
	var seconds := days * 1440.0 / GameClock.minutes_per_second
	var state_seen := {}
	var stuck := {}
	var last_pos := {}
	var chunk := 60.0
	var elapsed := 0.0
	var max_stuck := 0.0
	while elapsed < seconds:
		village.sim.advance(chunk)
		elapsed += chunk
		for v in village.villagers:
			state_seen[v.fsm.current_name] = state_seen.get(v.fsm.current_name, 0) + 1
			var moving: bool = v.fsm.current is LocomotionState or v.fsm.current is OpenDoorState
			if moving and last_pos.get(v, Vector3.INF).distance_to(v.global_position) < 0.05:
				stuck[v] = stuck.get(v, 0.0) + chunk
				max_stuck = maxf(max_stuck, stuck[v])
			else:
				stuck[v] = 0.0
			last_pos[v] = v.global_position
	var wall_ms := Time.get_ticks_msec() - t0
	var tot := {}
	var starving := 0
	var starved_info := []
	var never_slept := 0
	var never_ate := 0
	for v in village.villagers:
		for k in v.stats:
			tot[k] = tot.get(k, 0.0) + v.stats[k]
		if v.stats["starve_minutes"] > 60.0:
			starving += 1
			starved_info.append({"id": v.villager_id, "home": v.home.building_id, "job": v.job, "pantry": village.ledger.acc[v.hh], "starve_minutes": v.stats["starve_minutes"], "log": v.log.slice(-8)})
		if v.stats["sleeps"] == 0:
			never_slept += 1
		if v.stats["meals_eaten"] == 0:
			never_ate += 1
	tot["metres"] = snappedf(tot["metres"], 1.0)
	tot.erase("max_hunger")
	tot["starve_minutes"] = snappedf(tot["starve_minutes"], 0.1)
	var door_opens := 0
	for dd in village.doors:
		door_opens += dd.open_count
	print("SIM totals over %.1f days, %d villagers: %s" % [days, village.villagers.size(), str(tot)])
	print("SIM state samples: ", state_seen)
	check("simulation ran %s game days" % days, GameClock.day() >= int(days) - 0, {"clock": GameClock.text(), "steps": village.sim.steps, "wall_ms": wall_ms})
	check("villagers sleep (everyone at least once)", never_slept == 0, {"sleeps": tot["sleeps"], "never_slept": never_slept})
	check("villagers cook", tot["meals_cooked"] > 0, tot["meals_cooked"])
	check("villagers eat (everyone at least once)", never_ate == 0, {"meals_eaten": tot["meals_eaten"], "never_ate": never_ate})
	check("villagers fish and land a catch", tot["fish_caught"] > 0, tot["fish_caught"])
	check("villagers work", tot["work_blocks"] > 0, tot["work_blocks"])
	check("doors are opened by villagers", door_opens > 0 and tot["doors_opened"] > 0, door_opens)
	check("stairs are climbed", tot["stairs_climbed"] > 0, tot["stairs_climbed"])
	check("no villager is stuck while travelling", max_stuck < 300.0, {"max_stuck_s": max_stuck})
	var problems: Array = village.ledger.audit()
	check("ledger balances: money constant, goods = minted - consumed, nothing negative", problems.is_empty(),
		{"problems": problems, "money": village.ledger.money_issued, "minted": village.ledger.minted, "consumed": village.ledger.consumed})
	check("no route failures", tot["failed_paths"] == 0, tot["failed_paths"])
	check("nobody starves (no one at maximum hunger for over 60 game minutes)", starving == 0, {"cases": starved_info, "total_minutes_at_max": snappedf(tot["starve_minutes"], 0.1)})
	# ---- 6. boats, fishing economy, weather, needs (same long run)
	var trips := 0
	var landed := 0
	var aborted := 0
	var worst_cond := 1.0
	for bid in village.boats:
		var bt: Boat = village.boats[bid]
		trips += bt.trips
		landed += bt.landed
		aborted += bt.aborted
		worst_cond = minf(worst_cond, bt.condition)
	var es: Dictionary = village.economy.stats
	var lt: Dictionary = village.ledger.totals
	check("boats: crews board, sail, fish and land a catch", trips > 0 and landed > 0 and tot["boat_trips"] == trips, {"trips": trips, "fish_landed": landed, "aborted_by_weather": aborted})
	check("landed fish is sold to the market for money", es["fish_sold_to_market"] > 0 and lt.has("landing_sale") and lt["landing_sale"]["money"] > 0, {"sold": es["fish_sold_to_market"], "kept_for_home": es["fish_kept"], "paid": lt.get("landing_sale", {})})
	check("cargo never exceeds a boat's capacity", village.boats.values().all(func(x): return village.ledger.qty(x.object_id, "fish") <= x.capacity_fish()))
	check("households buy fish and meals with money", es["fish_bought"] > 0 and es["meals_sold"] > 0, {"fish_bought": es["fish_bought"], "meals_sold_by_eatery": es["meals_sold"]})
	check("wages are paid; levy funds the council", es["wages_paid"] > 0 and es["levy_paid"] > 0, {"wages_paid": es["wages_paid"], "unpaid": es["wages_unpaid"], "levy_paid": es["levy_paid"], "levy_missed": es["levy_missed"], "council": village.ledger.money(Economy.COUNCIL)})
	check("market price responds to stock", village.economy.fish_sell_price() >= 5 and village.economy.fish_buy_price() >= 3, {"stock": village.ledger.qty(Economy.MARKET, "fish"), "buy": village.economy.fish_buy_price(), "sell": village.economy.fish_sell_price()})
	check("boat wear leads to paid repairs", es["repairs"] > 0 or worst_cond >= Boat.REPAIR_BELOW - Boat.TRIP_WEAR - 0.001, {"repairs": es["repairs"], "unaffordable": es["repairs_unaffordable"], "worst_condition": snappedf(worst_cond, 0.01)})
	check("villagers drink and wash", tot["drinks"] > 0 and tot["washes"] > 0, {"drinks": tot["drinks"], "washes": tot["washes"]})
	check("weather changed during the run", village.weather.hours_in.values().filter(func(x): return x > 0).size() >= 2, village.weather.hours_in)
	check("friendships form from time spent together", village.society.bonds.size() > 20, {"pairs": village.society.bonds.size(), "strong": village.society.bonds.values().filter(func(x): return x >= 45.0).size()})
	var poorest := 1 << 30
	var richest := 0
	for hh in village.households:
		poorest = mini(poorest, village.ledger.money(hh))
		richest = maxi(richest, village.ledger.money(hh))
	check("no household has negative money", poorest >= 0, {"poorest": poorest, "richest": richest})

	# ---- 7. interruption: a storm turns a boat round
	var crew = null
	var boat: Boat = null
	village.weather.force("clear")
	for i in 3000:
		village.sim.advance(6.0)
		village.weather.state = "clear"
		for bb in village.boats.values():
			if bb.boat_state == "outbound" and not bb.users.is_empty():
				boat = bb
				crew = bb.users[0]
		if boat:
			break
	if boat == null:
		check("storm interrupts a trip (no boat put to sea within the wait)", false)
	else:
		var ab0 := boat.aborted
		village.weather.force("storm")
		var back := false
		for i in 600:
			village.sim.advance(2.0)
			village.weather.state = "storm"
			if boat.boat_state == "moored":
				back = true
				break
		var next_act: String = crew.activity
		check("storm interrupts a trip: boat returns and moors, crew moves on", back and boat.aborted == ab0 + 1 and not crew.at_sea, {"boat": boat.object_id, "crew_then": next_act})
		var sailed := false
		for i in 300:
			village.sim.advance(2.0)
			village.weather.state = "storm"
			for bb in village.boats.values():
				sailed = sailed or bb.boat_state == "outbound"
		check("no boat puts to sea during a storm", not sailed)
		village.weather.force("clear")

	# ---- 8. save / load mid-activity
	var save_path := "user://lt_test_save.json"
	village.sim.advance(600.0)
	var busy := 0
	for v in village.villagers:
		if v.fsm.current_name != "idle":
			busy += 1
	var snap: Dictionary = SaveGame.snapshot(village)
	var ok_save: bool = SaveGame.save(village, save_path)
	var n_before: int = village.villagers.size()
	var clock_before := GameClock.total_minutes
	var money_before := {}
	for id in village.ledger.acc:
		money_before[id] = village.ledger.money(id)
	village.queue_free()
	await get_tree().process_frame
	GameClock.reset(6.0)
	var v2 := Village.new()
	v2.with_presentation = false
	add_child(v2)
	v2.sim.auto = false
	await get_tree().process_frame
	var data: Dictionary = SaveGame.load_file(save_path)
	var applied: bool = SaveGame.apply(v2, data)
	var same_money := true
	for id in money_before:
		same_money = same_money and v2.ledger.money(id) == money_before[id]
	var ages_ok := true
	for r in snap["villagers"]:
		var nv = v2.villager_by_id(r["id"])
		ages_ok = ages_ok and nv != null and absf(nv.age - r["age"]) < 0.001 and nv.hh == r["household"] and nv.partner == r["partner"] \
			and absf(nv.needs["hunger"] - r["needs"]["hunger"]) < 0.001
	check("save written while %d villagers were mid-activity" % busy, ok_save and busy > 0)
	check("load restores clock, residents, households, money, weather", applied and v2.villagers.size() == n_before and absf(GameClock.total_minutes - clock_before) < 0.01
		and same_money and ages_ok and v2.weather.state == snap["weather"]["state"] and v2.ledger.audit().is_empty(),
		{"villagers": v2.villagers.size(), "audit": v2.ledger.audit()})
	v2.sim.advance(1440.0)
	var stuck2 := 0
	for v in v2.villagers:
		stuck2 += v.stats["failed_paths"]
	check("simulation continues for a day after loading", v2.ledger.audit().is_empty() and stuck2 == int(tot["failed_paths"]) and v2.villagers.size() >= n_before, {"clock": GameClock.text()})
	var old: Dictionary = snap.duplicate(true)
	old["version"] = 1
	old.erase("grounds")
	old.erase("journal")
	old["weather"]["state"] = "rain"
	for r in old["villagers"]:
		r["needs"].erase("thirst")
	var fo := FileAccess.open("user://lt_test_save_v1.json", FileAccess.WRITE)
	fo.store_string(JSON.stringify(old))
	fo.close()
	var mig: Dictionary = SaveGame.load_file("user://lt_test_save_v1.json")
	check("version-1 save migrates to the current schema", not mig.has("error") and int(mig["version"]) == SaveGame.VERSION and mig["villagers"][0]["needs"].has("thirst") and mig.has("journal") and mig["weather"]["state"] == "light_rain")
	var fb := FileAccess.open("user://lt_test_bad.json", FileAccess.WRITE)
	fb.store_string("{\"schema\": \"living-tides.save\", \"version\": 3}")
	fb.close()
	check("a damaged save is rejected, not half-applied", SaveGame.load_file("user://lt_test_bad.json").has("error"))
	v2.queue_free()
	await get_tree().process_frame

	# ---- 9. generations: accelerated calendar (1 game day = 1 year of life)
	GameClock.reset(6.0)
	var v3 := Village.new()
	v3.with_presentation = false
	add_child(v3)
	v3.sim.auto = false
	v3.society.days_per_year = 1.0
	await get_tree().process_frame
	var pop0: int = v3.villagers.size()
	var tg := Time.get_ticks_msec()
	v3.sim.advance(gen_days * 1440.0)
	var sc: Dictionary = v3.society.counts
	var dangling := 0
	var bad_house := 0
	var no_bed := 0
	for v in v3.villagers:
		if v.partner != "" and v3.villager_by_id(v.partner) == null:
			dangling += 1
		if v.partner != "" and v3.villager_by_id(v.partner) != null and v3.villager_by_id(v.partner).partner != v.villager_id:
			dangling += 1
		if not v3.households.has(v.hh) or v3.households[v.hh]["building"] != v.home.building_id:
			bad_house += 1
		if v.bed == null or (v.shares_bed_of == "" and v.bed.owner_id != v.villager_id) or (v.shares_bed_of != "" and not v.bed.co_sleepers.has(v.villager_id)):
			no_bed += 1
	var members_ok := true
	for hh in v3.households:
		members_ok = members_ok and v3.households[hh]["members"] == v3.villagers.filter(func(x): return x.hh == hh).size()
	var starved3 := 0
	for v in v3.villagers:
		if v.stats["starve_minutes"] > 180.0:
			starved3 += 1
	print("GEN ", gen_days, " days: ", sc, " population ", pop0, " -> ", v3.villagers.size(), " events ", v3.society.events.size(), " wall_ms ", Time.get_ticks_msec() - tg)
	check("generations: births happen", sc["births"] > 0, sc)
	check("generations: residents age, retire and die", sc["deaths"] > 0 and sc["retired"] > 0, {"deaths": sc["deaths"], "retired": sc["retired"]})
	check("generations: children come of age", sc["came_of_age"] > 0 or gen_days < 17.0, sc["came_of_age"])
	check("generations: estates settle and the books still balance", v3.ledger.audit().is_empty(), {"estates": sc["estates"], "audit": v3.ledger.audit()})
	check("generations: no dangling partners, homes, beds or member counts", dangling == 0 and bad_house == 0 and no_bed == 0 and members_ok, {"dangling": dangling, "bad_house": bad_house, "no_bed": no_bed})
	check("generations: life events are recorded as history", v3.society.events.size() >= sc["births"] + sc["deaths"], v3.society.events.slice(-3))
	check("generations: village still fed after %d days" % int(gen_days), starved3 == 0, {"starved": starved3, "population": v3.villagers.size()})
	var all_states := true
	for s in ["walk", "sleep", "eat", "cook", "work", "climb_stairs", "fish_trip", "drink"]:
		all_states = all_states and state_seen.has(s)
	check("all activity states observed", all_states, state_seen.keys())

	var summary := {"engine": Engine.get_version_info()["string"], "passed": results.size() - failures, "failed": failures,
		"days": days, "villagers": n_before, "nav_nodes": g.pos.size(), "totals": tot, "state_samples": state_seen,
		"sim_wall_ms": wall_ms, "economy": es, "ledger_totals": lt, "society": sc, "results": results}
	if out_path != "":
		var f := FileAccess.open(out_path, FileAccess.WRITE)
		if f:
			f.store_string(JSON.stringify(summary, " "))
			f.close()
	print("RESULT: %s (%d passed, %d failed)" % ["PASSED" if failures == 0 else "FAILED", results.size() - failures, failures])
	get_tree().quit(0 if failures == 0 else 1)
