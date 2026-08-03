---
name: NFSMW SpeedBreaker (GAMEBREAKER) skeleton
description: Initial mapping of the SpeedBreaker time-dilation mechanic in NFSMW speed.exe
type: project
originSessionId: research-2026-05-14
---

# SpeedBreaker / GAMEBREAKER

NFSMW's signature bullet-time. **Internal engine name is "GameBreaker"** (string `GAME_ACTION_GAMEBREAKER`, `GAMEACTION_GAMEBREAKER`); only the HUD identifiers say "SpeedBreaker". Note **PursuitBreaker is a different mechanic** (environmental cop-stop objects, strings like `MPursuitBreaker`, `PURSUIT_BREAKER_%d`) — do not conflate.

## Confirmed anchors

| Address | What | Notes |
|---|---|---|
| `0x008a5a24` | str `GAME_ACTION_GAMEBREAKER` | entry in GAME_ACTION enum string table |
| `0x008a6608` | str `GAMEACTION_GAMEBREAKER`  | parallel enum table (older variant) |
| `0x008f6e84` | input binding row | action_id `0x9d` (157), default key `0x22` (DInput SC_E), stride 0x34 |
| `0x008a78e8` | str `"StartBreaker"` | script-VM function name (bChunk hash 0xCA58F64D) |
| `0x00626510` | `DispatchStartBreakerToScript` | C++ shim — pushes "StartBreaker" + 1 byte arg, calls script VM |
| `0x006332a0` | `RegisterStartBreakerEventListener` | registers the shim as listener on AUDIO/UI event bus (`DAT_0091e0d0`) — exact event hash TBD |
| `0x0059e420` | `ConstructHudSpeedBreakerMeter` | HUD widget — slave display, reads energy from a sub-object passed in via param_1 |
| `0x008a20cc-0x008a27e0` | HUD asset names | `Speedbreaker_Meter_Multi_Image`, `SPEEDBREAKER_METER_ICON_GROUP`, `Speedbreaker_Meter_Group`, `Hud_SpeedBreakerMeter`, `TIP_SPEEDBREAKER` |

## Per-frame dt scaling (load-bearing find)

`WorldTickScaleSimulationDt @ 0x006f6cf0` (called by `DispatchWorldSimulationTick @ 0x006f6ec0`, top of per-frame from FUN_00625370) is the **single dt scaling site** for the world sim. Layout on world_root_singleton:

```
+0x18  float  raw frame dt (in)
+0x24  float  time-scale multiplier   (default 1.0)
+0x1c  float  scaled dt = (+0x24) * (+0x18)
+0x2c  int    play-state (3 == active tick)
+0x38  ptr    optional "time strategy" with an IList queried for interfaces:
                  LAB_006e8280  -> returns the time-scale float (vt+4, base is __purecall)
                  LAB_006200e0  -> returns the play-state int (vt+4, base is __purecall)
```

After scaling, the scaled dt is added to `DAT_009885d8` (sim-time accumulator read by `GetSimulationTimeSeconds @ 0x6e8de0`) and `DAT_00988dec`.

**This is the hook SpeedBreaker plugs into.** When no strategy is registered at +0x38, scale stays 1.0 and the world advances at real time. The concrete SpeedBreaker controller class (subclass providing `LAB_006e8280::vt+4 -> 0.4f` while active) is **not yet located**.

Important consequence: this scales the **world simulation dt** (physics, AI, particles, animation — anything driven by `GetSimulationTimeSeconds`). The frame loop / render / audio mixer / UI animator use a different timer (`UpdateUIAnimatorTimer @ 0x56cd20`, etc.) so HUD/menus tick at normal speed.

## Hypothesized state machine (NOT YET VERIFIED)

```
input  DInput key 0x22 -> GAME_ACTION_GAMEBREAKER (id 0x9d)
            v
action handler -> raises event on DAT_0091e0d0 bus
            v
RegisterStartBreakerEventListener listener fires
            v
DispatchStartBreakerToScript -> script function "StartBreaker"
            v
script flips a C++ flag via some bound native (not in RegisterScriptNativesGameplay)
            v
SpeedBreaker controller registers itself at world_root+0x38
            v
WorldTickScaleSimulationDt now reads scale < 1.0 each frame
            v
controller drains energy bar (unlocated global); when 0, unregisters from +0x38
            v
scale back to 1.0, controller starts recharge timer
```

## Negative results (don't waste time re-checking)

- `CDActionIce` is **NOT** SpeedBreaker. ICE = In-Camera Editing (replay cinematics): `ICEACTION_SHUTTLE_*`, `ICECut%d`, `MICECameraFinished`.
- `GetSimulationTimeSeconds @ 0x6e8de0` is a pure reader of accumulator `DAT_009885d8`; scaling does not happen there.
- `StartBreaker` is NOT in `RegisterScriptNativesGameplay @ 0x61e750` — it is a script-side function, not a C++ native.
- The string `GAME_ACTION_GAMEBREAKER` itself has no direct xref because action-table rows hold the pointer and the binding loop accesses by index.

## What dt's are scaled vs. not (best inference)

Scaled (driven by world sim dt at +0x1c, ultimately read via accumulator at `DAT_009885d8`):
- EAGL physics integrator (entry via `DAT_009885c8[+0x44]` per per-frame call chain memory)
- AI tick (AIGoals/AIActions ride the same world tick)
- Particle / animation (TickableBus dispatched on world dt)

NOT scaled (separate timers):
- HUD/UI animator (`UpdateUIAnimatorTimer @ 0x56cd20`)
- Audio mixer / render present
- Network session loop (`Net_MultiplayerSessionUpdateLoop @ 0x761b30`)

This matches the in-game behavior: world slows but the HUD bar drains smoothly and audio low-pass crossfades at real time.

## Renames applied this session

- `0x006f6cf0` → `WorldTickScaleSimulationDt`
- `0x006f6ec0` → `DispatchWorldSimulationTick`
- `0x00626510` → `DispatchStartBreakerToScript`
- `0x006332a0` → `RegisterStartBreakerEventListener`
- `0x0059e420` → `ConstructHudSpeedBreakerMeter`
- `0x0059e570` → `DestructHudSpeedBreakerMeter`
- `0x0059e590` → `FinalizeHudSpeedBreakerMeter`

Plate comments at `0x006f6cf0`, `0x00626510`; disassembly comment at `0x008f6e84`.

## Open questions

1. **The SpeedBreaker controller class.** Find concrete subclass that overrides `LAB_006e8280::vt+4` (time-scale getter) to return < 1.0. Bottom-up approach: search xrefs to `InsertOrAssignTypeRegistry(*, &LAB_006e8280, *)` and check which one's vt+4 returns a non-constant float.
2. **Energy bar / cooldown globals.** `ConstructHudSpeedBreakerMeter` receives the data source via `param_1`; chase `Hud_SpeedBreakerMeter` instantiation site in the in-game HUD root (`FUN_005a6600` at offset +0x2e8) backward to find the source object.
3. **C++ native that the script function calls to actually start the slow-mo.** Not in the gameplay native table — possibly in an audio/camera native table registered elsewhere.
4. **Player-input action-handler that maps id 0x9d to event raise.** Need to find what reads action_id 0x9d from the binding table at 0x008f6e84 and converts to an event broadcast. `LookupUIInputBindingByCode @ 0x56ecc0` per old memory is actually `FEPlayerCarDB_GetCarRecordByHandle` (an unrelated 200-slot DB lookup) — that prior note is stale.
5. **Visual/audio effect tie-ins** (camera FOV, color grading, low-pass): not yet found. Audio low-pass likely keyed off the same controller state via an audio-side query of `LAB_006200e0`. ENISMotionBlur exists as a separate NIS-only effect — probably reused for SpeedBreaker but not confirmed.
6. **Bus identity.** `DAT_0091e0d0` event bus that `RegisterStartBreakerEventListener` subscribes to — confirm whether it is the global gameplay bus or an audio-only bus (the function name calls `ProcessAudioCallbackInvocation`, which is suspicious — might be a misnomer).

## Verification tip

The strategy holder slot is `world_root_singleton + 0x38`. The cheapest probe is a memory watchpoint on that slot during gameplay while triggering SpeedBreaker — the writer is the controller install path; xref the writer back to the script-native or event handler.
