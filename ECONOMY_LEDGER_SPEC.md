# ECONOMY LEDGER SPEC

## Principle
All money and all goods live in **one Ledger** (`godot/scripts/sim/ledger.gd`). Nothing else holds a quantity. Every change is one of four operations; each refuses to go negative and is logged as `[game_minute, reason, from, to, what, n]`.

| Operation | Meaning | Allowed to create or destroy? |
|---|---|---|
| `open(id, money)` | open an account with starting money | **creates money**, counted in `money_issued` |
| `pay(from, to, n, reason)` | move money | no |
| `move(from, to, item, n, reason)` | move goods | no |
| `mint(to, item, n, reason)` | goods enter the world by a named production rule | creates goods, counted in `minted[item]` |
| `consume(from, item, n, reason)` | goods leave the world by a named use | destroys goods, counted in `consumed[item]` |

`audit()` asserts: total money = money issued; for every item, on-hand = minted − consumed; nothing negative. Every test run ends with a clean audit. With `keep_all = true` (tests) the whole history is kept, so any change can be traced to its cause.

## Accounts
| Account | Who | Holds |
|---|---|---|
| `HH_<building>` | each household | money, fish, meals, bait |
| `BIZ_P01` fish market | owner + staff | money, fish |
| `BIZ_P05` general store | | money, bait |
| `BIZ_P04` net loft | | bait (lines, hooks, bait made up) |
| `BIZ_P06` eatery | | money, fish, meals |
| `BIZ_P02` boat yard, `BIZ_P07` carpenter, others | | money |
| `BOAT_0n` | each boat | fish in the hold |
| `council` | the village | money (levy in, wages out) |
| `scraps` | the harbour scrap heap | spoiled fish |

## Production rules (`mint`) and uses (`consume`)
| Reason | Rule |
|---|---|
| `boat_catch` | a boat's gear takes fish from the ecosystem's schools (the same fish leave the sea) |
| `handline_catch` | a pier/shore bite roll |
| `cooked` / `eatery_cook` | 1 fish → 3 meals |
| `net_loft_made` | a net-loft work block makes 4 bait |
| `cut_bait` | 1 fish → 3 bait, at home, when the shop is out |
| `start_stock`, `scenario_setup_*` | initial stock; test setups (always labelled) |
| `eaten`, `eaten_out` | a meal eaten |
| `used_at_sea` | 1 bait per boat trip |
| `stolen_by_gull` | a gull takes 1 fish from a boat being unloaded or the market |
| `eaten_by_gulls` | gulls scavenge the scrap heap |
| `rotted` | half the scrap heap rots each dawn |

## Flows
```
sea schools --boat_catch--> BOAT --landing_sale--> MARKET --market_sale / market_credit--> HH --cooked--> meal --eaten
                               \--landing_home--> HH                \--eatery_supply--> EATERY --eatery_cook--> meal --eatery_sale/eaten_out
NETLOFT --net_loft_made--> bait --store_supply--> STORE --store_sale--> HH --used_at_sea
HH / MARKET --spoiled_thrown_out / market_spoilage--> SCRAPS --eaten_by_gulls / rotted
HH --levy--> COUNCIL --wage--> HH ;  MARKET/EATERY/STORE/BOATYARD --wage--> HH (when they can pay)
HH --boat_repair--> BOATYARD ;  HH or COUNCIL --storm_repair--> CARPENTER ;  HH --gift--> HH ;  HH --inheritance--> HH or COUNCIL
```

## Prices and scarcity
- Market selling price: `clamp(round(9 − stock/7), 3, 9)`; the buying price paid to fishers is 2 less (minimum 2). An empty market charges 9; a glutted one 3–5.
- Meals at the eatery: 4. Bait: 2. Boat repair: 12. Storm repair: 8.
- Freshness: each dawn a household loses half of the raw fish above 4, and the market a third of what is above 25. Both go to the scrap heap.

## Credit, gifts and hardship
- **Credit:** a household that cannot pay may take fish from the market up to a slate of 18 (`debts`); it pays the slate back at dawn once it has 12 to spare. Both events are journalled.
- **Gifts:** a resident with spare fish (more than 2 per household member) who knows a household with an empty larder and a hungry, sick or elderly member may take them food. The score rises with generosity and with favours received from that household before (`favours`, reciprocity). The fish moves through the ledger. Recipients remember it, and the bond rises.
- **Unpaid repairs:** a carpenter mends storm damage even when the household cannot pay, and is remembered for it.
- **Struggling businesses:** four days without money for a wage is journalled; so is the recovery.
- **Succession:** when an owner retires or dies, a working-age child takes over, else the longest-serving hand; with no one, the business is journalled as without a keeper.

## Known limits
Prices are rule-based, not negotiated. Shops have no opening hours beyond the market's 06:00–20:00 and closing in storms. There are no rents, property sales or business closures: a business with no keeper keeps its account but no new owner appears. These are listed in `KNOWN_ISSUES.md`.
