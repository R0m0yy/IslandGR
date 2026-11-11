# INTERACTION MATRIX

Status: **implemented in Godot and exercised by headless tests** (`godot/scripts/interaction/`, `godot/tests/test_runner.gd`). Base contract (`interactable.gd`): `free → reserved → in_use → free`, reservation timeout 240 game minutes, capacity per object.

| Object (anchor type) | Class | Object states | Who may use | Villager state | Duration | Effects | Tested |
|---|---|---|---|---|---|---|---|
| `door` | `Door` | closed → opening → open → closing → closed | anyone | `open_door` | 0.55 s swing, closes 2.2 s after the last request | leaf rotates 100° about its hinge; `state.door_open` | cycle + rotation asserted |
| `bed` | `Bed` | free / reserved / in_use | owner only | `sleep` | until energy ≥ 96 in the morning, or woken by hunger | energy +13 / h | owner-only asserted |
| `stove` | `CookingStation` | cold → lit (5 min) → cooking (25 min) → cold | household | `cook` | ~30 game min | 1 raw fish → 3 meals in the pantry; fire light on while lit | cycle, light, stock asserted |
| `chair`, `table` | `Interactable` | free / in_use | household | `eat`, `sit` | eat 20 min | 1 meal → hunger −70 | covered by the 5-day run |
| fishing spot (outdoor) | `FishingSpot` | free / in_use, 1–2 slots | anyone | `fish` | until 2–3 catches or 200 min | bite roll every 12 min (38 %), fish to pantry or market | covered by the 5-day run |
| `counter`, `scales`, `ice_box` at P01 | `Interactable` | free / in_use | anyone | `shop` | 6 min | up to 2 raw fish market → pantry | ledger balance asserted |
| `counter`, `stall`, `workbench`, `desk`, `shelf`, `net_frame`, `stage`, … | `Interactable` | free / in_use | job holder | `work` | 60–120 min | counts a work block (no output yet) | covered by the 5-day run |
| `lamp` | `OmniLight3D` | off / on | — | — | — | on when it is dark and someone awake is inside | asserted on H01 |
| `sink`, `cabinet`, `storage`, `washstand`, `net_rack`, `bench` | `Interactable` | free / in_use | — | none yet | — | modelled and anchored, no behaviour | — |

Failure handling implemented: object taken → reservation refused → plan not formed → next-best activity; failed use → release reservations, 30-minute cooldown on that activity, idle. **Not implemented:** waiting in a queue, interruption by weather, save/load mid-activity, tool/ingredient sub-goals beyond fish.
