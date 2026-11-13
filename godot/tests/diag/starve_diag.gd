extends Node
## Diagnostic: which residents go hungry in the accelerated 45-day generations run, and doing what.
func _ready() -> void:
	GameClock.reset(6.0)
	var v3 := Village.new()
	v3.with_presentation = false
	add_child(v3)
	v3.sim.auto = false
	v3.society.days_per_year = 1.0
	await get_tree().process_frame
	var hungry := {}
	for hour in int(45 * 24):
		v3.sim.advance(60.0)
		for v in v3.villagers:
			if v.needs["hunger"] >= 99.9:
				var k: String = v.villager_id
				if not hungry.has(k):
					hungry[k] = []
				hungry[k].append("d%d h%02d age%.0f %s/%s fsm=%s raw=%d purse=%d" % [GameClock.day(), int(GameClock.hour()), v.age, v.activity, str(v.plan.slice(0, 2)), v.fsm.current_name, v3.ledger.qty(v.hh, "fish"), v3.ledger.money(v.hh)])
	for k in hungry:
		var v = v3.villager_by_id(k)
		print("HUNGRY ", k, " starve_min=", v.stats["starve_minutes"] if v else "gone", " samples=", hungry[k].size())
		for s in hungry[k].slice(0, 12):
			print("    ", s)
		if v:
			print("    log: ", v.log.slice(-10))
	get_tree().quit()
