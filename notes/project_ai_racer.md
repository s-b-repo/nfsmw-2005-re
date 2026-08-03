---
name: ai-racer-aigoalracer-aivehicleracer-host-racing-line-follow-rubber-band-blocker-scan
description: "Two-layer racer AI: AIVehicleRacer host wrapper drives path-follower; AIGoalRacer is the active goal on the stack. Rubber-band catchup is data-driven via g_pGRaceStatus + a 3-entry difficulty table."
metadata: 
  node_type: memory
  type: project
  originSessionId: c4edf485-e85f-4e2f-ac31-e021ba66e8d6
---

NFSMW non-cop racer AI is two layers:
1. **AIVehicleRacer** (host wrapper, 0x7EC bytes, pool `DAT_00925b30`). Vtable `0x00892ad0` (slot 0 dtor `DestroyAIVehicleAndMaybeFree`). Constructed by `CreateAIVehicleRacerInstance @ 0x43ef70`, which first calls `CreateAIGoalRacerInstance` then installs the host vtable, the EAGL physics vtable `vtbl_EAGLPhysics_PlayerCar` at `this+0x4c`, and the path-follower sub-vtables.
2. **AIGoalRacer** (active goal, 0x7CC bytes). Vtable `0x00892720`. Constructed by `CreateAIGoalRacerInstance @ 0x43d388`, pushed via `PushAIGoalByHash(bChunk("AIGoalRacer"))`.

The behavior pivots on `DAT_009b3829` ("race is pursuit-mode"); when true the racer also draws cop-AI subsystems.

## Per-frame call chain
```
TickAIVehiclePlayerCarRacerFrame @ 0x42f140       ; AIVehicleRacer::Tick (host)
  ├ FUN_00407e10                                  ; refresh nav target
  ├ EvaluateRacerCatchupAndNearbyObjects @ 0x4293d0
  │     UpdateRacerSteeringErrorPID @ 0x4292a0   ; PID on heading error
  │     ComputeRacerRubberBandTargetSpeed @ 0x5ff990    ← rubber-band core
  │     FUN_00653e20                              ; apply speed delta
  │     FUN_00727480(DAT_009aa540, "Car"/"Heli")  ; spatial-hash query
  ├ Pick look-ahead via interp:
  │     route stage == 1 -> DAT_008eb498
  │     else             -> DAT_008eb484
  ├ Scan racing line ahead: FUN_007862d0 -> FUN_00785a00
  ├ Rebind waypoint look-ahead: FUN_0077bba0 + FUN_00788f30
  ├ (if 0x7cc.vt[3] is true) delegate to TickAIGoalRacerPerFrame
  ├ TickRacerStuckTimer @ 0x408730                ; this+0x94 anti-stuck
  └ (sharp corner) FUN_005fdda0(DAT_0091e014,0x80); play nitrous SFX (no NOS consume)

TickAIGoalRacerPerFrame @ 0x42aa80                ; slot +0x28 of vtbl_AIGoalRacer
  ├ IsAIRacerInActiveRaceState (sub-state gate)
  ├ EvaluateRacerCatchupAndNearbyObjects(dt)
  ├ this+0xb0 += dt                               ; goal-active timer
  ├ TickRacerStuckTimer(dt)
  ├ LOS check FUN_00408810 -> this+0xa6
  └ broadcast to children: (*this+0xb8)+0x08(dt)
```

## State machine (AIGoalRacer goal-stack lifecycle)
- **CREATE**: `CreateAIGoalRacerInstance @ 0x43d388` — installs vtbl_AIGoalRacer @ 0x892720; sub-vtables `0x8925d8/.cc/.c4/.b4`; registers via `InsertOrAssignTypeRegistry(world, &LAB_00403850, this+0x7c4)`; pushes by bChunk hash.
- **ACTIVATE**: `SetAIRacerGoal @ 0x42305f` — tears down prior goal at `this-0x70c`; pushes new AIGoalRacer; sets path-follower mode 2 (RACE); look-ahead 30m (human) or 60m (AI).
- **TICK**: `TickAIGoalRacerPerFrame @ 0x42aa80` (and concurrently the host `TickAIVehiclePlayerCarRacerFrame @ 0x42f140`).
- **TEARDOWN**: `TeardownAIRacerGoalAndPathFollower @ 0x416900` — resets handlers; calls `ResetAIPathFollowerState`.
- **DESTROY**: `DestructAIGoalRacerSubcomponent @ 0x433570` → `DeleteAIGoalRacerInstance @ 0x4352c0` (pool free 0x7CC).

## Racing-line traversal
- Path graph DAT `0x009a3a64` (AI track segments, 6-byte nodes); accessed via `GetAITrackPathSegmentPtr @ 0x00723c94`.
- Look-ahead distance: `TableLookup_LinearInterp(DAT_008eb498, racingLinePos)` (route stage 1+) or `DAT_008eb484` (stage 0). Each is a 3-point ramp.
- Waypoint flag table `DAT_009b38c0` (22-byte stride); `flags & 1` → non-traversable, triggers replan `FUN_00786330`.
- Path follower head at `this+0x4c` and `this+0x758` (8-slot sub-vtable `0x008925d8`). Mode field at controller+0x78: 0=free-steer, 2=RACE.

## Drafting / blocker / overtake decision tree
There is **NO dedicated drafting or slipstream code**. Observed behavior emerges from:
1. **Forward racing-line scan** (`FUN_007862d0`) — projects `desired_lookahead` ahead, returns first hit. If hit ≠ -1 and waypoint flag-bit 0 is clear and `FUN_007700b0`/`FUN_00766640` don't veto, the path-follower stays mode 2 (RACE). Otherwise it falls back to mode 0 (free-steer) which is the racer's "overtake/avoid" branch.
2. **Lateral nearby-vehicle flags** in `EvaluateRacerCatchupAndNearbyObjects`. Spatial-hash `DAT_009aa540` is queried with keys `DjbHash("Car") = DAT_0090d98c` and `DjbHash("Heli") = DAT_0090d988`. Threshold: lateral < `DAT_00891660 = 1.25 m` persistent for `0.05 s` (`DAT_00890ea8`) → sets `this+0x784` (car-ahead) / `this+0x785` (heli-ahead). Heli flag only matters in pursuit-mode races.
3. **No explicit blocking-when-ahead logic.** Player-side blocking is the racer staying on the racing line at high speed; rubber-band keeps speeds close.

## Rubber-band parameters & globals
| Global | Value/Type | Purpose |
|---|---|---|
| `g_pGRaceStatus + 0x4484` | float | per-race rubber-band gain (set from race attribs) |
| `DAT_008a37d8[3]` | `{0.0, 0.5, 1.0}` | per-difficulty catchup multiplier (Easy/Medium/Hard) |
| `DAT_008f5b58 / .b6c` | 5-pt ramp pair | trailing-racer base-speed (outShort, outLong) vs mySpeed |
| `DAT_008f5b80 / .b94` | 5-pt ramp pair | leader / lap-leader base-speed |
| `DAT_008eb4d4` | 3-pt ramp | catchup scaler keyed on `this+0x7a8` (per-racer aggression) when leading |
| `DAT_008eb4e8` | 3-pt ramp | catchup scaler keyed on `this+0x7a8` when trailing |
| `DAT_00890d3c` | float | upper hard cap on rubber-band outShort |
| `DAT_00890da8` | float | lower clamp |
| `DAT_008933d4` | 0.5 | leader bias |
| `DAT_00890dc4` | 0.01 | catchup gain coefficient |

**Disable rubber-band**: NOP the gain multiply inside `EvaluateRacerCatchupAndNearbyObjects` (~`0x429510`-ish, the `* g_pGRaceStatus+0x4484 * _DAT_00890dc4 * (target - mine)`), or zero `DAT_008a37d8[0..2]`, or zero `g_pGRaceStatus+0x4484` after race load.

## Per-difficulty scaling sources
1. **`DAT_008a37d8[difficulty]`** = `{0.0, 0.5, 1.0}` — base catchup multiplier. Index from `GetRacerDifficultyBucketFromAttribs @ 0x5fac10` which reads attribute hash `0x88a7e3be`: returns 0 if attrib < 0x22, 1 if [0x22..0x42], 2 if > 0x42. **3 buckets confirmed**.
2. **`g_pGRaceStatus+0x4484`** = per-race gain (probably sourced from race-script attribs).
3. **`this+0x7a8`** = per-racer aggression; keys `DAT_008eb4d4/.e8` lookups. *Writer not yet located — likely set at AI vehicle spawn from RACERNAME_%03d attribs.*

## Nitrous AI
**Racer AI does NOT consume nitrous.** Confirmed: `EPlayerTriggeredNOS @ 0x008a7194` has *zero* xrefs in the binary (player-only event hash). The corner-emergency at end of `TickAIVehiclePlayerCarRacerFrame` plays the *blow-off SFX* on `DAT_0091e014` but no NOS is actually consumed — racer "speed boost" is the rubber-band system. Strings `OL_UseNOS`/`CatchUp` at 0x8b7970/0x8b7990 are **online-lobby room options**, NOT AI tunables.

## Open questions
- Writer of `this+0x7a8` (per-racer aggression). Suspected: AI vehicle spawn path, sourced from RACERNAME attribs.
- The "AIActionRace" tactical action (`vtbl_AIActionRace @ 0x892b30`, see `project_ai_architecture.md`) — racer pushes it but the *racer-side* tactical branch (vs cop-side) hasn't been disambiguated.
- The 0x7cc.vt[3] gate inside the host tick: which condition trips it? (host->goal delegation, suspected "pursuit-race active").
- `DAT_009b3829` writer (the pursuit-race switch).

## Renames applied
| Address | Name |
|---|---|
| 0x42f140 | TickAIVehiclePlayerCarRacerFrame |
| 0x42aa80 | TickAIGoalRacerPerFrame |
| 0x4293d0 | EvaluateRacerCatchupAndNearbyObjects |
| 0x5ff990 | ComputeRacerRubberBandTargetSpeed |
| 0x433570 | DestructAIGoalRacerSubcomponent |
| 0x4352c0 | DeleteAIGoalRacerInstance |
| 0x4292a0 | UpdateRacerSteeringErrorPID |
| 0x4097c0 | IsAIRacerInActiveRaceState |
| 0x408730 | TickRacerStuckTimer |
| 0x416900 | TeardownAIRacerGoalAndPathFollower |
| 0x43ef70 | CreateAIVehicleRacerInstance |
| 0x5fac10 | GetRacerDifficultyBucketFromAttribs |

**Pre-existing names used:** `CreateAIGoalRacerInstance @ 0x43d388`, `SetAIRacerGoal @ 0x42305f`, `PushAIGoalByHash @ 0x422480`, `ResetAIPathFollowerState`, `DestroyAIVehicleAndMaybeFree @ 0x4380c0`.

**Why it matters:** modders have three handles to tune racer difficulty: the 3-entry difficulty table `0x008a37d8`, the per-race gain `g_pGRaceStatus+0x4484`, and the 4 speed-curve tables `0x008f5b58…0x008f5b94`. Disable rubber-band by zeroing the gain or NOP'ing the multiply in `EvaluateRacerCatchupAndNearbyObjects`. The attribute hash `0x88a7e3be` (read by `GetRacerDifficultyBucketFromAttribs`) is the per-racer difficulty knob.
