extends Node
## Diagnostic: where the money sits after N days, wage claims by employer, household spending.
func _ready() -> void:
	var days := 7
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--days="):
			days = int(a.substr(7))
	GameClock.reset(6.0)
	var v := Village.new()
	v.with_presentation = false
	add_child(v)
	v.sim.auto = false
	await get_tree().process_frame
	for d in days:
		v.sim.advance(1440.0)
		var hh_money := 0
		var biz := {}
		for k in v.ledger.acc:
			var m: int = v.ledger.money(k)
			if k.begins_with("HH_"):
				hh_money += m
			elif m != 0:
				biz[k] = m
		print("DAY ", d + 1, " households=", hh_money, " others=", biz, " owed=", v.economy.arrears_total())
	var e: Dictionary = v.economy.stats
	print("STATS ", e)
	print("UNPAID_BY ", v.economy.unpaid_by)
	print("ARREARS ", v.economy.arrears)
	var t: Dictionary = v.ledger.totals
	for k in t:
		if t[k].get("money", 0) > 0:
			print("FLOW ", k, " ", t[k])
	var rich := []
	for hh in v.households:
		rich.append(v.ledger.money(hh))
	rich.sort()
	print("HH_MONEY ", rich)
	get_tree().quit()
