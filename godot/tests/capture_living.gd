extends Node
## Living-world in-engine frames (software OpenGL under Xvfb):
##   xvfb-run -s "-screen 0 1600x900x24" godot --rendering-method gl_compatibility --rendering-driver opengl3 \
##       res://tests/capture_living.tscn -- --out=/abs/dir
## Every shot waits for the real situation to occur in the simulation, then
## frames it. Nothing is staged except where a line says "setup".

var out_dir := "user://"
var village: Village
var rig
var log_lines: Array = []

func shot(name_: String, note: String) -> void:
	village.day_night.apply(GameClock.hour())
	village.sim._update_lights()
	for i in 24:
		await get_tree().process_frame
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	img.save_png("%s/%s.png" % [out_dir, name_])
	var line := "%s  %s  [%s, %s]  %s" % [name_, GameClock.text(), village.weather.state, village.day_night.phase_name(), note]
	log_lines.append(line)
	print("saved ", line)

func until(pred: Callable, max_minutes: float, step := 1.0, hold := "") -> bool:
	var t := 0.0
	while t < max_minutes:
		if pred.call():
			return true
		village.sim.advance(step)
		if hold != "":
			village.weather.state = hold
		t += step
	return pred.call()

func to_hour(h: float, hold := "clear") -> void:
	while GameClock.hour() < h - 0.01 or GameClock.hour() > h + 12.0:
		village.sim.advance(10.0)
		if hold != "":
			village.weather.state = hold

func frame(target: Vector3, yaw: float, pitch: float, dist: float) -> void:
	rig.release()
	rig.family_hh = ""
	rig.goal_target = target
	rig.goal_yaw = deg_to_rad(yaw)
	rig.goal_pitch = deg_to_rad(pitch)
	rig.goal_dist = dist
	rig.snap()

func ui(on: bool, figures: bool) -> void:
	village.hud.hidden_ui = not on
	village.set_figures_visible(figures)

func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--out="):
			out_dir = a.substr(6)
	GameClock.reset(5.0)
	village = Village.new()
	add_child(village)
	village.sim.auto = false
	rig = village.camera_rig
	rig.set_process_unhandled_input(false)
	village.hud.journal_mode = 0
	village.weather.locked = true
	if OS.get_cmdline_user_args().has("--night"):
		await _night_only()
		get_tree().quit()
		return
	# ---- 1. a resident's morning: fisherman leaves home (inspector shows the day's schedule)
	var fisher = village.villagers.filter(func(x): return x.job != null and x.job["role"] == "fisher")[0]
	await until(func(): return fisher.fsm.current_name in ["walk", "climb_stairs", "open_door"] and fisher.activity in ["boat_trip", "buy_bait"], 300.0)
	ui(true, true)
	rig.focus_villager(fisher)
	frame(fisher.global_position + Vector3(0, 1.2, 0), 38.0, -26.0, 12.0)
	rig.follow = fisher
	await shot("L01_fisherman_morning_inspector", "%s on his way: %s" % [fisher.display_name, fisher.activity])
	# ---- 2. the boat at sea in rough water, riding the shared waves
	await until(func(): return village.boats[fisher.job["place"]].boat_state == "fishing", 240.0)
	var boat: Boat = village.boats[fisher.job["place"]]
	village.weather.state = "heavy_rain"
	village.weather.wind = 0.75
	rig.focus_boat(boat)
	frame(boat.pos + Vector3(0, 1, 0), 30.0, -14.0, 13.0)
	rig.follow = boat
	await shot("L02_boat_riding_waves_rough", "setup: wind forced to 0.75 for the frame; %s fishing at %s" % [boat.object_id, boat.ground["name"]])
	village.weather.state = "clear"
	village.weather.wind = 0.15
	# ---- 3. landing: fish into the market (building inspector shows till and stock)
	await until(func(): return boat.boat_state == "unloading", 400.0)
	rig.focus_boat(boat)
	frame(boat.pos + Vector3(0, 1, 0), 35.0, -28.0, 16.0)
	rig.follow = boat
	await shot("L03_boat_unloading", "%s unloading %d fish" % [boat.object_id, village.ledger.qty(boat.object_id, "fish")])
	await until(func(): return boat.boat_state == "moored", 60.0)
	rig.focus_building(village.buildings["P01"])
	village.hud.journal_mode = 1
	await shot("L04_fish_market_inspector_journal", "market stock %d, till %d" % [village.ledger.qty(Economy.MARKET, "fish"), village.ledger.money(Economy.MARKET)])
	village.hud.journal_mode = 0
	# ---- 4. a gull raid
	var eco: Ecosystem = village.ecosystem
	var raid = [null]
	var got := await until(func():
		for b in eco.birds:
			if b["kind"] == "gull" and b["state"] == "raid" and b["pos"].distance_to(b["target"]["pos"]) < 6.0:
				raid[0] = b
				return true
		return false, 900.0, 0.2)
	if got:
		var g = raid[0]
		rig.release()
		frame(g["target"]["pos"] + Vector3(0, 1.0, 0), 40.0, -20.0, 9.0)
		village.hud.journal_mode = 2
		await shot("L05_gull_raid", "gull %s (hunger %d) closing on fish at %s" % [g["id"], int(g["hunger"]), g["target"]["account"]])
		await until(func(): return g["state"] != "raid", 2.0, 0.1)
		await shot("L06_gull_raid_outcome", "outcome: %s; thefts so far %d" % ["took a fish" if g["carry"] else "driven off", eco.stats["thefts"]])
		village.hud.journal_mode = 0
	# ---- 5. a neighbour in need (setup: one household's food spoils and money is lost)
	var need_hh := ""
	var donor = null
	for d in village.villagers:
		if d.age >= 18.0 and d.generosity > 0.6:
			for hh in village.households:
				if hh != d.hh and village.households[hh]["members"] > 0 and village.buildings[village.households[hh]["building"]].global_position.distance_to(d.home.global_position) < 9.0:
					need_hh = hh
					donor = d
					break
		if donor:
			break
	if donor:
		for it in ["fish", "meal"]:
			var q := village.ledger.qty(need_hh, it)
			if q > 0:
				village.ledger.consume(need_hh, it, q, "scenario_setup_spoilage")
		var m := village.ledger.money(need_hh)
		if m > 0:
			village.ledger.pay(need_hh, Economy.COUNCIL, m, "scenario_setup_lost_savings")
		village.economy.debts[need_hh] = Economy.CREDIT_LIMIT
		for r in village.villagers.filter(func(x): return x.hh == need_hh):
			r.needs["hunger"] = 80.0
		village.ledger.mint(donor.hh, "fish", 8, "scenario_setup_good_catch")
		var giver = [null]
		var seen := await until(func():
			for x in village.villagers:
				if x.activity == "give_food" and x.path.size() <= 2:
					giver[0] = x
					return true
			return false, 600.0, 0.5)
		if seen:
			ui(true, true)
			rig.focus_villager(giver[0])
			frame(giver[0].global_position + Vector3(0, 1.2, 0), 35.0, -24.0, 10.0)
			rig.follow = giver[0]
			await shot("L07_neighbour_brings_food", "setup: %s's larder emptied; %s arriving with fish" % [village.household_name(need_hh), giver[0].display_name])
			await until(func(): return village.journal.of_type("community").size() > 0, 30.0, 0.5)
			village.hud.journal_mode = 2
			await shot("L08_gift_in_journal", "journal shows the gift")
			village.hud.journal_mode = 0
	# ---- 6. storm: people run home, boats return, birds roost
	to_hour(13.0)
	village.weather.force("storm")
	village.weather.state = "storm"
	await until(func(): return false, 50.0, 1.0, "storm")
	ui(true, true)
	frame(Vector3(2, 3, 8), 34.0, -22.0, 42.0)
	await shot("L09_storm_harbour", "storm forced (setup); sheltering: %d" % village.villagers.reduce(func(a, x): return a + x.stats["sheltered"], 0))
	village.weather.force("clear")
	village.weather.cloud = 0.05; village.weather.rain = 0.0; village.weather.wind = 0.15
	village.weather.state = "clear"
	# ---- 7. golden hour and sunset watchers
	to_hour(18.4)
	ui(false, false)
	frame(Vector3(-4, 6, 0), 40.0, -18.0, 100.0)
	await shot("L10_golden_hour_overview", "environment only")
	var watcher = [null]
	await until(func():
		for x in village.villagers:
			if x.at_node in ["k_look", "sp_1"] and x.fsm.current_name == "idle":
				watcher[0] = x
				return true
		return false, 60.0, 1.0)
	if watcher[0]:
		ui(true, true)
		rig.focus_villager(watcher[0])
		frame(watcher[0].global_position + Vector3(0, 1.2, 0), 250.0, -10.0, 12.0)
		rig.follow = watcher[0]
		await shot("L11_watching_the_sunset", "%s at %s" % [watcher[0].display_name, watcher[0].at_node])
	# ---- 8. night, moon, lit homes
	to_hour(21.5)
	ui(false, false)
	frame(Vector3(2, 3, 6), 34.0, -20.0, 52.0)
	await shot("L12_night_moonlight", "environment only; moon %s" % village.day_night.phase_name())
	frame(Vector3(-4, 10, 0), 200.0, -12.0, 110.0)
	await shot("L13_night_sky_moon_stars", "looking out to sea")
	# ---- 9. village inspector + journal after a day
	to_hour(23.0)
	ui(true, false)
	village.hud.show_village = true
	village.hud.journal_mode = 1
	frame(Vector3(-4, 6, 0), 40.0, -30.0, 112.0)
	await shot("L14_village_inspector_journal", "after one day")
	village.hud.show_village = false
	# ---- 10. a family after generations (loads the save written by living_world_test scenario E)
	var d := SaveGame.load_file("user://lt_living_E.json")
	if not d.has("error") and SaveGame.apply(village, d):
		var best = null
		var bn := -1
		for x in village.villagers:
			var n: int = x.children.size() + x.parents.size() * 2
			if n > bn:
				bn = n
				best = x
		village.hud.view = "family"
		village.hud.journal_mode = 0
		ui(true, true)
		rig.focus_villager(best)
		frame(best.global_position + Vector3(0, 1.2, 0), 40.0, -30.0, 16.0)
		rig.follow = best
		await shot("L15_family_tree_after_24_years", "loaded save from scenario E (24 accelerated years)")
		village.hud.view = "timeline"
		await shot("L16_resident_timeline", "same resident's life history")
	var f := FileAccess.open("%s/capture_living_log.txt" % out_dir, FileAccess.WRITE)
	f.store_string("\n".join(log_lines))
	f.close()
	get_tree().quit()

func _night_only() -> void:
	village.hud.hidden_ui = true
	village.set_figures_visible(false)
	to_hour(21.5)
	frame(Vector3(2, 3, 6), 34.0, -20.0, 52.0)
	await shot("L12_night_moonlight", "environment only; moon %s" % village.day_night.phase_name())
	frame(Vector3(-4, 10, 0), 200.0, -12.0, 110.0)
	await shot("L13_night_sky_moon_stars", "looking out to sea")
	to_hour(19.0)
	frame(Vector3(-4, 6, 0), 40.0, -18.0, 100.0)
	await shot("L10b_sunset_overview", "environment only")
	var f := FileAccess.open("%s/capture_living_night_log.txt" % out_dir, FileAccess.WRITE)
	f.store_string("\n".join(log_lines))
	f.close()
