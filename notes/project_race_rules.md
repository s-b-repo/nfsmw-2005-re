---
name: race-rules-engine
description: "NFSMW race-mode enum, dispatch, checkpoint pipeline, per-mode rule sites"
metadata: 
  node_type: memory
  type: project
  originSessionId: c4edf485-e85f-4e2f-ac31-e021ba66e8d6
---

# Race Rules Engine (NFSMW speed.exe)

## Enum (cracked)
`GetEventRaceModeId @ 0x005faa20` resolves the per-event mode id by reading
attribute `0x0F6BCDE1` ("GameMode" string) and linear-scanning the 11-row
table at `PTR_s_circuit_008f5cd8` (pairs of {string*, int}):

| id | name             | notes                                     |
|----|------------------|-------------------------------------------|
| 0  | `p2p`            | Sprint / point-to-point                   |
| 1  | `circuit`        | Multi-lap loop                            |
| 2  | `drag`           | Drag race; special pre-race camera state  |
| 3  | `knockout`       | Lap Knockout (eliminate last per lap)     |
| 4  | `tollbooth`      | Time-extension checkpoint chain           |
| 5  | `speedtrap`      | Highest combined trap-speed wins          |
| 6  | `checkpointrace` | Linear ordered checkpoint sprint          |
| 7  | `cashgrab`       | Same time-extension mech as tollbooth     |
| 8  | `challenge`      | Career/tutorial dispatch (sub-events)     |
| 9  | `speedtrapjump`  | Air-time speedtrap (tutorial)             |
| 10 | `milestonejump`  | Career-event jump                         |

No "Drift" mode is shipped — the lowercase string `drift` at 0x0089abcc
is a leftover localization key only; not present in the mode table or any
scoring routine. NFSMW omits the Underground-era Drift mode entirely.

There is **no single per-mode rule vtable**. Dispatch is
`switch (GetEventRaceModeId(event))` scattered across the notify-handlers
(NotifyLapFinished_Impl, NotifySpeedTrapTriggered_Impl, ProcessStartRace,
InitPlayerCameraForRaceModeStart, etc.). 112 xrefs total.

## Anchors

| Address     | Symbol                                  | Role                          |
|-------------|-----------------------------------------|-------------------------------|
| 0x005faa20  | GetEventRaceModeId                      | Race-mode dispatcher          |
| 0x008f5cd8  | PTR_s_circuit_008f5cd8                  | Mode-name → id table          |
| 0x0060dbd0  | ProcessStartRace                        | Race init; mode-2 (drag) reset path |
| 0x006117f0  | NotifyCheckpointReached_Impl            | Script native, per-checkpoint |
| 0x00611850  | NotifyLapFinished_Impl                  | Knockout elimination site     |
| 0x00611440  | ProcessKnockoutRacer                    | Removes a racer (also `TotalRacer`)|
| 0x00600660  | OnCheckpointReachedUpdateRacerTimers    | Per-racer timer update        |
| 0x005dc260  | StoreRacerLapTime                       | `[event_idx][racer]` table at GRaceStatus+0x19BC |
| 0x005dc2f0  | StoreRacerCheckpointTime                | `[event_idx][racer][cp]` at GRaceStatus+0x1C3C   |
| 0x005fb920  | GetEventTimeLimitSec   (attr 0xD8BAA07B) | Per-event countdown length    |
| 0x005fc6e0  | GetEventKnockoutRatePerLap (attr 0x181462DA) | racers eliminated per lap |
| 0x005facd0  | GetEventDeclaredNumRacers               | Racer slot count              |
| 0x005fc030  | GetEventNeedsCopsFlag  (attr 0x3918E889) | Mode needs heat?              |
| 0x005fcba0  | (event-id getter, used in ProcessStartRace) | Event ID hash               |
| 0x005fa9a0  | (event mode-id from cached handle)      | Helper to GetEventRaceModeId  |
| 0x0060a7b0  | NotifySpeedTrapTriggered_Impl           | SpeedTrap record + UI flasher |
| 0x005fe600  | ProcessAwardBonusTime                   | Tollbooth time-extension      |
| 0x006113e0  | ShowTimeExtension_Impl                  | HUD bridge to BroadcastShowTimeExtensionEvent |
| 0x006252d0  | BroadcastShowTimeExtensionEvent         | FE event poster               |
| 0x00641840  | InitPlayerCameraForRaceModeStart        | Camera initial-state by mode  |
| 0x0057c000  | GetDragTachoIconForRpmBracket           | Drag shift-point HUD selector |
| 0x00611700  | SetRacerGoal_Impl                       | Sets racer waypoint + checkpoint |
| 0x00605140  | ProcessChallengeComplete                | Career native; mode-8 finalizer |

## Per-mode rule sites
- **Sprint (0) / Circuit (1)**: timer ticks via `StoreRacerLapTime`,
  finish line = last checkpoint of last lap. Number of laps via attribute
  at event+0x158 (FUN_005ddec0).
- **Drag (2)**: ProcessStartRace zeros `GRaceStatus+0x454C` (mode-specific
  reset). InitPlayerCameraForRaceModeStart picks camera vt-slot 5/6 for drag
  (player/AI) instead of 3/4. Tach UI driven by
  `GetDragTachoIconForRpmBracket` reading attr `0xF1F5FBC7` (RPM curve);
  builds `DRAG_RPM_%d_LINES` icon names. 4-gear shift-points are
  data-driven via per-vehicle RPM thresholds, not a hard-coded gear count.
- **Knockout (3)**: at lap-finish, count `iVar8 = racers still on/past
  current_lap`. Quota `iVar3 + (1 - iVar1 * lap)` with iVar3 =
  GetEventDeclaredNumRacers, iVar1 = GetEventKnockoutRatePerLap. When the
  quota is hit, eliminate the racer whose lap_idx < current_lap.
- **Tollbooth (4) / Cashgrab (7)**: scripts call `AwardBonusTime(seconds)`
  -> ProcessAwardBonusTime adds to `GRaceStatus+0x1980` (global countdown),
  also appends a per-racer time stamp to ring buffer at `+0x48`. Time
  expires => race over via standard placement flow.
- **SpeedTrap (5)**: NotifySpeedTrapTriggered_Impl stores per-trap kmh in
  attribute `0x822179D1` list (per-trap index). Win = highest combined.
- **Checkpointrace (6)**: standard checkpoint chain with
  OnCheckpointReachedUpdateRacerTimers; no laps, finish = last cp.
- **Challenge (8)**: ProcessChallengeComplete posts event 0x20D60DBF
  (challenge-complete hash) and hands off to milestone system.
- **SpeedtrapJump (9) / MilestoneJump (10)**: jump-stunt variants of
  speedtrap; per-jump scoring in same attribute list.

## Checkpoint trigger model
`AddCheckpoint` and `SetNextCheckpointPos` are script natives (see
`RegisterScriptNativesGameplay @ 0x0061e750`). Volumes live in the world
descriptor; on entry, scripts call `NotifyCheckpointReached(racer, lap)`
which routes to `OnCheckpointReachedUpdateRacerTimers`. The 3D time table
at GRaceStatus+0x1C3C is indexed `[event_idx][racer_idx][cp_idx]` stride 4.

## Open questions
- Drift scoring: confirmed absent. The lowercase "drift" string is only
  used by older localization tables, no math.
- Pursuit Mode "time-survived": career-level, not a race mode. Owned by
  cop_ai_pursuit.md / career_milestones.md (`pursuit_evasion_time`,
  `pursuit_length`, `cost_to_state_in_pursuit` stat keys at 0x0089D5xx).
- "challenge" (mode 8) dispatches what specifically? ProcessChallengeComplete
  only posts a hashed event; the consumer side (career screen, milestone
  step) is in project_career_milestones.md.
- The 200-row table at DAT_0091cf90+0x414 (xref'd from GetDragTachoIconForRpmBracket)
  is per-player active-pvehicle mapping; worth a future plate.
- Lap-knockout quota formula uses signed arithmetic; the boundary case
  `rate * lap >= total` could underflow if rate>1 and lap>=total/rate,
  but in shipping events rate==1 and lap<=total-1, so it never triggers.

## Cross-refs
- Career flow: project_career_milestones.md (ProcessChallengeComplete,
  MilestoneProgressEvent path).
- AI side: project_ai_architecture.md (AIGoalRacer drives the racers we
  knock out / eliminate).
- Cops: project_cop_ai_pursuit.md (mode==pursuit is *not* a race mode --
  it's a parallel persistent system).
- Script natives: project_script_natives.md (StartRace, AwardBonusTime,
  NotifyCheckpointReached, etc. all registered in same block).
