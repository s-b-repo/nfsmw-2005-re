---
name: in-race HUD rendering subsystem
description: Map of NFSMW in-race HUD - 28 named widgets bound to FNG screens (HUD_SingleRace.fng / HUD_Drag.fng / HUD_Player1/2.fng / HUD_Drag_Player1/2.fng). Widget update wiring is event-driven via the EventBus (event 0x20d60dbf etc.); per-widget update functions still unmapped.
type: project
originSessionId: 9_hud_rendering
---
NFSMW in-race HUD is a CFEManager screen-stack rendered through the standard FNG pipeline; widget update logic is event-bus driven, not call-list driven.

## Key entry points
- `D3D9_PerFrame_RenderAndPresent @ 0x6e7220` -- main render entry.
- `ProcessUIOrHUDElements @ 0x504d00` -- **NOT** the HUD widget walker. It only runs `ProcessAnimationInterpolation` + `UpdateWorldCamerasAndViewport` + `FUN_004fc800` (animation timer) + a flag toggle. Misnamed historically. The actual HUD draw is part of the FE scene-graph walk performed inside the world/FE render passes.
- `HUDFNGSelector_GetActiveScreenName @ 0x005694e0` -- returns which HUD FNG to display by race-mode index:
  - default -> `HUD_SingleRace.fng`
  - 2 -> `HUD_Drag.fng`
  - 3 -> `HUD_Player1.fng` (split-screen)
  - 4 -> `HUD_Player2.fng`
  - 5 -> `HUD_Drag_Player1.fng`
  - 6 -> `HUD_Drag_Player2.fng`
- `CheckShouldShowPauseOrMovieDuringHud @ 0x00595d40` -- predicate: HUD_SingleRace.fng is in scene-stack AND no modal overlay.
- `ProcessFEngHudActionInput @ 0x0057c660` -- FEngHud action router: handles pause / quit / safehouse / retry switches; case 0x2d-0x31 in dispatcher.

## FNG screens used for HUD
- `HUD_SingleRace.fng` (default in-race)
- `HUD_Drag.fng` (drag-race mode)
- `HUD_Player1.fng`, `HUD_Player2.fng` (split-screen)
- `HUD_Drag_Player1.fng`, `HUD_Drag_Player2.fng` (split-screen drag)
- `CustomHUD.fng` / `CustomHUDColor.fng` -- player paint/colour customization preview
- `Pause_Main.fng` (overlay)
- `FadeScreen.fng` (transition cover)

The FNG->handler registry @ `0x008f4320` pairs `(string_ptr, init_fn_ptr)`. HUD container FNGs (HUD_SingleRace, HUD_Drag) have **NULL** handler -- they are passive layout containers that receive their values from the bus, not from a per-screen tick callback.

## The 28 named HUD widgets
String table at `0x008a27cc..0x008a2994` (.rdata). Names actively used by the game:

```
Hud_GetAwayMeter      Hud_SpeedBreakerMeter   Hud_ShiftUpdater       Hud_DragTachometer
Hud_EngineTempGauge   Hud_Minimap             Hud_RadarDetector      Hud_Infractions
Hud_MenuZoneTrigger   Hud_BustedMeter         Hud_MilestoneBoard     Hud_PursuitBoard
Hud_CostToState       Hud_HeatMeter           Hud_Reputation         Hud_Tachometer
Hud_TimeExtension     Hud_Coundown            Hud_WrongWIndi         Hud_TurboMeter
Hud_GenericMessage    Hud_RaceOverMessage     Hud_NitrousGauge       Hud_LeaderBoard
Hud_RaceInformation   Hud_Speedometer         Hud_RaceOverMessage    Hud_GenericMessage
```

Each name is referenced **only** from its destructor funclet inside one large widget-array initializer (parent function is NOT cross-referenced via the funcinfo; cannot be located via static byte-scan). Funclet block @ `0x008737a3..0x008739a2`, FuncInfo @ `0x008d5a00` (28 cleanup states). All destructors funnel into `__free_dbg` via 12-byte free-thunk wrappers @ `0x652b20+`.

## Event-bus wiring (pursuit / bounty path)
- `AwardPlayerBounty_Impl @ 0x612220` writes `pcVar7[0x10] = (curr + amt) / divisor` in the player's career record (`DAT_0091cf90 + 0x10 + slot*4 + 0x414 + 0xa8`), then constructs and broadcasts event hash `0x20d60dbf` (`PursuitBountyAwarded`).
- `RegisterPursuitBountyEventListeners @ 0x648590` subscribes 65 listener stubs to that event (one block of registrations: `EventBus_RegisterListenerStub @ 0x6356a0..0x6376a0`). Each pair `(addr_handler, dispatcher_fn)` binds a subsystem callback. Listener contexts include `0x631320` (audio-callback dispatcher) and 64 others; HUD listeners likely sit among them but each must be decompiled individually to confirm which one drives `Hud_BustedMeter` / `Hud_HeatMeter` / `Hud_PursuitBoard` / `Hud_GetAwayMeter`.

## Data-flow (partial, what's verified)
```
pvehicle_AggregatePhysicsState @ 0x694160
   v->speed, v->rpm, v->gear, v->throttle, v->nitrous, v->engine_temp
              |
              +-- per-frame physics state buffer (active_vehicle_components_arr_a_head @ 0x913e74)
              |
              +-- (path: per-frame FNG tree walk, TBD) --> Hud_Speedometer / Hud_Tachometer / Hud_NitrousGauge / Hud_EngineTempGauge

AwardPlayerBounty_Impl @ 0x612220
  -> event 0x20d60dbf (PursuitBountyAwarded)
              |
              +-- 65 registered listeners (RegisterPursuitBountyEventListeners) ---> heat-meter / bust-meter UI update + audio cue + mission state

g_pUIRootContext @ 0x91cadc   <-- root FNG scene; widgets are children
g_pFrontEndManager @ 0x91cf90 <-- screen-stack; flags @ +0x12C
g_pGRaceStatus @ 0x91e000     <-- read by HUDFNGSelector_GetActiveScreenName for mode index
```

## Globals
- `DAT_0091cf90` -- CFEManager root (+300 = HUD/screen flag bits; bit 0x20 = race-screen active, 0x100 = race-end overlay, 0x40000 = "GameWon" path)
- `DAT_0091cadc` -- UI root context (scene-graph head, queried via `CheckSceneNodeExists` and `FindChildSceneNodeById`)
- `g_pGRaceStatus + 0x1968` -- active event handle (used by `GetEventRaceModeId` to select HUD FNG)
- `DAT_0092d87c` / `DAT_0092d884` -- player profile / car DB pointer
- FNG-handler table `0x008f4320..0x008f4500` -- (string_ptr, init_fn) pairs; HUD_SingleRace.fng / HUD_Drag.fng have NULL init (passive containers)
- Event hash `0x20d60dbf` -- PursuitBountyAwarded, central pursuit-event bus

## Renames applied
- `0x005694e0` -> `HUDFNGSelector_GetActiveScreenName` (was FUN_005694e0)
- `0x0057c660` -> `ProcessFEngHudActionInput` (was FUN_0057c660)
- `0x00648590` -> `RegisterPursuitBountyEventListeners` (was FUN_00648590)
- `0x006356a0` -> `EventBus_RegisterListenerStub` (was FUN_006356a0)
- `0x00595d40` was already `CheckShouldShowPauseOrMovieDuringHud`.
- Plate comments added on all five plus on the funclet block @ `0x00873790`.

## Open questions / unfinished
1. **Per-widget update functions not yet mapped.** The 28 Hud_X widgets are passive layout nodes in the FNG tree; their value updates come via UI bus events (`DispatchUIEventToNamedNode`, `PostUIEventToNamedNode`) and FNG model-binding rather than direct C++ update calls. Need a runtime trace -- set a memory breakpoint on `0x008a2994` (Hud_Speedometer string) under a debugger, run an in-race lap, see which function actually reads the string (this is the widget instance constructor).
2. The big widget-init parent function (the one whose FuncInfo @ `0x008d5a00` covers funclets `0x008737a3..0x008739a2`) is not statically discoverable -- standard MSVC `B8 <funcinfo> E9 <CxxFrameHandler3>` SEH stub @ `0x873778` exists but no code in `.text` LEAs or pushes the funcinfo immediate. The parent likely uses a `__try` wrapper around a tail-call dispatcher and the body lives in a different function. Skip static; use dynamic.
3. Minimap path: world position -> screen-space -- need to chase `EngageGPS` @ found in `FUN_0055b0c0` + AI path graph `DAT_009a3a64` -> minimap texture coords. Not done.
4. Speedometer needle (analog rotation matrix) -- need to find the FNG node bound to Hud_Speedometer; likely a quaternion/rotation applied via `SetUITextNodeFormatted`-style call but on a sprite. Not done.
5. Of the 65 PursuitBountyAwarded listeners, which ones target `Hud_HeatMeter` vs `Hud_BustedMeter` vs `Hud_PursuitBoard` -- each FUN_00631320..FUN_00637620 must be decompiled to find which calls `DispatchUIEventToNamedNode` with what target name. Bulk-decompile job.

## Why
For HUD modding (replacing speedometer artwork, retargeting meters), the FE/FNG approach means you don't need to rewrite C++ -- you replace the FNG bundle. But for changing **semantics** (e.g., showing real KPH instead of MPH, or making the speedometer log-scale), you need to find the binding layer, which goes through the UI bus. The static binding is hidden behind hashed widget-names; the way in is the runtime breakpoint on the widget name strings.

## How to apply
Investigating HUD-related bugs or building HUD mods:
1. Identify which FNG container is active via `HUDFNGSelector_GetActiveScreenName` and the race-mode in `g_pGRaceStatus + 0x1968`.
2. Use `CheckSceneNodeExists(DAT_0091cadc, "HUD_X.fng")` pattern to verify scene presence.
3. For event-driven widgets (heat/bust/pursuit), patch via `EventBus_RegisterListenerStub` registrations or intercept the dispatch hash.
4. For value-driven widgets (speed/rpm/gear/nitrous), runtime-trace from `pvehicle_AggregatePhysicsState @ 0x694160` outputs.
