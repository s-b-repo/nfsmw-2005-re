# AI Systems — Complete Reference

Consolidated AI subsystem reference for NFS Most Wanted (2005). Covers the full AI hierarchy, three concrete AI vehicle classes (Cop, Racer, Traffic, Helicopter), the AIGoal/AIAction model, and modding hooks.

## 1. Overview

NFSMW's AI is organized as a **two-layer stack**:

1. **AIGoals** — strategic objectives. Pushed onto a goal-stack per AI vehicle. Examples: Patrol, Pursuit, HeliPursuit, Race, Pit, HeliExit. Each goal has its own vtable and lifecycle.
2. **AIActions** — tactical sub-behaviors invoked by a goal. Examples: Race (drive), Ram, RoadBlock, StaticRoadBlock, HeliExit. Per-frame `ProcessAIDecisionEvaluation` chooses which action to run.

**Vehicle classes** (all inherit from `AIVehicle`):

| Class | Role | vtable |
|---|---|---|
| `AIVehicle` (base) | abstract base | (shared base, slots common to all) |
| `AIVehicleCopCar` | police cars (ground pursuit) | `0x008925b0` (per SDK) |
| `AIVehiclePursuit` | pursuit base (shared with heli) | `0x00891EC0` |
| `AIVehicleHelicopter` | pursuit chopper | `0x008920D8` |
| `AIVehicleHuman` | human-driven (includes racer) | `0x00892AD0` |
| `AIVehicleRacecar` | non-cop racer | (subclass of Human) |
| `AIVehicleTraffic` | civilian ambient traffic | `0x00891CF8` |
| `AIVehicleEmpty` | placeholder / stationary | (separate vtable) |

**Common method indices** (verified wave-16 from binary):

| Slot | Role |
|---|---|
| vt[0] | dtor (per-class) |
| vt[1] | `AIVehicle_BaseUpdate_vt1 @ 0x406600` — shared base "update" (returns 0 for non-overrides) |
| vt[3] | sentinel-getter (`return -10`) |
| vt[4] | `OnAttach(target)` — caches Pursuit/Engine/Transmission handles on this+0xbc..+0xdc |
| vt[5] | `OnDetach(target)` |
| vt[7] | `OnSimableEvent(payload)` — handles IList add/remove events |
| **vt[10]** | **`OnDriving(dt)` — per-class per-frame driving update (the main hook!)** |
| vt[11..14] | shared AI-state queries |

## 2. AIVehicleCopCar — cop AI

### Pursuit state machine

```
Idle/Patrol
  ↳ AIGoalNone or AIGoalPatrol
       ↓ (player spotted)
SetAICopPursuitGoal @ 0x42ab80
       ├─ ground cop → AIGoalPursuit
       └─ heli       → AIGoalHeliPursuit
       ↓
Engaged
  CreateAIActionRace @ 0x43b800 picks per-frame action:
    AIActionRace, AIActionPursuitOffRoad, AIActionTooDamaged
  Evaluated by ProcessAIDecisionEvaluation
       ↓ (heat escalates)
Escalated
  CreateAIActionRam @ 0x43b9b0   (ramming)
  CreateAIGoalPit @ 0x43fe90     (PIT maneuver)
       ↓ (backup requested)
Backup/Roadblock
  CreateAIActionStaticRoadBlock @ 0x43be50
       ↓ (busted/escaped)
Done
  AIGoalHeliExit @ 0x423510 (heli timeout) / player-evade
```

### Key anchors

- `PushAIGoalByHash @ 0x422480` — push goal onto cop's stack (registry lookup at `DAT_0090d8e8`)
- `SetAICopPursuitGoal @ 0x42ab80` — ground vs heli selection
- `AwardPlayerBounty_Impl @ 0x612220` — heat accumulation; broadcasts event `0x20d60dbf` (PursuitBountyAwarded) — 65 audio listeners on the audio bus
- `g_pGRaceStatus @ 0x91e000` — race state object exposed to scripts
- `DAT_0092d87c` — active player profile (bounty offset +0x414+0xa8)

### Bounty accumulation

```c
AwardPlayerBounty_Impl @ 0x612220 {
    *(int*)(*(int*)(DAT_0092d87c[0x4]) + 0x414 + 0xa8) += amount;
    amount /= *(float*)0x8f5a50;  // bounty divisor (typically 1.0)
    BroadcastEvent(0x20d60dbf);   // PursuitBountyAwarded → 65 audio listeners
}
```

## 3. AIVehicleRacer — non-cop racer

**vtable**: `vtbl_AIVehicleRacer @ 0x892ad0` (class size 0x7EC)
**Per-frame tick**: `0x42f140` (AIVehicle host tick)
**Goal vtable**: `vtbl_AIGoalRacer @ 0x892720` (class size 0x7CC), per-frame `@ 0x42aa80`

### CRITICAL: No drafting / no AI nitrous

Two community-modding myths debunked in wave-5:

1. **No drafting code exists.** What players experience as "slipstream" is the **rubber-band catchup multiplier** — there's no proximity check, no airflow simulation. The AI's target speed is `base × difficulty × rubber_band_gain` and gain rises as the player pulls ahead.

2. **AI doesn't use nitrous.** The `EPlayerTriggeredNOS` event has **zero xrefs** from AI code. Perceived "AI nitrous bursts" are pure rubber-band speed multiplier, not N2O consumption.

### Rubber-band machinery

- `ComputeRacerRubberBandTargetSpeed @ 0x5ff990` — the speed-target function
- `g_pGRaceStatus + 0x4484` — per-race gain
- `DAT_008a37d8 = {0.0, 0.5, 1.0}` — 3 difficulty multipliers (Easy/Medium/Hard)
- `0x8f5b58..0x8f5b94` — 4 ramp tables (per-race ramp curves)

### Difficulty bucket

`GetRacerDifficultyBucketFromAttribs @ 0x5fac10` reads attribute hash `0x88a7e3be` → 3 buckets:

| Bucket | Threshold | Difficulty |
|---|---|---|
| 0 | `value < 0x22` | Easy |
| 1 | `0x22 ≤ value < 0x42` | Medium |
| 2 | `value ≥ 0x42` | Hard |

### Path follow

Uses the shared AI path layer (`DAT_009a3a64` 6-byte nodes from world streamer memory), with look-ahead picks from:
- `DAT_008eb484` (route stage 0)
- `DAT_008eb498` (route stage 1+)

Waypoint metadata at `DAT_009b38c0` (22-byte stride). `&1` bit = non-traversable.

## 4. AIVehicleTraffic — civilian AI

**vtable**: `0x00891CF8` (24 slots) — verified wave-16 via SDK Extensions.h:528 RTTI fingerprint.

### Class layout (from SDK)

`AIVehicleTraffic : AIVehicle, ITrafficAI`

AIVehicleTraffic adds only:
- `Update(dt)` override
- `StartDriving(dt)`
- dtor

AIVehicle base carries:
- `mDriveToNav`, `mDriveSpeed`, `mTarget`
- `mLastSpawnTime`, `mCanRespawn`
- `mCurrentGoal`, `mGoalName`
- `mAvoidableRadius`, `mCollNav`
- 2 embedded `WRoadNav` (`mCurrentRoad`, `mFutureRoad`)
- `mAccelData[10]`, `mTopSpeed`

### Key anchors

| Function | Address | Role |
|---|---|---|
| `DestructAIVehicleTraffic` | `0x00433680` | dtor (vt[0]) |
| `UpdateAIVehicleTraffic_OnDriving` | `0x0042ab40` | per-frame driving update (vt[10]) |
| `SetAITrafficGoal` | `0x00423190` | pushes AIGoalTraffic (vt[23]) |
| `DestroyAITrafficVehicleEntry` | `0x004352f0` | despawn |
| `SetTrafficSignVtable` | `0x0050df00` | traffic-sign object init |
| `ReleaseAITrafficSlot` | `0x007831e0` | pool slot release |
| `DestroyTrafficSpawnSlotEntry` | `0x0078fbc0` | spawn-slot teardown |
| `GetTrafficSpawnSystemSingleton` | `0x00799f50` | global spawn manager |
| `DestroyTrafficAIChainList` | `0x007b3f00` | chain cleanup |

### Lane state (in WRoadNav)

`WRoadNav` carries the lane-following / lane-changing state:

- `bTrafficFilter` — distinguishes traffic lanes from race/cop
- `fLaneInd`, `fFromLaneInd`, `fToLaneInd` — current/source/destination lane
- `fLaneOffset`, `fFromLaneOffset`, `fToLaneOffset` — fractional positions
- `fLaneChangeDist`, `fLaneChangeInc` — interpolation speed
- 32-deep `NavCookie` trail
- `fOccludingTrailSpeed` — forward-car following

### Density / spawn-radius globals

| Address | Symbol | Default |
|---|---|---|
| `0x00926090` | `g_fSkipFETrafficDensity` | 0.0 |
| `0x00926094` | `g_bSkipFEDisableTraffic` | true |

`AISpawnManager.mMinSpawnDist`, `mMaxSpawnDist` — consumers of `MAX_TRAFFIC_SPAWN_DISTANCE` attribute.

### Cracked attribute names (wave-7)

- `TRAFFIC_SPEED` (Float `0x811C6606`)
- `TrafficPattern` (Text `0x6319B692`)
- `TRAFFIC_TYPES` (StringKey `0xB7606A9A`)
- `MAX_TRAFFIC_SPAWN_DISTANCE` (Float `0x3F4A4CEC`)
- `TRAFFIC_LANE_CHANGES` (Bool `0x4463A62D`)
- `CHECK_PLAYER_BEHIND_TRAFFIC` (Bool `0xE8A7CCE2`)

## 5. AIVehicleHelicopter — pursuit chopper

**vtable**: `0x008920D8` (30 slots) — verified wave-16 + SDK Extensions.h:453 RTTI fingerprint.
**Parent**: `vtbl_AIVehiclePursuit @ 0x00891EC0` (also extended by AIVehicleCopCar).

### Multiple inheritance

`AIVehicleHelicopter : AIVehiclePursuit, IAIHelicopter`. Secondary vtable for IAIHelicopter is embedded at offset within the class.

### Member layout (from SDK)

| Field | Type | Role |
|---|---|---|
| `mDestinationVelocity` | Vector3 | target velocity for ISimpleChopper |
| `mLookAtPosition` | Vector3 | camera look-at point |
| `mLastPlaceHeliSawPerp` | Vector3 | last-known player position |
| `mHeight` | float | target altitude over destination |
| `mStrafeToDest` | bool | strafe-mode flag |
| `mPerpHiddenFromMe` | bool | sight-line broken |
| `mHeliFuelTimeRemaining` | float | despawn countdown |
| `mShadowScale` | float | shadow rendering scale |
| `mDustStormIntensity` | float | dust effect strength |
| `mHeliSheets[3]` | HeliSheetCoordinate | strafe-triangle waypoints |
| `mISimpleChopper` | ISimpleChopper* | physics actor |

`HeliSheetCoordinate = { float PreviousElevation; bool VertexValid; Vector3 Vertex[3]; }`

### Per-class method anchors (renamed wave-16)

| Address | Function |
|---|---|
| `0x004336e0` | `DestructAIVehicleHelicopter` (vt[0]) |
| `0x0042adb0` | `UpdateAIVehicleHelicopter_OnDriving(this, dt)` (vt[10]) |
| `0x00417a20` | `FilterHeliAltitudeVector(this, V3&)` (vt[17]) |
| `0x00423510` | `SetAIHeliExitGoal` (despawn-goal push) |
| `0x00404060` | `IAIHelicopter_GetIHandle` (interface thunk) |

### Method order per SDK (slots 15+)

- `GetHeliSheetCoord`
- `Get/SetDesiredHeightOverDest`
- `Set/GetLookAtPosition`
- `SetDestinationVelocity`
- `SteerToNav(WRoadNav*, h, spd, bStop)`, `StartPathToPoint`
- `Set/StrafeToDestIsSet`, `SetStrafeToDest`
- **`FilterHeliAltitude(V3&)`** — verified vt[17] @ `0x417a20`
- `RestrictPointToRoadNet`
- `SetFuelFull`, `GetFuelTimeRemaining`
- `Set/GetShadowScale`, `Set/GetDustStormIntensity`

### Despawn paths

| Trigger | Mechanism |
|---|---|
| Fuel exhausted | `mHeliFuelTimeRemaining` decrements each Update → on expiry, `SetAIHeliExitGoal @ 0x423510` |
| Damaged | `vtbl_DamageHeli @ 0x008AD3C4` — `OnTaskSimulate` flips `mAutoDestruct` → `mDestroying` |
| Pursuit ended | `SetAICopPursuitGoal @ 0x42ab80` chooses a different state |
| Off nav-net | `RestrictPointToRoadNet` triggers if heli wanders too far from road graph |

### Attribute schema

RefSpec `chopperspecs` (hash `0x5D898EE7`, cracked wave-7). SDK exposes `Attrib::Gen::chopperspecs` as an empty stub — child field hashes not yet cracked.

Candidate field names to attempt against uncracked hashes: `MIN_HEIGHT`, `MAX_HEIGHT`, `DEFAULT_HEIGHT_OVER_DEST`, `STRAFE_SPEED`, `FUEL_TIME`, `SHADOW_SCALE`, `ROTOR_RATE`, `DESIRED_VELOCITY_GAIN`, `FACING_TURN_RATE`.

### Spotlight / search-light

Asset `Helicopter_Line_Of_Sight.tga` exists in `InGameB.bun` — cone asset for spotlight beam. Spawn site likely in `Update()` gated on `CanSeeTarget(target)`. Specific call site TBD.

## 6. AIGoal hierarchy

### Goal-stack model

Each AI vehicle holds a per-instance goal stack. Goals are hashed (Jenkins mix3) and looked up in a registry to instantiate the correct vtable.

### Registry

- `DAT_0090d8e8` — AI goal factory registry (hash → vtable)
- `DAT_0090d664` — target pool / lookup table

### Known AIGoal classes

| Goal | Used by | When |
|---|---|---|
| `AIGoalNone` / `AIGoalPatrol` | cops | idle / patrol |
| `AIGoalPursuit` | ground cops | spotted player |
| `AIGoalHeliPursuit` | helicopters | spotted player (heli-specific) |
| `AIGoalPit` | cops | high-heat (PIT maneuver) |
| `AIGoalHeliExit` | helicopters | despawn |
| `AIGoalRacer` | racers | normal race driving |
| `AIGoalTraffic` | traffic | civilian driving |

### Target tracking

- `FUN_00423860` — `SetTargetByID` (queries `DAT_0090d664`)
- `FUN_004238b0` — `SetWaypointPos` (X,Y,Z fallback)
- `FUN_00408810` — line-of-sight raycast (returns LOS bool)

## 7. AIAction tactical layer

AIActions are tactical sub-behaviors invoked by goals each frame.

| Action | Address | Role |
|---|---|---|
| `CreateAIActionRace` | `0x43b800` | drive toward target (default per-cop action) |
| `CreateAIActionRam` | `0x43b9b0` (alias `0x43ba28`) | ramming attack |
| `UpdateAIActionRam` | `0x43bb28` | per-frame ram update |
| `CreateAIActionStaticRoadBlock` | `0x43be50` | static roadblock spawn |
| `CreateAIGoalPit` | `0x43fe90` | PIT maneuver |
| `AIGoalHeliExit` | `0x423510` | heli despawn |
| `AwardPlayerBounty_Impl` | `0x612220` | heat accumulation |

Per-frame: `ProcessAIDecisionEvaluation` walks each AI vehicle's goal stack + evaluates which action to run.

## 8. Per-frame AI tick

```
GameFrameTick @ 0x663d30
  → SubsystemDtAccumulator @ 0x64a680
    → if World.state == 3 (race):
        ActiveComponents_TickAll @ 0x4ba940
          → for each AIVehicle:
              ProcessAIDecisionEvaluation (chooses action)
              → (*vt[10])(this, dt)  ← per-class OnDriving
```

The per-class `OnDriving @ vt[10]` is the main mod hook point.

## 9. Modding AI

### Hook patterns

| Goal | Hook |
|---|---|
| Change ALL traffic behavior | Hook `UpdateAIVehicleTraffic_OnDriving @ 0x42ab40` |
| Change ALL heli behavior | Hook `UpdateAIVehicleHelicopter_OnDriving @ 0x42adb0` |
| Disable heli altitude clamping | Hook `FilterHeliAltitudeVector @ 0x417a20` |
| Change rubber-band aggression | Hook `ComputeRacerRubberBandTargetSpeed @ 0x5ff990` |
| Force despawn a heli | Push `AIGoalHeliExit` via `PushAIGoalByHash` |
| Custom cop class | Register new AIGoal vtable in `DAT_0090d8e8` factory registry |
| Increase bounty rate | Modify divisor at `*(float*)0x8f5a50` |
| Disable cops globally | `SkipFEDisableCops @ 0x8F86C0` = 1 (combined with `SkipFE`) |
| Disable traffic globally | `g_bSkipFEDisableTraffic @ 0x926094` = 1 |

### Attribute-level mods (no hooks needed)

Edit `attributes.bin` via NFS-VltEd:

| Attribute | Type | Effect |
|---|---|---|
| `chopperspecs` RefSpec | record ref | per-vehicle helicopter tuning |
| `aivehicle` RefSpec | record ref | AI behavior data |
| `pursuitescalation` (TBD field hashes) | record | heat escalation curves |
| `pursuitlevels` | record | per-heat-level cop config |
| `pursuitsupport` | record | backup unit composition |
| `trafficpattern` | record | per-region traffic density |
| `presetride` | record | per-car AI preset |

### Vtable replacement template

```c
// Replace AIVehicleHelicopter's OnDriving (vt[10]) with a custom function
#define VTBL_HELI         0x008920D8
#define SLOT_ONDRIVING    10

static void (*orig_heli_ondriving)(void *this, float dt);

void my_heli_ondriving(void *this, float dt) {
    // pre-call mod
    *(float*)((char*)this + offsetof_mHeight) = 50.0f;  // force altitude
    // call original
    orig_heli_ondriving(this, dt);
    // post-call mod
}

void install_hook() {
    void **vtbl = (void**)VTBL_HELI;
    DWORD old;
    VirtualProtect(&vtbl[SLOT_ONDRIVING], 4, PAGE_EXECUTE_READWRITE, &old);
    orig_heli_ondriving = vtbl[SLOT_ONDRIVING];
    vtbl[SLOT_ONDRIVING] = my_heli_ondriving;
    VirtualProtect(&vtbl[SLOT_ONDRIVING], 4, old, &old);
}
```

## 10. Outstanding investigations

- Decompile 13 unnamed slots in vtbl_AIVehicleTraffic and vtbl_AIVehicleHelicopter
- Locate AIVehicle base vtable (shared slots come from this address)
- Crack `chopperspecs` field hashes (currently empty Attrib::Gen stub)
- Find the helicopter spotlight spawn code (asset `Helicopter_Line_Of_Sight.tga` referenced but spawn site TBD)
- AIVehicleHuman vtable (mentioned in SDK but not yet read)
- `AIGoalRoadBlock` ctor location

## Sources

- `memory/project_ai_architecture.md`
- `memory/project_cop_ai_pursuit.md`
- `memory/project_ai_racer.md`
- `memory/project_ai_helicopter.md`
- `memory/project_ai_vehicle_vtables.md`
- `docs/sdk_addrs.json`
- `docs/nfsplugin_sdk_mw05/Types/AIVehicle*.h`
- `docs/nfsplugin_sdk_mw05/Extensions.h` (RTTI fingerprints)
