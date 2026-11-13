class_name Economy
extends RefCounted
## Village economy rules on top of the Ledger. Closed loop:
##   sea -> fish (boats, hand lines) -> market / pantries -> meals -> eaten
##   households -> levy -> council -> wages of non-trading workplaces -> households
##   market and eatery pay their own wages out of what they earn
## Prices move with market stock. Nothing here creates money.

const COUNCIL := "council"
const MARKET := "BIZ_P01"
const EATERY := "BIZ_P06"
const BOATYARD := "BIZ_P02"
const STORE := "BIZ_P05"
const NETLOFT := "BIZ_P04"
const CARPENTER := "BIZ_P07"
const BAIT_PRICE := 2
const REPAIR_PRICE := 8
const CREDIT_LIMIT := 18
const SCRAPS := "scraps"           # the harbour scrap heap: spoiled fish thrown out, scavenged by gulls
const HOME_KEEP := 4               # raw fish a household can keep fresh (salted / in the cool)
const MARKET_KEEP := 25            # what the market's ice box holds
const WAGE := 4
const LEVY := 6
const MEAL_PRICE := 4
const MEALS_PER_FISH := 3

var ledger: Ledger
var village = null
var stats := {"wages_paid": 0, "wages_unpaid": 0, "levy_paid": 0, "levy_missed": 0, "fish_sold_to_market": 0,
	"fish_kept": 0, "fish_bought": 0, "meals_sold": 0, "repairs": 0, "repairs_unaffordable": 0, "bait_made": 0, "bait_sold": 0, "credit_sales": 0, "credit_repaid": 0,
	"gifts": 0, "gift_items": 0, "spoiled_home": 0, "spoiled_market": 0, "rotted": 0, "bait_cut": 0, "house_repairs": 0, "house_repairs_unpaid": 0, "successions": 0,
	"consigned": 0, "payables_settled": 0, "stall_rent": 0, "stall_rent_missed": 0,
	"levy_waived_days": 0, "subsidised_wages": 0, "handline_sold": 0}
const COUNCIL_RESERVE := 250          # above this the council waives levy and rent and props up wages
var _waiving := false
var unpaid_by: Dictionary = {}
const STALL_RENT := {"BIZ_P01": 8, "BIZ_P06": 4, "BIZ_P05": 4}
const MARKET_ROOM := 35             # fish the market will take in (ice box + the day's slab)
var debts: Dictionary = {}            # household -> money owed to the market
var payables: Dictionary = {}         # fisher household -> money the market owes for fish taken on consignment
var _payable_order: Array = []        # oldest first
var favours: Dictionary = {}          # "giver_hh|receiver_hh" -> items given (remembered kindness)
var owners: Dictionary = {}           # business id -> villager id
var lean_days: Dictionary = {}        # business id -> consecutive days it could not pay a wage
var _day: int = -1

func setup(v, l: Ledger) -> void:
	village = v
	ledger = l
	ledger.open(COUNCIL, 500)
	ledger.open(SCRAPS, 0)
	for id in village.buildings:
		var rec: Dictionary = village.buildings[id].record
		if rec.get("business") != null:
			var start := 0
			if rec["business"]["id"] == MARKET:
				start = 200
			elif rec["business"]["id"] == EATERY:
				start = 80
			elif rec["business"]["id"] == STORE:
				start = 60
			ledger.open(rec["business"]["id"], start)
		if rec.get("household") != null:
			ledger.open(rec["household"]["id"], 60)
	var pantry: Dictionary = VillageDB.population.get("start_pantry", {})
	for hh in village.households:
		if int(pantry.get("raw_fish", 0)) > 0:
			ledger.mint(hh, "fish", int(pantry["raw_fish"]), "start_stock")
		if int(pantry.get("meals", 0)) > 0:
			ledger.mint(hh, "meal", int(pantry["meals"]), "start_stock")
	ledger.mint(MARKET, "fish", 6, "start_stock")
	ledger.mint(STORE, "bait", 12, "start_stock")

var _flow := {"in": [], "out": []}        # [hour, n] buckets of fish into and out of the market

func _flow_add(kind: String, n: int) -> void:
	var h := int(GameClock.total_minutes / 60.0)
	var b: Array = _flow[kind]
	if b.is_empty() or b[-1][0] != h:
		b.append([h, 0])
	b[-1][1] += n
	while not b.is_empty() and b[0][0] < h - 24:
		b.pop_front()

func flow24(kind: String) -> int:
	var h := int(GameClock.total_minutes / 60.0)
	var t := 0
	for e in _flow[kind]:
		if e[0] >= h - 24:
			t += int(e[1])
	return t

func fish_sell_price() -> int:
	## Supply and demand: what is on the slab sets the base, and the last day's
	## flow moves it - selling faster than fish comes in pushes the price up.
	var base := 9.0 - ledger.qty(MARKET, "fish") / 7.0
	var scarcity := clampf((flow24("out") + 6.0) / (flow24("in") + 6.0), 0.7, 1.7)
	return clampi(int(round(base * scarcity)), 3, 10)

func fish_buy_price() -> int:
	## What the market pays a fisher: always below its selling price.
	return maxi(2, fish_sell_price() - 2)

func daily(day: int) -> void:
	if day == _day:
		return
	_day = day
	var waive: bool = ledger.money(COUNCIL) > COUNCIL_RESERVE
	if waive != _waiving:
		_waiving = waive
		village.journal.add("economy", [], "The council %s the household levy and stall rents (reserve %d)." % ["waived" if waive else "restored", ledger.money(COUNCIL)], "council reserve %s %d" % [">" if waive else "<=", COUNCIL_RESERVE])
	if waive:
		stats["levy_waived_days"] += 1
	for hh in village.households:
		if village.households[hh].get("members", 0) <= 0 or waive:
			continue
		# harbour dues by means: a flat part plus a share of what the household holds above 60
		var due: int = LEVY / 2 + int(maxf(0.0, ledger.money(hh) - 60.0) * 0.03)
		if ledger.pay(hh, COUNCIL, due, "levy"):
			stats["levy_paid"] += 1
		else:
			stats["levy_missed"] += 1
		# settle the slate at the market once there is money to spare
		var owed: int = int(debts.get(hh, 0))
		if owed > 0 and ledger.money(hh) >= owed + 12 and ledger.pay(hh, MARKET, owed, "credit_repaid"):
			debts.erase(hh)
			settle_payables()
			stats["credit_repaid"] += owed
			village.journal.add("economy", [], "%s settled a debt of %d at the fish market." % [village.household_name(hh), owed], "money to spare")
	_spoilage()
	for biz in STALL_RENT:
		if waive:
			break
		if ledger.pay(biz, COUNCIL, STALL_RENT[biz], "stall_rent"):
			stats["stall_rent"] += STALL_RENT[biz]
		else:
			stats["stall_rent_missed"] += 1
	for biz in [MARKET, EATERY, STORE]:
		if ledger.money(biz) < WAGE:
			lean_days[biz] = int(lean_days.get(biz, 0)) + 1
			if lean_days[biz] == 4:
				village.journal.add("economy", [], "%s is struggling: four days without the money for a wage." % village.business_name(biz), "till empty", true)
		else:
			if int(lean_days.get(biz, 0)) >= 4:
				village.journal.add("economy", [], "%s is back on its feet." % village.business_name(biz), "till recovered")
			lean_days[biz] = 0

func employer_account(v) -> String:
	var biz := "BIZ_" + String(v.job["place"])
	if biz == MARKET:
		# the market pays the fishermen it owes before it pays its own staff
		return MARKET if ledger.money(MARKET) - owed_to_fishers() >= WAGE else ""
	if biz in [EATERY, BOATYARD, STORE, NETLOFT, CARPENTER]:
		return biz if ledger.money(biz) >= WAGE else ""
	return COUNCIL

func owed_to_fishers() -> int:
	var t := 0
	for k in payables:
		t += int(payables[k])
	return t

func settle_payables() -> void:
	## Money that comes into the market goes first to the fishermen it owes.
	while not _payable_order.is_empty():
		var hh: String = _payable_order[0]
		var owed: int = int(payables.get(hh, 0))
		var can: int = mini(owed, ledger.money(MARKET))
		if can <= 0:
			if owed <= 0:
				_payable_order.pop_front()
				payables.erase(hh)
				continue
			return
		ledger.pay(MARKET, hh, can, "consignment_paid")
		stats["payables_settled"] += can
		payables[hh] = owed - can
		if int(payables[hh]) <= 0:
			payables.erase(hh)
			_payable_order.pop_front()

func work_done(v, obj) -> void:
	## Called when a work block ends: production first, then the wage.
	var biz := "BIZ_" + String(v.job["place"])
	if biz == EATERY:
		# the eatery buys fish at the market price and turns it into meals
		for i in 2:
			if ledger.qty(EATERY, "fish") < 1 and ledger.qty(MARKET, "fish") > 0:
				var p := fish_sell_price()
				if ledger.money(EATERY) >= p and ledger.move(MARKET, EATERY, "fish", 1, "eatery_supply"):
					_flow_add("out", 1)
					ledger.pay(EATERY, MARKET, p, "eatery_supply")
					settle_payables()
			if ledger.qty(EATERY, "meal") < 12 and ledger.consume(EATERY, "fish", 1, "eatery_cook"):
				ledger.mint(EATERY, "meal", MEALS_PER_FISH, "eatery_cook")
	if biz == NETLOFT:
		ledger.mint(NETLOFT, "bait", 4, "net_loft_made")           # lines, hooks and bait made up for the boats
		stats["bait_made"] += 4
	if biz == STORE:
		for i in 4:                                              # the shop restocks from the net loft
			if ledger.qty(STORE, "bait") < 16 and ledger.qty(NETLOFT, "bait") > 0 and ledger.money(STORE) >= 1:
				ledger.move(NETLOFT, STORE, "bait", 1, "store_supply")
				ledger.pay(STORE, NETLOFT, 1, "store_supply")
	var main_skill: String = {"fisher": "fishing", "cook": "cooking", "carpenter": "carpentry", "apprentice": "carpentry", "boatwright": "carpentry"}.get(v.job["role"], "trade")
	v.skills[main_skill] = minf(1.0, v.skills[main_skill] + 0.004)
	var payer := employer_account(v)
	if payer == "" and ledger.money(COUNCIL) > COUNCIL_RESERVE:
		payer = COUNCIL                                   # the village keeps its shops staffed when trade is thin
		stats["subsidised_wages"] += 1
	if payer != "" and ledger.pay(payer, v.hh, WAGE, "wage"):
		stats["wages_paid"] += 1
		v.stats["wages"] += WAGE
	else:
		stats["wages_unpaid"] += 1
		unpaid_by[v.job["place"]] = int(unpaid_by.get(v.job["place"], 0)) + 1

func land_catch(v, boat: Boat) -> void:
	## Unload a boat: sell to the market while it can pay and has room; the rest goes home.
	var n := ledger.qty(boat.object_id, "fish")
	var consigned := 0
	var home_need: int = maxi(0, 2 * village.households[v.hh]["members"] - ledger.qty(v.hh, "fish"))
	for i in n:
		var p := fish_buy_price()
		if home_need > 0:
			# a fisherman keeps enough for his own table first
			ledger.move(boat.object_id, v.hh, "fish", 1, "landing_home")
			stats["fish_kept"] += 1
			home_need -= 1
		elif ledger.qty(MARKET, "fish") < MARKET_ROOM and ledger.money(MARKET) - owed_to_fishers() >= p:
			ledger.move(boat.object_id, MARKET, "fish", 1, "landing_sale")
			_flow_add("in", 1)
			ledger.pay(MARKET, v.hh, p, "landing_sale")
			stats["fish_sold_to_market"] += 1
			v.stats["income"] += p
		elif ledger.qty(MARKET, "fish") < MARKET_ROOM:
			# the till is short: the market takes the fish on account and pays as it sells
			ledger.move(boat.object_id, MARKET, "fish", 1, "landing_consigned")
			_flow_add("in", 1)
			if not payables.has(v.hh):
				_payable_order.append(v.hh)
			payables[v.hh] = int(payables.get(v.hh, 0)) + p
			stats["consigned"] += 1
			consigned += 1
		else:
			ledger.move(boat.object_id, v.hh, "fish", 1, "landing_home")
			stats["fish_kept"] += 1
	if consigned > 0:
		village.journal.add("economy", [v.villager_id], "The market took %d of %s's fish on account - its till was short." % [consigned, v.display_name], "market owes fishermen %d" % owed_to_fishers())
	boat.landed += n
	if boat.condition < Boat.REPAIR_BELOW:
		if ledger.pay(v.hh, BOATYARD, Boat.REPAIR_COST, "boat_repair"):
			boat.condition = 1.0
			stats["repairs"] += 1
		else:
			stats["repairs_unaffordable"] += 1

func _spoilage() -> void:
	## Fresh fish does not keep. Each dawn half of what a larder holds beyond
	## HOME_KEEP goes off, and the market's stock beyond its ice box loses a third.
	## Spoiled fish is carried to the scrap heap (it still exists - gulls eat it).
	for hh in village.households:
		var q := ledger.qty(hh, "fish")
		if q > HOME_KEEP:
			var n := (q - HOME_KEEP + 1) / 2
			ledger.move(hh, SCRAPS, "fish", n, "spoiled_thrown_out")
			stats["spoiled_home"] += n
	var mq := ledger.qty(MARKET, "fish")
	if mq > MARKET_KEEP:
		var n2 := (mq - MARKET_KEEP + 2) / 3
		ledger.move(MARKET, SCRAPS, "fish", n2, "market_spoilage")
		stats["spoiled_market"] += n2
	var sq := ledger.qty(SCRAPS, "fish")
	if sq > 0:
		var r := (sq + 1) / 2                                    # what the gulls leave rots away
		ledger.consume(SCRAPS, "fish", r, "rotted")
		stats["rotted"] += r

func cut_bait(v) -> bool:
	## No bait in the shop: a fisher cuts his own from a fish at home.
	if not ledger.consume(v.hh, "fish", 1, "cut_bait"):
		return false
	ledger.mint(v.hh, "bait", 3, "cut_bait")
	stats["bait_cut"] += 1
	return true

func credit_ok(hh: String) -> bool:
	return int(debts.get(hh, 0)) + fish_sell_price() <= CREDIT_LIMIT

func buy_fish(v) -> int:
	var got := 0
	for i in 2:
		var p := fish_sell_price()
		if ledger.money(v.hh) >= p and ledger.move(MARKET, v.hh, "fish", 1, "market_sale"):
			ledger.pay(v.hh, MARKET, p, "market_sale")
			_flow_add("out", 1)
			got += 1
		elif ledger.money(v.hh) < p and credit_ok(v.hh) and ledger.move(MARKET, v.hh, "fish", 1, "market_credit"):
			_flow_add("out", 1)
			# on the slate: the fish changes hands now, the money is owed
			debts[v.hh] = int(debts.get(v.hh, 0)) + p
			stats["credit_sales"] += 1
			got += 1
			v.remember("credit", "the market let us have fish on credit", 3.0)
			village.journal.add("community", [v.villager_id], "The fish market let %s take a fish on credit (%d owed)." % [v.display_name, debts[v.hh]], "empty purse, trusted household")
	stats["fish_bought"] += got
	if got > 0:
		settle_payables()
	return got

func buy_meal(v) -> bool:
	if ledger.money(v.hh) >= MEAL_PRICE and ledger.qty(EATERY, "meal") > 0:
		ledger.pay(v.hh, EATERY, MEAL_PRICE, "eatery_sale")
		ledger.consume(EATERY, "meal", 1, "eaten_out")
		stats["meals_sold"] += 1
		return true
	if v.needs["hunger"] >= 85.0 and food_of(v.hh) == 0 and ledger.qty(EATERY, "meal") > 0:
		# nobody goes hungry with the eatery open: a meal on the house for someone with nothing
		ledger.consume(EATERY, "meal", 1, "charity_meal")
		stats["charity_meals"] = int(stats.get("charity_meals", 0)) + 1
		v.remember("charity", "the eatery fed us when we had nothing", 4.0)
		village.journal.add("community", [v.villager_id], "The eatery gave %s a meal on the house." % v.display_name, "hungry, empty larder, empty purse")
		return true
	return false

func buy_bait(v) -> int:
	var got := 0
	for i in 3:
		if ledger.money(v.hh) >= BAIT_PRICE and ledger.move(STORE, v.hh, "bait", 1, "store_sale"):
			ledger.pay(v.hh, STORE, BAIT_PRICE, "store_sale")
			got += 1
	stats["bait_sold"] += got
	return got

func food_of(hh: String) -> int:
	return ledger.qty(hh, "fish") + ledger.qty(hh, "meal")

func give(v, to_hh: String, item: String, n: int) -> void:
	## A gift between households: the goods really move, and it is remembered.
	n = mini(n, ledger.qty(v.hh, item))
	if n <= 0 or not ledger.move(v.hh, to_hh, item, n, "gift"):
		return
	stats["gifts"] += 1
	stats["gift_items"] += n
	v.stats["gifts_given"] += n
	var k: String = v.hh + "|" + to_hh
	favours[k] = int(favours.get(k, 0)) + n
	var names := []
	for o in village.villagers:
		if o.hh == to_hh:
			o.stats["gifts_received"] += n
			o.remember("kindness", "%s brought us %d %s when we had nothing" % [v.display_name, n, item], 8.0)
			var bk: String = Society.key(v.villager_id, o.villager_id)
			village.society.bonds[bk] = minf(100.0, village.society.bonds.get(bk, 0.0) + 9.0)
			names.append(o.villager_id)
	v.remember("kindness", "took %d %s round to %s" % [n, item, village.household_name(to_hh)], 4.0)
	village.journal.add("community", [v.villager_id] + names, "%s brought %d %s to %s, who had run out of food." % [v.display_name, n, item, village.household_name(to_hh)],
		"neighbour in need; %s had %d to spare" % [v.display_name, ledger.qty(v.hh, item) + n], true, v.global_position)

func repair_building(v, bid: String) -> void:
	var b = village.buildings[bid]
	if b.state.get("condition", 1.0) >= 1.0:
		return
	b.state["condition"] = 1.0
	stats["house_repairs"] += 1
	v.stats["repairs_done"] += 1
	v.skills["carpentry"] = minf(1.0, v.skills["carpentry"] + 0.01)
	var payer := ""
	if b.record.get("household") != null:
		payer = b.record["household"]["id"]
	elif b.record.get("business") != null:
		payer = COUNCIL
	if payer != "" and ledger.pay(payer, CARPENTER, REPAIR_PRICE, "storm_repair"):
		village.journal.add("repair", [v.villager_id], "%s mended the storm damage at %s." % [v.display_name, b.record["name"]], "storm damage; paid %d" % REPAIR_PRICE)
	else:
		stats["house_repairs_unpaid"] += 1
		village.journal.add("community", [v.villager_id], "%s mended the storm damage at %s without charge - the household could not pay." % [v.display_name, b.record["name"]], "storm damage; empty purse", true)
		for o in village.villagers:
			if payer != "" and o.hh == payer:
				o.remember("kindness", "%s fixed our roof for nothing" % v.display_name, 8.0)
				var bk: String = Society.key(v.villager_id, o.villager_id)
				village.society.bonds[bk] = minf(100.0, village.society.bonds.get(bk, 0.0) + 8.0)

func assign_owners() -> void:
	for v in village.villagers:
		if v.job != null and String(v.job["place"]).begins_with("P"):
			var biz := "BIZ_" + String(v.job["place"])
			if not owners.has(biz):
				owners[biz] = v.villager_id

func succession(v) -> void:
	## The owner leaves (retires or dies): a child who can work, else a colleague, takes over.
	for biz in owners.keys():
		if owners[biz] != v.villager_id:
			continue
		var heir = null
		var why := ""
		for c in v.children:
			var cv = village.villager_by_id(c)
			if cv and cv.age >= 16.0 and cv.age < 65.0:
				heir = cv
				why = "child of the owner"
				break
		if heir == null:
			for o in village.villagers:
				if o != v and o.job != null and "BIZ_" + String(o.job["place"]) == biz:
					heir = o
					why = "longest-serving hand"
					break
		if heir:
			owners[biz] = heir.villager_id
			stats["successions"] += 1
			heir.remember("work", "took over %s" % village.business_name(biz), 6.0)
			village.journal.add("business", [heir.villager_id, v.villager_id], "%s passed from %s to %s." % [village.business_name(biz), v.display_name, heir.display_name], why, true)
		else:
			owners.erase(biz)
			village.journal.add("business", [v.villager_id], "%s has no one to run it after %s." % [village.business_name(biz), v.display_name], "no heir or staff", true)

func wealth() -> Array:
	var w := []
	for hh in village.households:
		if village.households[hh]["members"] > 0:
			w.append(ledger.money(hh) - int(debts.get(hh, 0)))
	w.sort()
	return w

func extra_state() -> Dictionary:
	return {"debts": debts, "favours": favours, "owners": owners, "lean_days": lean_days, "payables": payables, "payable_order": _payable_order, "waiving": _waiving, "flow": _flow}

func load_extra(d: Dictionary) -> void:
	debts = {}; favours = {}; lean_days = {}
	for k in d.get("debts", {}):
		debts[k] = int(d["debts"][k])
	for k in d.get("favours", {}):
		favours[k] = int(d["favours"][k])
	for k in d.get("lean_days", {}):
		lean_days[k] = int(d["lean_days"][k])
	owners = d.get("owners", {}).duplicate()
	payables = {}
	for k in d.get("payables", {}):
		payables[k] = int(d["payables"][k])
	_payable_order = d.get("payable_order", []).duplicate()
	_waiving = bool(d.get("waiving", false))
	_flow = {"in": [], "out": []}
	for k in ["in", "out"]:
		for e in d.get("flow", {}).get(k, []):
			_flow[k].append([int(e[0]), int(e[1])])

func sell_handline(v) -> void:
	## Someone without a job sells what the household cannot eat to the market,
	## like any small shore fisher. Paid now if the till allows, else on account.
	if v.job != null or ledger.qty(v.hh, "fish") <= HOME_KEEP:
		return
	if ledger.qty(MARKET, "fish") >= MARKET_ROOM:
		return
	var p := fish_buy_price()
	if ledger.money(MARKET) - owed_to_fishers() >= p:
		ledger.move(v.hh, MARKET, "fish", 1, "handline_sale")
		_flow_add("in", 1)
		ledger.pay(MARKET, v.hh, p, "handline_sale")
	else:
		ledger.move(v.hh, MARKET, "fish", 1, "handline_consigned")
		_flow_add("in", 1)
		if not payables.has(v.hh):
			_payable_order.append(v.hh)
		payables[v.hh] = int(payables.get(v.hh, 0)) + p
	stats["handline_sold"] += 1
	v.stats["income"] += p
