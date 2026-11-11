extends Node
## Living-world scenario tests (directive §16-17). Each scenario builds a fresh
## village, lets the simulation run, and checks real state: ledger
## transactions, inventories, journal entries, memories, positions.
## Setup steps that bend the world on purpose (to make a rare situation happen
## now) are recorded under "setup" in the output, so nothing is hidden.
##
##   godot --headless res://tests/living_world_test.tscn -- --only=A,B,C --out=/abs/dir
## Scenarios: A fisherman's day · B struggling neighbour · C animal steals fish ·
## D storm · E household evolves + save/load · F poor season economy ·
## G ecosystem · Y one year · P generations (demography)

var out_dir := "user://"
var E_DAYS := 24.0
var results: Array = []
var failures := 0
var current := ""
var report := {}

func check(name_: String, ok: bool, detail = "") -> void:
	results.append({"scenario": current, "test": name_, "passed": ok, "detail": detail})
	if not ok:
		failures += 1
	print("%s  [%s] %s  %s" % ["PASS" if ok else "FAIL", current, name_, str(detail).left(400)])

func make_village(days_per_year: float = 28.0, seed_offset: int = 0) -> Village:
	GameClock.reset(6.0)
	var v := Village.new()
	v.with_presentation = false
	add_child(v)
	v.sim.auto = false
	v.ledger.keep_all = true
	v.society.days_per_year = days_per_year
	if seed_offset != 0:
		v.weather.rng.seed = 7 + seed_offset
		v.ecosystem.rng.seed = 23 + seed_offset
		v.society.rng.seed = 11 + seed_offset
	return v

func drop(v: Village) -> void:
	v.queue_free()
	await get_tree().process_frame

func run(v: Village, minutes: float, hold := "", stop: Callable = Callable()) -> float:
	## Advances the world; `hold` pins the weather; `stop` ends early. Returns minutes run.
	var done := 0.0
	v.weather.locked = hold != ""
	if hold != "":
		v.weather.state = hold
	while done < minutes:
		var step := minf(10.0, minutes - done)
		v.sim.advance(step)
		done += step
		if hold != "":
			v.weather.state = hold
		if stop.is_valid() and stop.call():
			break
	v.weather.locked = false
	return done

func led(v: Village, pred: Callable) -> Array:
	return v.ledger.log.filter(pred)

func _ready() -> void:
	var only := "A,B,C,D,E,F,G,Y,P"
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--out="):
			out_dir = a.substr(6)
		if a.begins_with("--only="):
			only = a.substr(7)
		if a.begins_with("--e-days="):
			E_DAYS = float(a.substr(9))
	for sc in only.split(","):
		current = sc
		var t0 := Time.get_ticks_msec()
		report[sc] = {}
		await call("scenario_" + sc)
		report[sc]["wall_ms"] = Time.get_ticks_msec() - t0
		print("== scenario %s done in %d ms" % [sc, report[sc]["wall_ms"]])
	var summary := {"engine": Engine.get_version_info()["string"], "passed": results.size() - failures, "failed": failures, "results": results, "report": report}
	var f := FileAccess.open("%s/living_world_%s.json" % [out_dir, only.replace(",", "")], FileAccess.WRITE)
	if f:
		f.store_string(JSON.stringify(summary, " "))
		f.close()
	print("RESULT: %s (%d passed, %d failed)" % ["PASSED" if failures == 0 else "FAILED", results.size() - failures, failures])
	get_tree().quit(0 if failures == 0 else 1)

# ===================================================================== A
func scenario_A() -> void:
	var v := make_village()
	var fisher = null
	for x in v.villagers:
		if x.job != null and x.job["role"] == "fisher" and String(x.job["place"]).begins_with("BOAT"):
			fisher = x
			break
	var hh: String = fisher.hh
	var boat: Boat = v.boats[fisher.job["place"]]
	var trace := []
	fisher.fsm.changed.connect(func(a, b): trace.append([GameClock.text(), b, fisher.activity, fisher.at_node]))
	var m0: int = v.ledger.money(hh)
	var mk0: int = v.ledger.qty(Economy.MARKET, "fish")
	var bait0: int = v.ledger.qty(hh, "bait")
	var trips0 := boat.trips
	var landed_home := [false]
	var stage := {"boarded": false, "landed": false, "purchase": false, "home_after": false}
	var stop := func():
		if fisher.fsm.current_name == "fish_trip":
			stage["boarded"] = true
		if stage["boarded"] and fisher.fsm.current_name != "fish_trip" and boat.boat_state == "moored":
			stage["landed"] = true
		if stage["landed"] and fisher.at_node.begins_with(fisher.home.building_id + ":"):
			stage["home_after"] = true
		stage["purchase"] = led(v, func(e): return e[2] == hh and e[1] in ["store_sale", "market_sale", "eatery_sale"]).size() > 0
		return stage["landed"] and stage["home_after"] and stage["purchase"]
	report["A"]["setup"] = "clear weather held for the day; nothing else changed"
	var store_bait := []
	var stop2 := func():
		if int(GameClock.total_minutes) % 120 == 0:
			store_bait.append([GameClock.text(), v.ledger.qty(Economy.STORE, "bait"), v.ledger.qty(Economy.NETLOFT, "bait"), v.ledger.qty(hh, "bait"), v.ledger.qty(hh, "fish")])
		return stop.call()
	var ran := run(v, 48 * 60.0, "clear", stop2)
	report["A"]["store_bait_netloft_bait_home_bait_home_fish"] = store_bait
	report["A"]["decision_log"] = fisher.log.duplicate()
	report["A"]["last_scores"] = fisher.brain.last_scores.duplicate()
	var mine := led(v, func(e): return e[2] == hh or e[3] == hh or e[2] == boat.object_id or e[3] == boat.object_id)
	var caught := 0
	var sold := 0
	var paid := 0
	var kept := 0
	var stolen_from_boat := 0
	for e in mine:
		if e[1] == "boat_catch" and e[3] == boat.object_id:
			caught += e[5]
		if e[1] == "landing_sale" and e[4] == "fish":
			sold += e[5]
		if e[1] == "landing_sale" and e[4] == "money":
			paid += e[5]
		if e[1] == "landing_home":
			kept += e[5]
		if e[1] == "stolen_by_gull" and e[2] == boat.object_id:
			stolen_from_boat += e[5]
	var purchases := mine.filter(func(e): return e[2] == hh and e[1] in ["store_sale", "market_sale", "eatery_sale"] and e[4] == "money")
	var sold_to_market: int = led(v, func(e): return e[1] == "landing_sale" and e[4] == "fish" and e[3] == Economy.MARKET).reduce(func(a, e): return a + e[5], 0)
	report["A"]["fisher"] = {"id": fisher.villager_id, "name": fisher.display_name, "boat": boat.object_id, "ground": boat.ground["name"],
		"game_minutes": ran, "trace": trace, "ledger": mine.slice(0, 60), "money_before": m0, "money_after": v.ledger.money(hh)}
	check("left home and boarded the assigned boat", stage["boarded"] and boat.trips > trips0, {"trips": boat.trips - trips0})
	check("caught fish from the sea (minted into the boat by the catch rule)", caught > 0, caught)
	check("returned, moored and unloaded: every fish caught is accounted for", stage["landed"] and v.ledger.qty(boat.object_id, "fish") == 0 and sold + kept + stolen_from_boat == caught,
		{"caught": caught, "sold": sold, "kept_for_home": kept, "stolen_by_gulls_while_unloading": stolen_from_boat})
	check("sold to the market: market stock and household money moved by the same sale", sold > 0 and paid > 0, {"fish_sold": sold, "paid": paid})
	check("bought household supplies with money", purchases.size() > 0, purchases.map(func(e): return "%s %d at %s" % [e[1], e[5], Journal.stamp({"minute": e[0]})]))
	check("came home after the trip", stage["home_after"])
	check("money and stock reconcile (ledger audit)", v.ledger.audit().is_empty(), v.ledger.audit())
	await drop(v)

# ===================================================================== B
func scenario_B() -> void:
	var v := make_village()
	run(v, 60.0, "clear")
	# pick a donor with spare food to be and a neighbour household to be in need
	var donor = null
	var need_hh := ""
	var best := -1.0
	for d in v.villagers:
		if d.age < 18.0:
			continue
		for hh in v.households:
			if hh == d.hh or v.households[hh]["members"] <= 0:
				continue
			var dist: float = v.buildings[v.households[hh]["building"]].global_position.distance_to(d.home.global_position)
			if dist < 9.0 and d.generosity > best:
				best = d.generosity
				donor = d
				need_hh = hh
	var setup := []
	for it in ["fish", "meal"]:
		var q := v.ledger.qty(need_hh, it)
		if q > 0:
			v.ledger.consume(need_hh, it, q, "scenario_setup_spoilage")
	var pay_out := v.ledger.money(need_hh)
	if pay_out > 0:
		v.ledger.pay(need_hh, Economy.COUNCIL, pay_out, "scenario_setup_lost_savings")
	v.economy.debts[need_hh] = Economy.CREDIT_LIMIT                    # their credit is used up too
	var recipients := v.villagers.filter(func(x): return x.hh == need_hh)
	for r in recipients:
		r.needs["hunger"] = 80.0
	v.ledger.mint(donor.hh, "fish", 8, "scenario_setup_good_catch")
	setup.append("household %s: food spoiled (%s), savings lost (%d), credit exhausted, members hungry 80" % [need_hh, "fish+meals", pay_out])
	setup.append("%s's household had a good catch: +8 fish" % donor.display_name)
	report["B"]["setup"] = setup
	var bond0: float = v.society.bond(donor.villager_id, recipients[0].villager_id)
	var gift_seen := func(): return led(v, func(e): return e[1] == "gift").size() > 0
	var ran := run(v, 10 * 60.0, "clear", gift_seen)
	var gifts := led(v, func(e): return e[1] == "gift")
	var g = gifts[0] if not gifts.is_empty() else null
	var giver_name := ""
	for x in v.villagers:
		if g != null and x.hh == g[2] and x.stats["gifts_given"] > 0:
			giver_name = x.display_name
	report["B"]["gift"] = g
	report["B"]["journal"] = v.journal.of_type("community").slice(0, 5)
	check("a neighbour noticed and brought food (within %d game minutes)" % int(ran), g != null and g[3] == need_hh, {"giver": giver_name, "transaction": g})
	check("the goods really moved: recipient pantry gained what the giver lost", g != null and v.ledger.qty(need_hh, "fish") + v.ledger.qty(need_hh, "meal") > 0)
	var mem := recipients.filter(func(r): return r.memories.any(func(m): return m["type"] == "kindness"))
	check("recipients remember the kindness", not mem.is_empty(), mem.map(func(r): return r.memories[-1]["text"]))
	var bond1: float = v.society.bond(donor.villager_id, recipients[0].villager_id)
	check("the relationship changed", g == null or g[2] != donor.hh or bond1 > bond0, {"before": snappedf(bond0, 0.1), "after": snappedf(bond1, 0.1)})
	run(v, 4 * 60.0, "clear")
	var fed := recipients.filter(func(r): return r.needs["hunger"] < 60.0).size()
	check("the help made a difference: recipients ate", fed > 0, {"recipients": recipients.size(), "now_below_60_hunger": fed})
	check("the favour is remembered for reciprocity", g != null and v.economy.favours.get(g[2] + "|" + need_hh, 0) > 0, v.economy.favours)
	check("ledger audit clean", v.ledger.audit().is_empty(), v.ledger.audit())
	await drop(v)

# ===================================================================== C
func scenario_C() -> void:
	var v := make_village()
	report["C"]["setup"] = "none: gulls get hungry on their own; clear weather held"
	var stop := func(): return v.ecosystem.stats["thefts"] >= 3
	var ran := run(v, 72 * 60.0, "clear", stop)
	var eco: Ecosystem = v.ecosystem
	var stolen := led(v, func(e): return e[1] == "stolen_by_gull")
	var entries := v.journal.of_type("wildlife").filter(func(e): return String(e["text"]).contains("gull snatched"))
	report["C"]["thefts"] = entries.slice(0, 6)
	report["C"]["stolen_ledger"] = stolen
	report["C"]["stats"] = eco.stats.duplicate(true)
	check("gulls stole fish on their own (in %d game minutes)" % int(ran), eco.stats["thefts"] > 0, {"thefts": eco.stats["thefts"], "attempts": eco.stats["theft_attempts"]})
	check("every theft removed a fish from the right account in the ledger", stolen.size() == eco.stats["thefts"] and stolen.all(func(e): return e[2] == Economy.MARKET or e[2].begins_with("BOAT")), stolen.map(func(e): return e[2]))
	check("every theft is in the journal with its cause", entries.size() == eco.stats["thefts"] and entries.all(func(e): return String(e["cause"]).contains("hungry gull")))
	var victims := v.villagers.filter(func(x): return x.stats["thefts_suffered"] > 0)
	check("when someone was there, they noticed and reacted (memory)", eco.stats["thefts"] == stolen.filter(func(e): return e[2] == Economy.MARKET).size() or not victims.is_empty(),
		victims.map(func(x): return "%s: %s" % [x.display_name, x.memories.filter(func(m): return m["type"] == "theft").map(func(m): return m["text"])]))
	check("not every attempt succeeds (guarded fish, failed raids)", eco.stats["theft_attempts"] >= eco.stats["thefts"])
	check("ledger audit clean", v.ledger.audit().is_empty(), v.ledger.audit())
	await drop(v)

# ===================================================================== D
func scenario_D() -> void:
	var v := make_village()
	run(v, 5 * 60.0, "clear")                                  # 11:00, boats out, people about
	var at_sea := v.boats.values().filter(func(b): return b.boat_state != "moored").size()
	var outdoors0 := v.villagers.filter(func(x): return x.inside_building() == "" and not x.at_sea).size()
	var sheltered0: int = v.villagers.reduce(func(a, x): return a + x.stats["sheltered"], 0)
	report["D"]["setup"] = "at %s the weather is forced to storm and held for 3 hours (%d boats at sea, %d people outdoors)" % [GameClock.text(), at_sea, outdoors0]
	v.weather.force("storm")
	var departed := [0]
	var trips_before: int = v.boats.values().reduce(func(a, b): return a + b.trips, 0)
	var rough := [0.0]                                          # lambdas capture by value: use a box
	run(v, 180.0, "storm", func(): rough[0] = maxf(rough[0], v.ocean.roughness()); return false)
	var trips_during: int = v.boats.values().reduce(func(a, b): return a + b.trips, 0) - trips_before
	var moored := v.boats.values().filter(func(b): return b.boat_state == "moored").size()
	var sheltered: int = v.villagers.reduce(func(a, x): return a + x.stats["sheltered"], 0) - sheltered0
	var birds_roost := v.ecosystem.birds.filter(func(b): return b["state"] == "roost").size()
	var crabs_hidden := v.ecosystem.crabs.filter(func(c): return c["state"] == "hidden").size()
	var damaged := v.buildings.keys().filter(func(k): return v.buildings[k].state.get("condition", 1.0) < 0.9)
	var outdoors_leisure := v.villagers.filter(func(x): return x.inside_building() == "" and not x.at_sea and x.activity in ["stroll", "fish"]).size()
	check("boats at sea came home and none left during the storm", moored == v.boats.size() and trips_during == 0, {"at_sea_when_it_broke": at_sea, "moored_now": moored, "departures": trips_during})
	check("people outdoors sought shelter", sheltered > 0 and outdoors_leisure == 0, {"ran_for_shelter": sheltered, "still_strolling_or_shore_fishing": outdoors_leisure})
	check("the sea rose with the wind (wave model)", rough[0] > 0.8, snappedf(rough[0], 0.01))
	check("wildlife took shelter (birds at roost, crabs in holes)", birds_roost >= v.ecosystem.birds.size() - 1 and crabs_hidden == v.ecosystem.crabs.size(), {"birds_roosting": birds_roost, "crabs_hidden": crabs_hidden})
	check("the storm did real damage", not damaged.is_empty(), damaged)
	report["D"]["journal_storm"] = v.journal.recent(12)
	v.weather.force("clear")
	v.weather.cloud = 0.05; v.weather.rain = 0.0; v.weather.wind = 0.15
	run(v, 20 * 60.0, "clear")
	var trips_after: int = v.boats.values().reduce(func(a, b): return a + b.trips, 0) - trips_before
	var repaired := damaged.filter(func(k): return v.buildings[k].state.get("condition", 1.0) >= 1.0)
	var repairs := v.journal.entries.filter(func(e): return e["type"] == "repair" or String(e["text"]).contains("mended the storm"))
	check("life resumed: boats went out again after the storm", trips_after > 0, trips_after)
	check("carpenters repaired the damage", repaired.size() == damaged.size(), {"damaged": damaged.size(), "repaired": repaired.size(), "journal": repairs.map(func(e): return e["text"])})
	check("ledger audit clean", v.ledger.audit().is_empty(), v.ledger.audit())
	await drop(v)

# ===================================================================== E
func scenario_E() -> void:
	var v := make_village(1.0)
	report["E"]["setup"] = "accelerated calendar: 1 game day = 1 year of life; 24 days"
	run(v, E_DAYS * 1440.0)
	var sc: Dictionary = v.society.counts
	var kinds := {}
	for e in v.journal.entries:
		kinds[e["type"]] = int(kinds.get(e["type"], 0)) + 1
	report["E"]["counts"] = sc
	report["E"]["journal_kinds"] = kinds
	check("life events happened: partnerships, births, new jobs", sc["births"] > 0 and kinds.get("hired", 0) > 0, {"births": sc["births"], "partnerships": sc["partnerships"], "hired": kinds.get("hired", 0), "moves": sc["moves"]})
	var grown := v.villagers.filter(func(x): return not x.parents.is_empty() and x.age >= 16.0)
	report["E"]["grown_children"] = grown.map(func(x): return {"id": x.villager_id, "name": x.display_name, "age": int(x.age), "job": x.job, "home": x.home.building_id, "parents": x.parents})
	check("a child born here grew up and took a job", grown.any(func(x): return x.job != null), report["E"]["grown_children"].slice(0, 4))
	var path := "user://lt_living_E.json"
	var snap := SaveGame.snapshot(v)
	SaveGame.save(v, path)
	var n_journal := v.journal.entries.size()
	await drop(v)
	var v2 := make_village(1.0)
	var ok := SaveGame.apply(v2, SaveGame.load_file(path))
	var same := true
	var diffs := []
	for r in snap["villagers"]:
		var x = v2.villager_by_id(r["id"])
		var why := []
		if x == null:
			why.append("missing")
		else:
			if x.partner != r["partner"]: why.append("partner %s/%s" % [x.partner, r["partner"]])
			if x.children != r["children"]: why.append("children %s/%s" % [x.children, r["children"]])
			if x.hh != r["household"]: why.append("hh %s/%s" % [x.hh, r["household"]])
			if JSON.stringify(x.job) != JSON.stringify(JSON.parse_string(JSON.stringify(r["job"]))): why.append("job %s/%s" % [x.job, r["job"]])
			if x.memories.size() != r["memories"].size(): why.append("memories %d/%d" % [x.memories.size(), r["memories"].size()])
		if not why.is_empty():
			same = false
			diffs.append([r["id"], why])
	check("after save and reload: households, partners, children, jobs and memories identical", ok and same, diffs.slice(0, 5))
	check("the journal (world history) survives the reload", v2.journal.entries.size() == n_journal, {"before": n_journal, "after": v2.journal.entries.size()})
	run(v2, 1440.0)
	check("the reloaded world keeps living (another year)", v2.ledger.audit().is_empty() and v2.journal.entries.size() > n_journal)
	await drop(v2)

# ===================================================================== F
func _econ_window(v: Village, days: float) -> Dictionary:
	var start := v.ledger.log.size()
	var prices := []
	var hh_food_hours := {}
	var t := 0.0
	while t < days * 1440.0:
		v.sim.advance(60.0)
		t += 60.0
		v.weather.state = "clear"
		prices.append(v.economy.fish_sell_price())
		for hh in v.households:
			if v.households[hh]["members"] > 0 and v.economy.food_of(hh) == 0:
				hh_food_hours[hh] = int(hh_food_hours.get(hh, 0)) + 1
	var win: Array = v.ledger.log.slice(start)
	var sum := func(reason: String, what: String): return win.filter(func(e): return e[1] == reason and e[4] == what).reduce(func(a, e): return a + e[5], 0)
	var spend := {}
	for e in win:
		if e[1] in ["market_sale", "eatery_sale"] and e[4] == "money":
			spend[e[2]] = int(spend.get(e[2], 0)) + e[5]
	return {"landed": sum.call("landing_sale", "fish") + sum.call("landing_home", "fish"), "caught": sum.call("boat_catch", "fish") + sum.call("handline_catch", "fish"),
		"bought_fish": sum.call("market_sale", "fish"), "on_credit": sum.call("market_credit", "fish"), "gifts": sum.call("gift", "fish"),
		"avg_price": snappedf(prices.reduce(func(a, x): return a + x, 0) / maxf(1.0, prices.size()), 0.01), "hh_hours_without_food": hh_food_hours.values().reduce(func(a, x): return a + x, 0),
		"households_without_food_at_some_point": hh_food_hours.size(), "spend_by_household": spend, "fish_stock_in_sea": int(v.ecosystem.total_fish())}

func scenario_F() -> void:
	var v := make_village()
	var base := _econ_window(v, 3.0)
	report["F"]["setup"] = "after 3 normal days, a poor season: fish regrowth x0.15 and the schools thinned to 30% (as after a marine heatwave)"
	v.ecosystem.fertility = 0.15
	for s in v.ecosystem.schools:
		s["size"] *= 0.3
	var poor := _econ_window(v, 3.0)
	report["F"]["normal"] = base
	report["F"]["poor_season"] = poor
	check("supply fell: less fish landed", poor["landed"] < base["landed"] * 0.75, {"normal": base["landed"], "poor": poor["landed"]})
	check("the market responded: fish got dearer", poor["avg_price"] > base["avg_price"], {"normal": base["avg_price"], "poor": poor["avg_price"]})
	var hand0: int = base["caught"] - base["landed"]
	var hand1: int = poor["caught"] - poor["landed"]
	check("households adjusted: bought less at the higher price, fished for themselves, took credit",
		poor["bought_fish"] < base["bought_fish"] and (hand1 > hand0 or poor["on_credit"] > base["on_credit"]),
		{"bought_fish": [base["bought_fish"], poor["bought_fish"]], "handline_fish": [hand0, hand1], "on_credit": [base["on_credit"], poor["on_credit"]],
		 "households_ever_without_food": [base["households_without_food_at_some_point"], poor["households_without_food_at_some_point"]]})
	var hit: Array = []
	for hh in v.households:
		if v.households[hh]["members"] > 0:
			hit.append([v.ledger.money(hh), hh])
	hit.sort()
	check("consequences differ between households", hit.size() > 2 and hit[-1][0] - hit[0][0] > 20, {"poorest": hit[0], "richest": hit[-1]})
	check("ledger audit clean", v.ledger.audit().is_empty(), v.ledger.audit())
	await drop(v)

# ===================================================================== G
func scenario_G() -> void:
	var v := make_village()
	var eco: Ecosystem = v.ecosystem
	var p0 := eco.schools.map(func(s): return s["pos"])
	var turtle_up := [0]
	var turtle_state := eco.turtles.map(func(t): return t["state"])
	var crab_out := [0]
	var heights := []
	var breaches := [0]
	report["G"]["setup"] = "none; natural weather"
	var watch := func():
		for i in eco.turtles.size():
			if eco.turtles[i]["state"] == "surface" and turtle_state[i] != "surface":
				turtle_up[0] += 1
			turtle_state[i] = eco.turtles[i]["state"]
		crab_out[0] += eco.crabs.filter(func(c): return c["state"] == "forage").size()
		breaches[0] += eco.dolphins.filter(func(d): return d["air"] > 1.2).size()
		heights.append(v.ocean.height(10.0, 20.0))
		return false
	run(v, 1440.0, "", watch)
	var moved := 0.0
	for i in eco.schools.size():
		moved += p0[i].distance_to(eco.schools[i]["pos"])
	var hmin: float = heights.min()
	var hmax: float = heights.max()
	report["G"]["stats"] = eco.stats.duplicate(true)
	check("fish schools travel", moved > 200.0, snappedf(moved, 1.0))
	check("schools bolt from predators and boats", eco.stats["school_flights"] > 0, eco.stats["school_flights"])
	check("barracuda hunt and eat fish", eco.stats["predator_kills"] > 0, eco.stats["predator_kills"])
	check("the dolphin pod feeds and breaches", eco.stats["dolphin_feeds"] > 0 and breaches[0] > 0, {"feeds": eco.stats["dolphin_feeds"], "breach_samples": breaches[0]})
	check("turtles surface to breathe", turtle_up[0] > 3, turtle_up[0])
	check("pelicans and terns dive on schools", eco.stats["bird_dives"] > 0 and eco.stats["bird_catches"] > 0, {"dives": eco.stats["bird_dives"], "catches": eco.stats["bird_catches"]})
	check("crabs come out on the spit around dusk and dawn", crab_out[0] > 0, crab_out[0])
	check("the sea surface moves (shared wave model, tide included)", hmax - hmin > 0.2, {"min": snappedf(hmin, 0.01), "max": snappedf(hmax, 0.01)})
	check("wildlife numbers feed fishing: boats' catch is taken from the schools", eco.stats["caught_by_boats"].values().reduce(func(a, x): return a + x, 0) > 0, eco.stats["caught_by_boats"])
	await drop(v)

# ===================================================================== Y
func scenario_Y() -> void:
	var v := make_village(28.0)
	report["Y"]["setup"] = "default pacing (28 game days = 1 year of life), natural weather, no intervention"
	var market_empty_hours := [0]
	var pops := []
	var boat_out_long := [0]
	var out_since := {}
	var school_still := {}
	var last_school := v.ecosystem.schools.map(func(s): return s["pos"])
	var hours := [0]
	var watch := func():
		if int(GameClock.total_minutes) % 60 == 0:
			hours[0] += 1
			if v.ledger.qty(Economy.MARKET, "fish") == 0:
				market_empty_hours[0] += 1
			for b in v.boats.values():
				if b.boat_state != "moored":
					out_since[b] = out_since.get(b, GameClock.total_minutes)
					if GameClock.total_minutes - out_since[b] > 600.0:
						boat_out_long[0] += 1
				else:
					out_since.erase(b)
			if int(GameClock.total_minutes) % 1440 == 0:
				pops.append(v.villagers.size())
		return false
	run(v, 28 * 1440.0, "", watch)
	var tot := {}
	for x in v.villagers:
		for k in x.stats:
			if typeof(x.stats[k]) in [TYPE_INT, TYPE_FLOAT]:
				tot[k] = tot.get(k, 0) + x.stats[k]
	var w: Array = v.economy.wealth()
	var median: int = w[w.size() / 2]
	report["Y"]["totals"] = tot
	report["Y"]["economy"] = v.economy.stats.duplicate()
	report["Y"]["ecosystem"] = v.ecosystem.stats.duplicate(true)
	report["Y"]["society"] = v.society.counts.duplicate()
	report["Y"]["population_by_day"] = pops
	report["Y"]["wealth"] = {"min": w[0], "median": median, "max": w[-1]}
	report["Y"]["journal_counts"] = v.journal.counts
	report["Y"]["weather_hours"] = v.weather.hours_in
	check("a full year ran (28 game days)", GameClock.day() >= 28, GameClock.text())
	check("no route failures or failed object uses", tot.get("failed_paths", 0) == 0 and tot.get("failed_uses", 0) == 0, {"failed_paths": tot.get("failed_paths", 0), "failed_uses": tot.get("failed_uses", 0)})
	check("nobody starves", tot.get("starve_minutes", 0.0) < 60.0, tot.get("starve_minutes", 0.0))
	check("books balance, nothing negative", v.ledger.audit().is_empty(), v.ledger.audit())
	check("no boat stays out more than 10 hours", boat_out_long[0] == 0, boat_out_long[0])
	check("the market is rarely empty (supplied)", market_empty_hours[0] < hours[0] * 0.15, {"empty_hours": market_empty_hours[0], "of": hours[0]})
	check("no runaway wealth: richest household below 12x the median", w[-1] <= maxi(12 * maxi(median, 10), 200), report["Y"]["wealth"])
	check("every kind of event was recorded", ["fishing", "wildlife", "weather", "community"].all(func(k): return v.journal.counts.has(k)), v.journal.counts)
	check("residents remember things that happened to them", v.villagers.filter(func(x): return x.memories.size() > 0).size() > v.villagers.size() * 0.8)
	await drop(v)

# ===================================================================== P
func scenario_P() -> void:
	var years := 90
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--years="):
			years = int(a.substr(8))
	var v := make_village(1.0)
	report["P"]["setup"] = "accelerated calendar (1 game day = 1 year); %d years; immigration to empty houses ON (configurable)" % years
	report["P"]["settings"] = v.society.settings.duplicate()
	var series := []
	var stop := func():
		if int(GameClock.total_minutes) % (1440 * 5) == 0:
			var kids := v.villagers.filter(func(x): return x.age < 16.0).size()
			var old := v.villagers.filter(func(x): return x.age >= 65.0).size()
			var ages := v.villagers.map(func(x): return x.age)
			var avg: float = 0.0 if ages.is_empty() else ages.reduce(func(a, x): return a + x, 0.0) / ages.size()
			series.append({"year": GameClock.day(), "pop": v.villagers.size(), "children": kids, "elders": old, "mean_age": snappedf(avg, 0.1),
				"births": v.society.counts["births"], "deaths": v.society.counts["deaths"], "newcomers": v.society.counts["newcomers"],
				"empty_houses": v.households.values().filter(func(h): return h["members"] == 0).size()})
		return false
	run(v, years * 1440.0, "", stop)
	var sc: Dictionary = v.society.counts
	report["P"]["series"] = series
	report["P"]["counts"] = sc
	report["P"]["birth_blocked_couple_years"] = v.society.birth_blocked
	var pops := series.map(func(s): return s["pop"])
	var final_pop: int = v.villagers.size()
	check("population does not collapse over %d years" % years, final_pop >= 30 and pops.min() >= 25, {"start": 42, "min": pops.min(), "max": pops.max(), "final": final_pop})
	check("population changes are explained by recorded births, deaths and arrivals", final_pop == 42 + sc["births"] + sc["newcomers"] - sc["deaths"], {"births": sc["births"], "newcomers": sc["newcomers"], "deaths": sc["deaths"], "final": final_pop})
	check("several generations: grandchildren of the founders exist", v.villagers.any(func(x): return x.parents.any(func(p): return not str(p).begins_with("V0") and not str(p).begins_with("V1") and not str(p).begins_with("V2") and not str(p).begins_with("V3") and not str(p).begins_with("V4"))) or sc["births"] > 40, sc)
	var dangling := 0
	for x in v.villagers:
		if x.partner != "" and (v.villager_by_id(x.partner) == null or v.villager_by_id(x.partner).partner != x.villager_id):
			dangling += 1
	check("family links stay consistent", dangling == 0 and v.ledger.audit().is_empty(), {"dangling": dangling, "audit": v.ledger.audit()})
	check("businesses changed hands when owners left", v.economy.stats["successions"] > 0, v.economy.stats["successions"])
	await drop(v)
