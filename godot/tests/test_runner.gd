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
	var days := 2.0
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--out="):
			out_path = a.substr(6)
		if a.begins_with("--days="):
			days = float(a.substr(7))
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
	for n in ["terrain", "cliffs", "gate", "structures", "props", "vegetation", "boats"]:
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
	var pantry := {"raw_fish": 1, "meals": 0}
	var sseq := [stove.stove_state]
	stove.begin_use(fake)
	sseq.append(stove.stove_state)
	var lit_light: bool = stove.light != null and stove.light.visible
	for i in 40:
		stove.tick(1.0)
		if sseq[-1] != stove.stove_state:
			sseq.append(stove.stove_state)
	var done: bool = stove.is_done()
	stove.finish(pantry)
	stove.release(fake)
	sseq.append(stove.stove_state)
	check("stove cold>lit>cooking>cold, fire light on while lit", sseq == ["cold", "lit", "cooking", "cold"] and lit_light and done and not stove.light.visible, sseq)
	check("cooking moves stock: 1 raw fish -> 3 meals", pantry == {"raw_fish": 0, "meals": 3}, pantry)
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
			starved_info.append({"id": v.villager_id, "home": v.home.building_id, "job": v.job, "pantry": v.household, "starve_minutes": v.stats["starve_minutes"], "log": v.log.slice(-8)})
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
	var stock_now := village.market_stock
	for hh in village.households.values():
		stock_now += hh["raw_fish"]
	var start: Dictionary = VillageDB.population.get("start_pantry", {})
	var expected := 4 + village.households.size() * int(start.get("raw_fish", 0)) + int(tot["fish_caught"]) - int(tot["meals_cooked"]) / CookingStation.MEALS_PER_FISH
	check("fish ledger balances (start + caught - cooked = pantries + market)", stock_now == expected, {"have": stock_now, "expected": expected, "market": village.market_stock})
	check("no route failures", tot["failed_paths"] == 0, tot["failed_paths"])
	check("nobody starves (no one at maximum hunger for over 60 game minutes)", starving == 0, {"cases": starved_info, "total_minutes_at_max": snappedf(tot["starve_minutes"], 0.1)})
	var all_states := true
	for s in ["walk", "sleep", "eat", "cook", "fish", "work", "climb_stairs"]:
		all_states = all_states and state_seen.has(s)
	check("all activity states observed", all_states, state_seen.keys())

	var summary := {"engine": Engine.get_version_info()["string"], "passed": results.size() - failures, "failed": failures,
		"days": days, "villagers": village.villagers.size(), "nav_nodes": g.pos.size(), "totals": tot, "state_samples": state_seen,
		"sim_wall_ms": wall_ms, "results": results}
	if out_path != "":
		var f := FileAccess.open(out_path, FileAccess.WRITE)
		if f:
			f.store_string(JSON.stringify(summary, " "))
			f.close()
	print("RESULT: %s (%d passed, %d failed)" % ["PASSED" if failures == 0 else "FAILED", results.size() - failures, failures])
	get_tree().quit(0 if failures == 0 else 1)
