---
name: hud-widget-slot-map-chudwidgetarray-offsets
description: "Every HUD widget's storage offset on CHudWidgetArray. 24 widgets cross-referenced between CHudWidgetArray_Ctor @ 0x5a6600 and CHudWidgetArray_Tick @ 0x58ca30. Only 10 widgets get per-frame ticks via the walker; the other 14 update via FNG/PostUIEventToNamedNode."
metadata: 
  node_type: memory
  type: project
  originSessionId: c4edf485-e85f-4e2f-ac31-e021ba66e8d6
---

## Definitive widget storage map

Each HUD widget is stored at a FIXED offset on the CHudWidgetArray object. Cross-referenced from `CHudWidgetArray_Ctor @ 0x5a6600` (master init).

| Offset | Widget | Object size | Wave-9 ctor | Update | Walker-ticked? |
|---|---|---|---|---|---|
| `+0x2c0` | Speedometer | (size TBD) | `0x59e7f0` | `0x57a540` | ❌ (no walker call) |
| `+0x2c4` | Tachometer | (size TBD) | `0x59e9d0` | `0x57a6e0` | ❌ |
| `+0x2c8` | DragTachometer | (size TBD) | `0x5a0ef0` | `0x57d130` | ❌ |
| `+0x2cc` | ShiftUpdater | (size TBD) | `0x5a0c60` | `0x569780` | ❌ |
| `+0x2d0` | CostToState | 0xd8 | `0x59d0c0` | `0x5668f0` | ❌ |
| `+0x2d4` | Reputation | (size TBD) | `0x59d2a0` | `0x5669b0` | ❌ |
| `+0x2d8` | HeatMeterInRace | 0x50 | `0x59cec0` | `0x5666a0` | ❌ |
| **`+0x2dc`** | **TurboMeter** | 0x98 | `0x5a0380` | `0x57bb40` | **✅** |
| **`+0x2e0`** | **EngineTempGauge** | (size TBD) | `0x59e620` | `0x5685e0` | **✅** |
| `+0x2e4` | NitrousGauge | 0x40 | `0x59e260` | `0x568330` | ❌ |
| **`+0x2e8`** | **SpeedBreakerMeter** | 0x48 | `0x59e420` | (TBD) | **✅** |
| **`+0x2ec`** | **RaceOverMessage** | 0x40 | `0x59e0f0` | `0x57a4b0` | **✅** |
| **`+0x2f0`** | **GenericMessage** | (size TBD) | `0x59dee0` | `0x567f80` | **✅** |
| `+0x2fc` | LeaderBoard | (size TBD) | `0x59f0e0` | `0x568950` | ❌ |
| `+0x300` | PursuitBoardInRace | (size TBD) | `0x59fc80` | `0x57aee0` | ❌ |
| `+0x304` | MilestoneBoard | (size TBD) | `0x59f440` | `0x57ae30` | ❌ |
| `+0x308` | BustedMeter | (size TBD) | `0x5a01d0` | `0x568eb0` (no-op) | ❌ |
| `+0x30c` | TimeExtension | (size TBD) | `0x5a0060` | `0x57b780` | ❌ |
| **`+0x310`** | **WrongWayIndi** | 0x48 | `0x59ec70` | `0x568800` | **✅** |
| **`+0x314`** | **(EMPTY — always-on slot)** | n/a | n/a | n/a | **✅** (always called) |
| **`+0x318`** | **Countdown** | 0x70 | `0x59dd30` | `0x5679b0` | **✅** |
| **`+0x31c`** | **RadarDetector** | 0x70 | `0x59cc30` | `0x566170` | **✅** |
| `+0x324` | GetAwayMeter | 0x48 | `0x59ca80` | `0x565b10` (stub) | ❌ |
| **`+0x328`** | **MenuZoneTrigger** | 0x50 | `0x5a0530` | `0x57bbc0` | **✅** |
| **`+0x32c`** | **Infractions** | 0xd8 | `0x5a1380` | `0x569a50` | **✅** |

**Total: 24 widgets** (matches wave-9 "28 named widgets" — minor delta because 4 are sub-screens / not slot-tied).

## The walker only ticks 10 of 24 widgets

`CHudWidgetArray_Tick @ 0x58ca30` (wave-13 discovered) iterates EXACTLY these 11 slots:

```
0x2dc TurboMeter
0x2e0 EngineTempGauge
0x2e8 SpeedBreakerMeter
0x2ec RaceOverMessage
0x2f0 GenericMessage
0x310 WrongWayIndi
0x314 (empty / always-on — no widget here in our analysis)
0x318 Countdown
0x31c RadarDetector
0x328 MenuZoneTrigger
0x32c Infractions
```

The other 14 widgets (Speedometer, Tachometer, DragTachometer, ShiftUpdater, CostToState, Reputation, HeatMeterInRace, NitrousGauge, LeaderBoard, PursuitBoardInRace, MilestoneBoard, BustedMeter, TimeExtension, GetAwayMeter) are **NOT walker-ticked**.

So how do they update? Two channels:

1. **FNG event bus** — `PostUIEventToNamedNode` (UI root `DAT_0091cadc`) routes events to named nodes; widget node handlers fire on each event. The Speedometer reads vehicle speed via `(*piVar3 + 0x8c)()` — this is invoked from a node-event handler, not from a global tick.

2. **External write injection** — BustedMeter and GetAwayMeter have NO-OP or stub Updates; their data is set by EXTERNAL writers (cop-AI tick, race-event handler) writing to FNG nodes directly. The "Update" is essentially passive.

## Why this matters

Wave-12 puzzled over BustedMeter's no-op Update. Now we know: it's not walker-ticked, AND the Update is a no-op — so the widget is purely **passive** (FNG-driven). The FNG file animates from data poked in by an external writer.

Modders targeting Speedometer / Tachometer / etc. should NOT hook the Update function — instead, hook the event-bus dispatcher or the FNG handler chain.

## Special slot at +0x314

`CHudWidgetArray_Tick` calls `(*(this+0x314) + 4)()` UNCONDITIONALLY (no mode-filter check, no NULL check is wrong, has NULL check). But no `ConstructHud_*` ctor writes to +0x314. This means either:

- It's reserved / unused in retail
- It's populated by a non-ctor path (e.g. plugin/asi hook)
- It might be the master-init's own self-pointer (CHudWidgetArray as its own widget?)

Worth investigating — could be a clean hook point for asi mods.

## Mode-filter integration

For each walker-ticked widget, the mode-filter check is:

```
widget[6] & widget[8] != 0 || widget[7] & widget[9] != 0
```

Per wave-13. So widget[6..9] are the per-widget activation masks set by the ctor based on race-mode requirements. Cross-reference with the master-init `local_4` state markers to get the mode-mask values per widget.

## Outstanding

- Object sizes for widgets without explicit malloc (left blank above) — can be inferred from FUN_005a6600 if needed
- The Speedometer/Tachometer event-bus invocation chain — what node-event fires their Update?
- +0x314 always-on slot — investigate if anything writes to it at runtime
