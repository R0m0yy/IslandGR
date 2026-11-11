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
const WAGE := 4
const LEVY := 6
const MEAL_PRICE := 4
const MEALS_PER_FISH := 3

var ledger: Ledger
var village = null
var stats := {"wages_paid": 0, "wages_unpaid": 0, "levy_paid": 0, "levy_missed": 0, "fish_sold_to_market": 0,
	"fish_kept": 0, "fish_bought": 0, "meals_sold": 0, "repairs": 0, "repairs_unaffordable": 0}
var _day: int = -1

func setup(v, l: Ledger) -> void:
	village = v
	ledger = l
	ledger.open(COUNCIL, 500)
	for id in village.buildings:
		var rec: Dictionary = village.buildings[id].record
		if rec.get("business") != null:
			var start := 0
			if rec["business"]["id"] == MARKET:
				start = 200
			elif rec["business"]["id"] == EATERY:
				start = 80
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

func fish_buy_price() -> int:
	## What the market pays a fisher. Falls when the stalls are full.
	var s := ledger.qty(MARKET, "fish")
	return 5 if s < 8 else (4 if s < 30 else 3)

func fish_sell_price() -> int:
	var s := ledger.qty(MARKET, "fish")
	return 8 if s < 4 else (6 if s < 30 else 5)

func daily(day: int) -> void:
	if day == _day:
		return
	_day = day
	for hh in village.households:
		if village.households[hh].get("members", 0) <= 0:
			continue
		if ledger.pay(hh, COUNCIL, LEVY, "levy"):
			stats["levy_paid"] += 1
		else:
			stats["levy_missed"] += 1

func employer_account(v) -> String:
	var biz := "BIZ_" + String(v.job["place"])
	if biz in [MARKET, EATERY, BOATYARD] and ledger.money(biz) >= WAGE:
		return biz
	return COUNCIL

func work_done(v, obj) -> void:
	## Called when a work block ends: production first, then the wage.
	var biz := "BIZ_" + String(v.job["place"])
	if biz == EATERY:
		# the eatery buys fish at the market price and turns it into meals
		for i in 2:
			if ledger.qty(EATERY, "fish") < 1 and ledger.qty(MARKET, "fish") > 0:
				var p := fish_sell_price()
				if ledger.money(EATERY) >= p and ledger.move(MARKET, EATERY, "fish", 1, "eatery_supply"):
					ledger.pay(EATERY, MARKET, p, "eatery_supply")
			if ledger.qty(EATERY, "meal") < 12 and ledger.consume(EATERY, "fish", 1, "eatery_cook"):
				ledger.mint(EATERY, "meal", MEALS_PER_FISH, "eatery_cook")
	if ledger.pay(employer_account(v), v.hh, WAGE, "wage"):
		stats["wages_paid"] += 1
		v.stats["wages"] += WAGE
	else:
		stats["wages_unpaid"] += 1

func land_catch(v, boat: Boat) -> void:
	## Unload a boat: sell to the market while it can pay and has room; the rest goes home.
	var n := ledger.qty(boat.object_id, "fish")
	for i in n:
		var p := fish_buy_price()
		if ledger.qty(MARKET, "fish") < 60 and ledger.money(MARKET) >= p:
			ledger.move(boat.object_id, MARKET, "fish", 1, "landing_sale")
			ledger.pay(MARKET, v.hh, p, "landing_sale")
			stats["fish_sold_to_market"] += 1
			v.stats["income"] += p
		else:
			ledger.move(boat.object_id, v.hh, "fish", 1, "landing_home")
			stats["fish_kept"] += 1
	boat.landed += n
	if boat.condition < Boat.REPAIR_BELOW:
		if ledger.pay(v.hh, BOATYARD, Boat.REPAIR_COST, "boat_repair"):
			boat.condition = 1.0
			stats["repairs"] += 1
		else:
			stats["repairs_unaffordable"] += 1

func buy_fish(v) -> int:
	var got := 0
	for i in 2:
		var p := fish_sell_price()
		if ledger.money(v.hh) >= p and ledger.move(MARKET, v.hh, "fish", 1, "market_sale"):
			ledger.pay(v.hh, MARKET, p, "market_sale")
			got += 1
	stats["fish_bought"] += got
	return got

func buy_meal(v) -> bool:
	if ledger.money(v.hh) >= MEAL_PRICE and ledger.qty(EATERY, "meal") > 0:
		ledger.pay(v.hh, EATERY, MEAL_PRICE, "eatery_sale")
		ledger.consume(EATERY, "meal", 1, "eaten_out")
		stats["meals_sold"] += 1
		return true
	return false
