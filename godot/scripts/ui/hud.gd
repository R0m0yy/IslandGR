extends CanvasLayer
## Observer UI. Everything shown is read from simulation state - nothing is
## written for display only. Panels: resident (with today's schedule, family,
## memories, finances), resident timeline, family tree, building / household,
## village, world journal. H hides everything.

const SAVE_PATH = "user://living_tides_save.json"

var village = null
var top: Label
var panel: PanelContainer
var body: Label
var side: PanelContainer
var side_body: Label
var help: Label
var toast: Label
var show_village = false
var view = "resident"               # resident | timeline | family
var journal_mode = 0                 # 0 off, 1 all, 2 notable, 3 followed resident
var hidden_ui = false
var _t = 0.0
var _toast_t = 0.0

func _ready() -> void:
	top = _label(Vector2(14, 10), 15)
	add_child(top)
	panel = _panel(Control.PRESET_TOP_RIGHT, Vector2(-350, 12), 336)
	body = panel.get_child(0)
	side = _panel(Control.PRESET_TOP_LEFT, Vector2(12, 44), 420)
	side_body = side.get_child(0)
	help = _label(Vector2(14, -30), 12)
	help.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_LEFT)
	help.position += Vector2(14, -30)
	help.text = "LMB select · RMB orbit · wheel zoom · WASD pan · Q/E rotate · Tab resident · G family · B boat · N wildlife · K cinematic · T timeline · F family tree · J journal · I village · C cutaway · V figures · H hide UI · 1-4 speed · Space pause · F5/F9 save/load"
	add_child(help)
	toast = _label(Vector2(14, 34), 14)
	add_child(toast)

func _panel(preset: int, pos: Vector2, w: float) -> PanelContainer:
	var p := PanelContainer.new()
	p.set_anchors_and_offsets_preset(preset)
	p.position = pos
	p.custom_minimum_size = Vector2(w, 0)
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.09, 0.11, 0.14, 0.76)
	sb.set_corner_radius_all(8)
	sb.set_content_margin_all(12)
	p.add_theme_stylebox_override("panel", sb)
	var l := Label.new()
	l.add_theme_font_size_override("font_size", 13)
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	l.custom_minimum_size = Vector2(w - 24, 0)
	p.add_child(l)
	p.visible = false
	add_child(p)
	return p

func _label(pos: Vector2, size: int) -> Label:
	var l := Label.new()
	l.position = pos
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.85))
	l.add_theme_constant_override("outline_size", 4)
	return l

func attach() -> void:
	village.journal.added.connect(func(e):
		if e["notable"]:
			say("★ " + e["text"]))

func say(msg: String) -> void:
	toast.text = msg
	_toast_t = 5.0

func _unhandled_input(ev: InputEvent) -> void:
	if ev is InputEventKey and ev.pressed and not ev.echo and village:
		match ev.keycode:
			KEY_1: village.sim.time_scale = 1.0
			KEY_2: village.sim.time_scale = 4.0
			KEY_3: village.sim.time_scale = 16.0
			KEY_4: village.sim.time_scale = 60.0
			KEY_SPACE: village.sim.auto = not village.sim.auto
			KEY_I: show_village = not show_village
			KEY_H: hidden_ui = not hidden_ui
			KEY_J: journal_mode = (journal_mode + 1) % 4
			KEY_T: view = "resident" if view == "timeline" else "timeline"
			KEY_F: view = "resident" if view == "family" else "family"
			KEY_V:
				village.set_figures_visible(not village.figures_visible)
				say("temporary figures %s" % ("shown" if village.figures_visible else "hidden"))
			KEY_F5:
				say("saved" if SaveGame.save(village, SAVE_PATH) else "save failed")
			KEY_F9:
				var d = SaveGame.load_file(SAVE_PATH)
				say("loaded" if SaveGame.apply(village, d) else "load failed: %s" % d.get("error", "?"))

# ------------------------------------------------------------------ resident
func _bar(x: float, bad_high: bool) -> String:
	var k = int(round(clampf(x, 0, 100) / 10.0))
	return "█".repeat(k) + "░".repeat(10 - k) + (" !" if (bad_high and x > 80.0) or (not bad_high and x < 20.0) else "")

func stage(age: float) -> String:
	if age < 5.0: return "infant"
	if age < 16.0: return "child"
	if age < 65.0: return "adult"
	return "elder"

func resident_text(v) -> String:
	var i: Dictionary = v.info()
	var n: Dictionary = i["needs"]
	var debt = int(village.economy.debts.get(v.hh, 0))
	var t = "%s, %d (%s)%s\n%s · %s\n" % [i["name"], i["age"], stage(v.age), "  · ill" if i["sick"] else "", i["job"], village.household_name(v.hh)]
	t += "\nNow: %s (%s)%s\n" % [i["activity"], i["state"], ("  → " + _place(i["going_to"])) if i["going_to"] != "" else ""]
	t += "Today:\n"
	var today = v.log.filter(func(l): return l.begins_with("Day %d " % (GameClock.day() + 1)))
	for l in today.slice(-6):
		t += "  " + l.substr(l.find(" ", 5) + 1) + "\n"
	var nxt = v.plan.map(func(st): return "go " + _place(st["go"]) if st.has("go") else (st.get("state", "") if st.has("use") else ("gift" if st.has("gift") else "wait")))
	if not nxt.is_empty():
		t += "  next: " + ", ".join(nxt) + "\n"
	t += "\nHunger %s\nThirst %s\nEnergy %s\nHygiene %s\nSocial %s\nMood %d · Health %d\n" % [_bar(n["hunger"], true), _bar(n["thirst"], true),
		_bar(n["energy"], false), _bar(n["hygiene"], false), _bar(n["social"], false), i["mood"], i["health"]]
	t += "\nPurse %d%s · pantry %s\n" % [i["household_money"], (" · owes %d" % debt) if debt > 0 else "", _items(i["pantry"])]
	var sk = i["skills"]
	t += "Skills: fishing %d · cooking %d · trade %d · carpentry %d\n" % [int(sk["fishing"] * 100), int(sk["cooking"] * 100), int(sk["trade"] * 100), int(sk["carpentry"] * 100)]
	var tr = i["traits"]
	t += "Leans to %s · %s, %s\n" % [i["ambition"], "generous" if tr["generosity"] > 0.6 else ("careful with money" if tr["generosity"] < 0.3 else "fair"), "bold" if tr["boldness"] > 0.6 else ("cautious" if tr["boldness"] < 0.3 else "steady")]
	t += "\nPartner: %s\n" % (village.person_name(i["partner"]) if i["partner"] != "" else "-")
	if not i["kids"].is_empty():
		t += "Children: %s\n" % ", ".join(i["kids"].map(func(c): return village.person_name(c) + ("" if village.is_alive(c) else " †")))
	if not i["friends"].is_empty():
		t += "Friends: " + ", ".join(i["friends"].map(func(f): return "%s (%d)" % [f[1], int(f[0])])) + "\n"
	if not i["memories"].is_empty():
		t += "\nRemembers:\n"
		for m in i["memories"].slice(-4):
			t += "  day %d: %s\n" % [int(m["day"]) + 1, m["text"]]
	return t

func _items(d: Dictionary) -> String:
	var parts = []
	for k in d:
		if int(d[k]) > 0:
			parts.append("%d %s" % [int(d[k]), k])
	return ", ".join(parts) if not parts.is_empty() else "empty"

func _place(node: String) -> String:
	if node.begins_with("door_"):
		var b = node.substr(5)
		return village.buildings[b].record["name"] if village.buildings.has(b) else b
	var i = node.find(":")
	if i > 0:
		var b2 = node.substr(0, i)
		return (village.buildings[b2].record["name"] if village.buildings.has(b2) else b2) + " (inside)"
	return node.replace("_", " ")

func timeline_text(v) -> String:
	var t = "%s — life so far\n" % v.display_name
	var pe = village.people.get(v.villager_id, {})
	t += "Arrived day %d aged %d\n\n" % [int(pe.get("arrived_day", 0)) + 1, int(pe.get("age_at_arrival", v.age))]
	var es = village.journal.of_actor(v.villager_id, 40)
	es.reverse()
	for e in es.slice(-18):
		t += "%s  %s\n" % [Journal.stamp(e), e["text"]]
	return t

func family_text(v) -> String:
	var id: String = v.villager_id
	var t = "Family of %s\n\n" % v.display_name
	var gps = []
	for p in village.parents_of(id):
		for gp in village.parents_of(p):
			gps.append(_who(gp))
	if not gps.is_empty():
		t += "Grandparents: %s\n" % ", ".join(gps)
	var ps = village.parents_of(id).map(func(p): return _who(p))
	t += "Parents: %s\n" % (", ".join(ps) if not ps.is_empty() else "came from along the coast")
	var sibs = []
	for p in village.parents_of(id):
		for c in village.children_of(p):
			if c != id and not sibs.has(c):
				sibs.append(c)
	if not sibs.is_empty():
		t += "Brothers and sisters: %s\n" % ", ".join(sibs.map(func(c): return _who(c)))
	t += "Partner: %s\n" % (_who(v.partner) if v.partner != "" else "-")
	for c in village.children_of(id):
		t += "  child %s\n" % _who(c)
		for g in village.children_of(c):
			t += "    grandchild %s\n" % _who(g)
	var hh = v.hh
	var house = village.journal.entries.filter(func(e): return e["actors"].any(func(a): var x = village.villager_by_id(a); return x != null and x.hh == hh) and e["type"] in ["birth", "death", "partnership", "moved", "hired", "newcomers", "community", "estate"])
	t += "\nHousehold history\n"
	for e in house.slice(-8):
		t += "%s  %s\n" % [Journal.stamp(e), e["text"]]
	return t

func _who(id: String) -> String:
	var v = village.villager_by_id(id)
	if v:
		return "%s (%d)" % [v.display_name, int(v.age)]
	var pe = village.people.get(id, {})
	if pe.is_empty():
		return id
	return "%s (†%d)" % [pe["name"], int(pe.get("age_at_death", 0))] if int(pe.get("died_day", -1)) >= 0 else pe["name"]

# ------------------------------------------------------------------ building / village / journal
func building_text(b: Building) -> String:
	var r: Dictionary = b.record
	var t = "%s  [%s]\n%s · %s storey(s) · condition %d%%\n" % [r["name"], r["id"], r["kind"], str(r["storeys"]), int(b.state.get("condition", 1.0) * 100)]
	var l: Ledger = village.ledger
	if r.get("household") != null:
		var hh: String = r["household"]["id"]
		var names = village.villagers.filter(func(x): return x.hh == hh).map(func(x): return "%s (%d)" % [x.display_name, int(x.age)])
		t += "\n%s\nResidents: %s\nPurse %d · pantry %s\n" % [village.household_name(hh), ", ".join(names) if not names.is_empty() else "empty", l.money(hh), _items(l.acc[hh]["items"])]
	if r.get("business") != null:
		var biz: String = r["business"]["id"]
		var owner = village.economy.owners.get(biz, "")
		var staff = village.villagers.filter(func(x): return x.job != null and x.job["place"] == r["id"]).map(func(x): return "%s (%s)" % [x.display_name, x.job["role"]])
		t += "\nBusiness · owner %s\nStaff: %s\nTill %d · stock %s%s\n" % [village.person_name(owner) if owner != "" else "none", ", ".join(staff) if not staff.is_empty() else "none",
			l.money(biz), _items(l.acc[biz]["items"]), "\nStruggling: %d lean days" % int(village.economy.lean_days.get(biz, 0)) if int(village.economy.lean_days.get(biz, 0)) > 0 else ""]
	var inside = village.villagers.filter(func(x): return x.inside_building() == r["id"]).map(func(x): return "%s: %s" % [x.display_name, x.fsm.current_name])
	t += "\nInside now: %s\nLights %s · door %s\n" % [", ".join(inside) if not inside.is_empty() else "nobody", "on" if b.state.get("lights_on") else "off", "open" if b.state.get("door_open") else "closed"]
	return t

func village_text() -> String:
	var l: Ledger = village.ledger
	var vs: Array = village.villagers
	var kids = vs.filter(func(x): return x.age < 16.0).size()
	var elders = vs.filter(func(x): return x.age >= 65.0).size()
	var food = 0
	for hh in village.households:
		food += l.qty(hh, "fish") + l.qty(hh, "meal")
	var es: Dictionary = village.economy.stats
	var sc: Dictionary = village.society.counts
	var eco = village.ecosystem
	var w: Array = village.economy.wealth()
	var t = "SALTCROWN\nPopulation %d · %d children · %d elders · %d households\n" % [vs.size(), kids, elders, village.households.values().filter(func(h): return h["members"] > 0).size()]
	t += "Employed %d · open jobs %d\n" % [vs.filter(func(x): return x.job != null).size(), village.open_jobs.size()]
	t += "\nFood in homes %d · market %d fish (buys %d / sells %d) · eatery %d meals\n" % [food, l.qty(Economy.MARKET, "fish"), village.economy.fish_buy_price(), village.economy.fish_sell_price(), l.qty(Economy.EATERY, "meal")]
	t += "Shop bait %d · scrap heap %d\n" % [l.qty(Economy.STORE, "bait"), l.qty(Economy.SCRAPS, "fish")]
	if not w.is_empty():
		t += "Household wealth: poorest %d · median %d · richest %d\n" % [w[0], w[w.size() / 2], w[-1]]
	t += "Debts at the market: %d · gifts given %d\n" % [village.economy.debts.values().reduce(func(a, x): return a + x, 0), es["gifts"]]
	t += "\nBoats at sea %d of %d · fish in the sea ~%d\n" % [village.boats.values().filter(func(b): return b.boat_state != "moored").size(), village.boats.size(), int(eco.total_fish())]
	t += "Gull thefts %d · scavenged %d · bird dives %d\n" % [eco.stats["thefts"], eco.stats["scavenged"], eco.stats["bird_dives"]]
	t += "\nWeather %s · storm risk next 4 h %d%%\n" % [village.weather.state.replace("_", " "), int(village.weather.storm_risk() * 100)]
	if village.day_night:
		t += "Moon: %s\n" % village.day_night.phase_name()
	t += "\nBirths %d · deaths %d · couples %d · newcomers %d\n" % [sc["births"], sc["deaths"], sc["partnerships"], sc["newcomers"]]
	return t

func journal_text() -> String:
	var j: Journal = village.journal
	var rig = village.camera_rig
	var es: Array
	var title = "JOURNAL — all events"
	if journal_mode == 2:
		es = j.recent(16, true)
		title = "JOURNAL — notable"
	elif journal_mode == 3 and rig and rig.follow is Villager:
		es = j.of_actor(rig.follow.villager_id, 16)
		title = "JOURNAL — " + rig.follow.display_name
	else:
		es = j.recent(16)
	var t = title + "\n"
	for e in es:
		t += "%s%s  %s\n" % ["★ " if e["notable"] else "", Journal.stamp(e), e["text"]]
	return t

func _process(dt: float) -> void:
	_toast_t -= dt
	toast.visible = _toast_t > 0.0 and not hidden_ui
	help.visible = not hidden_ui
	top.visible = not hidden_ui
	_t -= dt
	if _t > 0.0 or village == null:
		return
	_t = 0.25
	var w: Weather = village.weather
	var rig = village.camera_rig
	var mode = rig.mode_text() if rig else ""
	top.text = "%s   ·   %s   ·   x%d%s%s" % [GameClock.text(), w.state.replace("_", " "), int(village.sim.time_scale), "" if village.sim.auto else "  (paused)", ("   ·   " + mode) if mode != "" else ""]
	var txt = ""
	if rig and rig.follow and is_instance_valid(rig.follow) and rig.follow is Villager:
		txt = timeline_text(rig.follow) if view == "timeline" else (family_text(rig.follow) if view == "family" else resident_text(rig.follow))
	elif rig and rig.selected_building:
		txt = building_text(rig.selected_building)
	elif show_village:
		txt = village_text()
	panel.visible = txt != "" and not hidden_ui
	body.text = txt
	side.visible = journal_mode > 0 and not hidden_ui
	if side.visible:
		side_body.text = journal_text()
