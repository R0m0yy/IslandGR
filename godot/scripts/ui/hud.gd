extends CanvasLayer
## Observer UI: clock / weather / speed strip, resident inspector, building
## inspector and village inspector. Text panels only for now - deliberately
## plain until the art direction for UI is agreed.

const SAVE_PATH = "user://living_tides_save.json"

var village = null
var top: Label
var panel: PanelContainer
var body: Label
var help: Label
var toast: Label
var show_village = false
var _t = 0.0
var _toast_t = 0.0

func _ready() -> void:
	top = _label(Vector2(14, 10), 15)
	add_child(top)
	panel = PanelContainer.new()
	panel.set_anchors_and_offsets_preset(Control.PRESET_TOP_RIGHT)
	panel.position = Vector2(-330, 12)
	panel.custom_minimum_size = Vector2(316, 0)
	var sb = StyleBoxFlat.new()
	sb.bg_color = Color(0.09, 0.11, 0.14, 0.78)
	sb.set_corner_radius_all(8)
	sb.set_content_margin_all(12)
	panel.add_theme_stylebox_override("panel", sb)
	body = Label.new()
	body.add_theme_font_size_override("font_size", 13)
	body.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	panel.add_child(body)
	add_child(panel)
	panel.visible = false
	help = _label(Vector2(14, -30), 12)
	help.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_LEFT)
	help.position += Vector2(14, -30)
	help.text = "LMB select · RMB orbit · wheel zoom · WASD pan · Tab next resident · B next boat · Esc release · C cutaway · I village · V figures · 1-4 speed · Space pause · F5 save · F9 load"
	add_child(help)
	toast = _label(Vector2(14, 40), 14)
	add_child(toast)

func _label(pos: Vector2, size: int) -> Label:
	var l = Label.new()
	l.position = pos
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.85))
	l.add_theme_constant_override("outline_size", 4)
	return l

func say(msg: String) -> void:
	toast.text = msg
	_toast_t = 4.0

func _unhandled_input(ev: InputEvent) -> void:
	if ev is InputEventKey and ev.pressed and not ev.echo and village:
		match ev.keycode:
			KEY_1: village.sim.time_scale = 1.0
			KEY_2: village.sim.time_scale = 4.0
			KEY_3: village.sim.time_scale = 16.0
			KEY_4: village.sim.time_scale = 60.0
			KEY_SPACE: village.sim.auto = not village.sim.auto
			KEY_I: show_village = not show_village
			KEY_V:
				village.set_figures_visible(not village.figures_visible)
				say("temporary figures %s" % ("shown" if village.figures_visible else "hidden"))
			KEY_F5:
				say("saved" if SaveGame.save(village, SAVE_PATH) else "save failed")
			KEY_F9:
				var d = SaveGame.load_file(SAVE_PATH)
				say("loaded" if SaveGame.apply(village, d) else "load failed: %s" % d.get("error", "?"))

func resident_text(v) -> String:
	var i: Dictionary = v.info()
	var n: Dictionary = i["needs"]
	var t = "%s  (%d)\n%s · %s\n\nNow: %s%s\n" % [i["name"], i["age"], i["job"], i["household"], i["activity"],
		(" → " + i["going_to"]) if i["going_to"] != "" else ""]
	t += "\nHunger %s\nThirst %s\nEnergy %s\nHygiene %s\nSocial %s\nMood %d   Health %d\n" % [_bar(n["hunger"], true), _bar(n["thirst"], true),
		_bar(n["energy"], false), _bar(n["hygiene"], false), _bar(n["social"], false), i["mood"], i["health"]]
	t += "\nHousehold purse %d · pantry %s\n" % [i["household_money"], str(i["pantry"])]
	var p = village.villager_by_id(i["partner"]) if i["partner"] != "" else null
	t += "Partner: %s · children: %d\n" % [p.display_name if p else "-", i["children"]]
	if not i["friends"].is_empty():
		t += "Friends: " + ", ".join(i["friends"].map(func(f): return "%s (%d)" % [f[1], int(f[0])])) + "\n"
	t += "\n" + "\n".join(i["recent"])
	return t

func _bar(x: float, bad_high: bool) -> String:
	var k = int(round(clampf(x, 0, 100) / 10.0))
	return "█".repeat(k) + "░".repeat(10 - k) + (" !" if (bad_high and x > 80.0) or (not bad_high and x < 20.0) else "")

func building_text(b: Building) -> String:
	var r: Dictionary = b.record
	var t = "%s  [%s]\n%s · %s storey(s)\n" % [r["name"], r["id"], r["kind"], str(r["storeys"])]
	if r.get("household") != null:
		var hh: String = r["household"]["id"]
		var names = village.villagers.filter(func(x): return x.hh == hh).map(func(x): return "%s (%d)" % [x.display_name, int(x.age)])
		t += "\nHousehold %s\nResidents: %s\nPurse %d · pantry %s\n" % [hh, ", ".join(names) if not names.is_empty() else "empty", village.ledger.money(hh), str(village.ledger.acc[hh]["items"])]
	if r.get("business") != null:
		var biz: String = r["business"]["id"]
		var staff = village.villagers.filter(func(x): return x.job != null and x.job["place"] == r["id"]).map(func(x): return "%s (%s)" % [x.display_name, x.job["role"]])
		t += "\nBusiness %s\nStaff: %s\nTill %d · stock %s\n" % [biz, ", ".join(staff) if not staff.is_empty() else "none", village.ledger.money(biz), str(village.ledger.acc[biz]["items"])]
	var inside = village.villagers.filter(func(x): return x.inside_building() == r["id"]).map(func(x): return "%s: %s" % [x.display_name, x.fsm.current_name])
	t += "\nInside now: %s\nLights %s · door %s\n" % [", ".join(inside) if not inside.is_empty() else "nobody", "on" if b.state.get("lights_on") else "off", "open" if b.state.get("door_open") else "closed"]
	return t

func village_text() -> String:
	var l: Ledger = village.ledger
	var employed = village.villagers.filter(func(x): return x.job != null).size()
	var kids = village.villagers.filter(func(x): return x.age < 16.0).size()
	var food = 0
	var purse = 0
	for hh in village.households:
		food += l.qty(hh, "fish") + l.qty(hh, "meal")
		purse += l.money(hh)
	var es: Dictionary = village.economy.stats
	var sc: Dictionary = village.society.counts
	var t = "VILLAGE\nPopulation %d (%d children) · households %d\nEmployed %d · open jobs %d\n" % [village.villagers.size(), kids, village.households.size(), employed, village.open_jobs.size()]
	t += "\nFood at home %d · market fish %d (buy %d / sell %d)\nEatery meals %d\n" % [food, l.qty(Economy.MARKET, "fish"), village.economy.fish_buy_price(), village.economy.fish_sell_price(), l.qty(Economy.EATERY, "meal")]
	t += "\nHousehold money %d · council %d · market %d\nWages paid %d (unpaid %d) · levy missed %d\n" % [purse, l.money(Economy.COUNCIL), l.money(Economy.MARKET), es["wages_paid"], es["wages_unpaid"], es["levy_missed"]]
	var out = village.boats.values().filter(func(b): return b.boat_state != "moored").size()
	t += "\nBoats at sea %d of %d · fish landed %d\n" % [out, village.boats.size(), es["fish_sold_to_market"] + es["fish_kept"]]
	t += "\nBirths %d · deaths %d · couples formed %d\n" % [sc["births"], sc["deaths"], sc["partnerships"]]
	for e in village.society.events.slice(-5):
		t += "  day %d: %s %s\n" % [int(e["day"]) + 1, e["type"], e["detail"]]
	return t

func _process(dt: float) -> void:
	_toast_t -= dt
	toast.visible = _toast_t > 0.0
	_t -= dt
	if _t > 0.0 or village == null:
		return
	_t = 0.25
	var w: Weather = village.weather
	top.text = "%s   ·   %s   ·   x%d%s" % [GameClock.text(), w.state, int(village.sim.time_scale), "" if village.sim.auto else "  (paused)"]
	var rig = village.camera_rig
	var txt = ""
	if rig and rig.follow and is_instance_valid(rig.follow) and rig.follow is Villager:
		txt = resident_text(rig.follow)
	elif rig and rig.selected_building:
		txt = building_text(rig.selected_building)
	elif show_village:
		txt = village_text()
	panel.visible = txt != ""
	body.text = txt
