class_name Ledger
extends RefCounted
## The one place where money and goods change hands (ARCHITECTURE.md: "nothing
## is created or destroyed silently"). Money only enters through open(); goods
## only through mint() (a named production rule) and leave through consume().
## Every operation refuses to go negative and is recorded.

var acc: Dictionary = {}            # id -> {"money": int, "items": {name: int}}
var money_issued: int = 0
var minted: Dictionary = {}         # item -> qty
var consumed: Dictionary = {}       # item -> qty
var totals: Dictionary = {}         # reason -> {"n": int, "money": int, "qty": int}
var log: Array = []                 # recent transactions
var refused: int = 0

func open(id: String, money_: int = 0) -> void:
	if not acc.has(id):
		acc[id] = {"money": 0, "items": {}}
	acc[id]["money"] += money_
	money_issued += money_

func money(id: String) -> int:
	return acc[id]["money"] if acc.has(id) else 0

func qty(id: String, item: String) -> int:
	return int(acc[id]["items"].get(item, 0)) if acc.has(id) else 0

func pay(from: String, to: String, amount: int, reason: String) -> bool:
	if amount <= 0 or not acc.has(from) or not acc.has(to) or acc[from]["money"] < amount:
		refused += 1
		return false
	acc[from]["money"] -= amount
	acc[to]["money"] += amount
	_rec(reason, from, to, "money", amount)
	return true

func move(from: String, to: String, item: String, n: int, reason: String) -> bool:
	if n <= 0 or not acc.has(from) or not acc.has(to) or qty(from, item) < n:
		refused += 1
		return false
	acc[from]["items"][item] -= n
	acc[to]["items"][item] = qty(to, item) + n
	_rec(reason, from, to, item, n)
	return true

func mint(to: String, item: String, n: int, reason: String) -> void:
	acc[to]["items"][item] = qty(to, item) + n
	minted[item] = int(minted.get(item, 0)) + n
	_rec(reason, "", to, item, n)

func consume(from: String, item: String, n: int, reason: String) -> bool:
	if n <= 0 or qty(from, item) < n:
		refused += 1
		return false
	acc[from]["items"][item] -= n
	consumed[item] = int(consumed.get(item, 0)) + n
	_rec(reason, from, "", item, n)
	return true

func _rec(reason: String, from: String, to: String, what: String, n: int) -> void:
	if not totals.has(reason):
		totals[reason] = {"n": 0, "money": 0, "qty": 0}
	totals[reason]["n"] += 1
	if what == "money":
		totals[reason]["money"] += n
	else:
		totals[reason]["qty"] += n
	log.append([snappedf(GameClock.total_minutes, 0.1), reason, from, to, what, n])
	if log.size() > 300:
		log.pop_front()

func audit() -> Array:
	## Returns a list of problems; empty means the books balance.
	var bad := []
	var m := 0
	var have := {}
	for id in acc:
		m += acc[id]["money"]
		if acc[id]["money"] < 0:
			bad.append("negative money: %s" % id)
		for it in acc[id]["items"]:
			var q: int = acc[id]["items"][it]
			if q < 0:
				bad.append("negative %s: %s" % [it, id])
			have[it] = int(have.get(it, 0)) + q
	if m != money_issued:
		bad.append("money %d != issued %d" % [m, money_issued])
	for it in have:
		var expect: int = int(minted.get(it, 0)) - int(consumed.get(it, 0))
		if have[it] != expect:
			bad.append("%s on hand %d != minted-consumed %d" % [it, have[it], expect])
	return bad

func to_dict() -> Dictionary:
	return {"acc": acc.duplicate(true), "money_issued": money_issued, "minted": minted.duplicate(), "consumed": consumed.duplicate(),
		"totals": totals.duplicate(true), "refused": refused}

func from_dict(d: Dictionary) -> void:
	acc = {}
	for id in d["acc"]:
		var items := {}
		for it in d["acc"][id]["items"]:
			items[it] = int(d["acc"][id]["items"][it])
		acc[id] = {"money": int(d["acc"][id]["money"]), "items": items}
	money_issued = int(d["money_issued"])
	minted = _ints(d["minted"])
	consumed = _ints(d["consumed"])
	totals = d.get("totals", {}).duplicate(true)
	for r in totals:
		for k in totals[r]:
			totals[r][k] = int(totals[r][k])
	refused = int(d.get("refused", 0))

static func _ints(src: Dictionary) -> Dictionary:
	var o := {}
	for k in src:
		o[k] = int(src[k])
	return o
