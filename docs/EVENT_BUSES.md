# EVENT_BUSES.md — Event-Bus and State-Machine Systems in NFSMW

This document catalogues every event-bus, message-broadcast, and state-machine
mechanism reverse-engineered from `speed.exe` (Need for Speed: Most Wanted,
2005 PC build). Each section maps the public API (subscribe / publish), the
internal data structures, the known event hashes, and the modding hook points.

---

## 1. Overview

NFSMW is **not** built around a single global event bus. Instead, the engine
uses five distinct dispatch mechanisms, each tuned to a different
"who-talks-to-whom" pattern. Most engine-wide gameplay communication is hash
keyed (Bob Jenkins mix3 / "bChunk" — see `project_bchunk_hash`).

The five buses are:

| # | Bus / mechanism                            | Domain                                | Anchor                                                  |
|---|--------------------------------------------|---------------------------------------|---------------------------------------------------------|
| 1 | **FNG event bus** (UI / HUD)                | Screen-stack widget events            | `PostUIEventToNamedNode @ 0x516c90`                     |
| 2 | **Audio / gameplay event bus DAT_0091e0d0** | Cross-subsystem hashed events         | `BusBroadcastEventByHash @ 0x61fc10`                    |
| 3 | **TickableBus**                            | Per-frame tick fan-out                | `TickableBus_DispatchActiveSubscribers @ 0x72e0c0`      |
| 4 | **Game-state machine**                     | High-level boot / track / race phase  | `ProcessGameStateMachine @ 0x6596a0`                    |
| 5 | **Career message broadcast**               | Race-end / milestone notifications    | `MilestoneProgressEventConstructor @ 0x5dd670`          |

A sixth pattern — **`PursuitBreaker` triad** — is not its own bus, but a
canonical demonstration that a single user-visible mechanic can ride **three
separate event hashes on bus #2**. It is documented in section 7 because the
distinction trips up every first-time modder.

The remainder of this document expands each bus.

---

## 2. FNG event bus (`PostUIEventToNamedNode` chain)

**Domain:** the FNG screen-stack subsystem (see `project_fe_engine.md`).
This is the bus that fires widget updates: speedometer digits, milestone
popups, lap-counter increments, every text field that changes on screen.

### 2.1 End-to-end flow

```
[gameplay/system code]
   |
   v
PostUIEventToNamedNode @ 0x516c90
   |
   v
DispatchUIEventToNamedNode @ 0x516be0
   +- if name==NULL -> fan out via subscriber list at (*this+0xe0)
   +- if name!=NULL -> FindSceneNodeByName(name) ->
                       ScheduleUIDeferredEvent @ 0x5b7780
                          +- if (this+0x524e):
                              synchronous dispatch via (*this+0x108+0x54)()
                          +- enqueue 0x20-byte event into doubly-linked list:
                              this+0x4118 = head, this+0x411c = tail,
                              this+0x4114 = count
                              vtable PTR_FUN_008a2c90, fence 0xABADCAFE x 2

[per-frame tick — main loop]
   |
   v
FE_PerFrameTick_DrainQueueAndUpdateChildren @ 0x5c53c0
   +- if (this+0x524e): dispatch sync queue first via (*this+0x108+0x5c)()
   +- iterate this+0xd0 child handlers, call FUN_005ae960 per slot
   +- iterate this+0xe0 subscriber list (full per-handler tick)
   +- DrainUIDeferredEventQueue_PerFrame @ 0x5c1460
        For each event in queue (this+0x4118 -> ... -> null):
          UnlinkSceneNodeChild(this+0x4110, event)
          Read event[4] = target marker:
            0xfffffffc -> broadcast to all subscribers (this+0xe0)
            0xfffffffa -> alt-broadcast
            NULL        -> type-registry broadcast
            ptr         -> direct call into target node's handler
          Dispatch via:
            DispatchUIEvent_ToSubscriberHandler @ 0x5bbc00      (direct)
            DispatchUIEvent_ToTypeRegistrySubscribers @ 0x5beaa0 (registry)
```

### 2.2 Key addresses

| Address      | Symbol                                              | Role                                              |
|--------------|-----------------------------------------------------|---------------------------------------------------|
| `0x00516c90` | `PostUIEventToNamedNode`                            | Public producer                                   |
| `0x00516be0` | `DispatchUIEventToNamedNode`                        | Targeted vs. broadcast switch                     |
| `0x005b7780` | `ScheduleUIDeferredEvent`                           | Enqueue + optional sync dispatch                  |
| `0x005c1460` | `DrainUIDeferredEventQueue_PerFrame`                | Per-frame queue drainer                           |
| `0x005c12f0` | `ConstructUIDeferredQueueOwner`                     | Ctor — clears queue head/tail                     |
| `0x005bbc00` | `DispatchUIEvent_ToSubscriberHandler`               | Direct-subscriber dispatch                        |
| `0x005beaa0` | `DispatchUIEvent_ToTypeRegistrySubscribers`         | Type-registry-keyed dispatch                      |
| `0x005c53c0` | `FE_PerFrameTick_DrainQueueAndUpdateChildren`       | Main FE tick — calls the drainer                  |
| `0x005c20a0` | `FE_AlternateUpdate_DrainQueue`                     | Alt-mode tick (e.g. pause overlay)                |

### 2.3 Queue-owner object layout (FE/UI context)

| Offset    | Field                                | Notes                                                       |
|-----------|--------------------------------------|-------------------------------------------------------------|
| `+0x0e0`  | Subscriber list head                 | Linked list of registered handlers                          |
| `+0x0d0`  | Child handler count                  | Number of slots in handler array                            |
| `+0x108`  | Sync-dispatch vtable                 | `*+0x54` sync sched, `*+0x5c` sync drain, `*+0x40` handler list, `*+0x44` handler init |
| `+0x4110` | Queue-node vtable                    | `PTR_LAB_008a2c18` — used by `UnlinkSceneNodeChild`         |
| `+0x4114` | Event count                          | Incremented on `Schedule`                                   |
| `+0x4118` | Queue head ptr                       | First event to drain                                        |
| `+0x411c` | Queue tail ptr                       | Last event                                                  |
| `+0x524e` | Sync-dispatch enable flag            | If set: events dispatched immediately AND queued            |

### 2.4 Event object layout (0x20 bytes)

| Offset | Field                                                                |
|--------|----------------------------------------------------------------------|
| +0x00  | vtable = `PTR_FUN_008a2c90`                                          |
| +0x04  | prev ptr in queue (debug fence: `0xABADCAFE` initial)                |
| +0x08  | next ptr in queue (debug fence: `0xABADCAFE` initial)                |
| +0x0c  | param_2 (caller payload)                                             |
| +0x10  | event hash                                                           |
| +0x14  | event command / value (param_1 in Post)                              |
| +0x18  | target node ptr (or sentinel: `0xfffffffc`/`0xfffffffa`/NULL)        |
| +0x1c  | priority                                                             |

### 2.5 Push vs. pull HUD widgets

Two update patterns coexist:

* **Pull / walker widgets** (10): TurboMeter, etc. Have continuous animations
  or counters; ticked every frame by the FE walker.
* **Push / event-driven widgets** (14): speedometer digits, gear indicator,
  milestone popup, etc. Only update when a producer pushes an event for their
  named node. The producer (e.g. the vehicle physics pull-and-unpack loop)
  calls `PostUIEventToNamedNode(ui_root, hash, "SPEED_DIGIT_1", ...)`; the
  drainer next frame matches the named node and the registered
  type-registry handler is invoked.

### 2.6 Modding hook points

| Goal                                      | Hook                                                                                 |
|-------------------------------------------|--------------------------------------------------------------------------------------|
| Intercept ALL FNG events being posted     | Hook `PostUIEventToNamedNode @ 0x516c90`                                             |
| Block events for a specific node          | Hook `DispatchUIEventToNamedNode @ 0x516be0`, filter by node-hash                    |
| Block one event hash globally             | Hook `ScheduleUIDeferredEvent @ 0x5b7780`, filter by event hash                      |
| Manually flush the queue                  | Call `DrainUIDeferredEventQueue_PerFrame @ 0x5c1460`                                 |
| Inject a fake event into the queue        | Build a 0x20-byte event (vtable=`0x8a2c90`, fence=`0xabadcafe`) and link it at +0x4118 |

---

## 3. Audio / gameplay event bus `DAT_0091e0d0`

**Domain:** the global hashed-event bus used by audio cues, SpeedBreaker /
PursuitBreaker triggers, environmental triggers, world-event radio chatter,
and any C++-to-C++ message that wants to be loosely coupled. Originally
discovered while chasing audio callbacks (hence the legacy name
`ProcessAudioCallbackInvocation` on the broadcaster), it is the closest thing
NFSMW has to a "global event bus".

### 3.1 Public API

| Address      | Symbol (target rename)                       | Description                                                       |
|--------------|----------------------------------------------|-------------------------------------------------------------------|
| `0x0061fc10` | `BusBroadcastEventByHash`                    | Broadcast — takes constructed event handle, looks up bucket by `event[6]` (= hash), dispatches every listener registered to that bucket. |
| `0x0061fd00` | `BusSubscribeListenerByHash`                 | Register listener (callback + user ctx) on a hash bucket          |
| `0x005f9da0` | `BusDispatchEventToListenerFilters`          | Inner iteration over a bucket's listener filters                  |
| `0x0061fb40` | `BusFindOrCreateBucketByHash`                | Bucket allocator — keyed on `bChunk("name")`                      |
| `0x0061f8a0` | `ConstructEventBus`                          | Bus ctor                                                          |
| `0x0061f590` | `DestructEventBus`                           | Bus dtor                                                          |
| `0x0061f940` | `CreateGlobalEventBus_DAT0091e0d0`           | One-time global instantiation                                     |

### 3.2 Bus storage

`DAT_0091e0d0` is a singleton pointer that lives in the .data segment. Each
hash bucket holds:

* a 32-bit hash key (`bChunk(eventName)`),
* a linked list of `(callback, user_ctx, filter_mask)` triplets.

Listeners are matched by hash only — there is no per-bucket type information,
which is why a single mechanic (PursuitBreaker) is free to fire three
different hashes (section 7).

### 3.3 Hash caching pattern

Almost every callsite caches the result of `stringhash32("EventName")` in a
.data-segment global so that the hash is computed exactly once:

```
GetMPursuitBreakerEventHash_Cached @ 0x004b5880  ->  DAT_00913c34
GetMBreakerStopCopsEventHash_Cached @ 0x00405b70 ->  DAT_0090d940 (gated by bit 0 of DAT_0090d944)
GetEventHashPlayerEnterPursuit     @ 0x00626480  ->  cached global
GetMilestoneProgressMessageHash    @ 0x005dd5f0  ->  cached
GetMessageHashMilestoneReached     @ 0x005de370  ->  cached
GetPlayerRepMessageHash            @ 0x004058e0  ->  cached
GetRacePlacementMessageHash        @ 0x00604440  ->  cached
GetRaceTimeBroadcastMessageHash    @ 0x005db8a0  ->  cached
```

These helpers are the **easiest way to identify what hashes are in flight**:
every cached-hash getter has a string xref to its preimage and ends with the
same compare-and-store idiom.

### 3.4 Worked example — SpeedBreaker / PursuitBreaker path

`RegisterStartBreakerEventListener @ 0x006332a0` (the wave-9 misnomer; the
function actually subscribes to `MPursuitBreaker`, not `StartBreaker`) does:

```
hash = GetMPursuitBreakerEventHash_Cached()
BusSubscribeListenerByHash(DAT_0091e0d0, hash, DispatchStartBreakerToScript, ctx)
```

At runtime, when a player vehicle hits an environmental breaker:

```
[collision check fires]
   |
   v
BusBroadcastEventByHash(DAT_0091e0d0, hash("MPursuitBreaker"))
   |
   v
DispatchStartBreakerToScript @ 0x00626510
   |   pushes "StartBreaker" + 1-byte arg onto the script VM stack
   v
script function "StartBreaker"  (bChunk = 0xCA58F64D — never appears as
                                 a code immediate; runtime hash only)
   |
   v
script flips C++ time-scale strategy (world_root_singleton + 0x38)
   |
   v
WorldTickScaleSimulationDt @ 0x006f6cf0 now reads scale < 1.0 each frame
```

**Important:** the user keypress (`DIK_RCONTROL` / `DIK_G`) likely does *not*
travel via this bus — it goes via the action-axis edge detector or a direct
C++ native call. The bus carries the *environmental* trigger only.

### 3.5 Modding hook points

| Goal                                              | Hook                                                                          |
|---------------------------------------------------|-------------------------------------------------------------------------------|
| Snoop every event on the global bus               | Hook `BusBroadcastEventByHash @ 0x61fc10`, log `event[6]`                     |
| Add a custom listener for an existing event       | Call `BusSubscribeListenerByHash(DAT_0091e0d0, hash, cb, ctx)`                |
| Emit a synthetic event from a mod                 | Construct a bus-event handle, call `BusBroadcastEventByHash`                  |
| Suppress one event hash entirely                  | Hook `BusFindOrCreateBucketByHash`, return NULL for that hash                 |

---

## 4. TickableBus — `TickableBus_DispatchActiveSubscribers @ 0x72e0c0`

**Domain:** per-frame tick fan-out for any subsystem that wants a "called once
per frame with dt" handler. Used by EAGL4Anim, particle systems, world-object
animators, several audio entities (see `project_animation_runtime.md`,
`project_audio_subsystem.md`).

### 4.1 Mechanism

`TickableBus_DispatchActiveSubscribers` walks a list of registered subscribers
and, for each one whose enabled-flag is set, dispatches a `Tick(dt)` virtual
call. Unlike the hashed bus in section 3, this is **type-based and ordered**:

* Subscribers register themselves in a fixed list slot (no hash lookup).
* They are ticked in registration order each frame.
* The bus is NOT broadcast-by-hash — there is exactly one event-type per call:
  the per-frame tick.

This pattern is the engine equivalent of a `std::vector<ITickable*>` that's
walked once per frame.

### 4.2 Who rides this bus

| Caller                                                        | What it ticks                                  |
|---------------------------------------------------------------|------------------------------------------------|
| `Particle_And_Emitter_Pools_Initialize @ 0x4ff0a0` consumers  | Particle / Emitter / EmitterGroup animation    |
| EAGL4Anim engine                                              | Vehicle procedural anims fed from physics      |
| Audio TypeA/TypeD/TypeSmooth entities                         | Per-frame mix-state updates                    |
| UIScreenAnim entity class                                     | UI animator timer / blend updates              |

Notably absent: **gameplay vehicle physics**. The 23-slot
`PerPlayerSubsystemTick` array (see `project_runtime_trace.md`) handles AUDIO
+ UI subscribers via TickableBus, but vehicles are integrated via
`ActiveComponents_TickAll -> Vehicle_PullSimResultAndUnpackWheels`, a separate
path.

### 4.3 Modding hook points

| Goal                                                | Hook                                                  |
|-----------------------------------------------------|-------------------------------------------------------|
| Run code every frame from a DLL                     | Register a Tickable subscriber with the bus           |
| Profile per-frame subscribers                       | Hook `TickableBus_DispatchActiveSubscribers @ 0x72e0c0`, measure each callback |
| Suspend animation globally                          | Clear the enabled bits on the subscriber records      |

---

## 5. Game state machine — `ProcessGameStateMachine @ 0x6596a0`

**Domain:** the high-level boot / track-load / race-mode / unload phases of
the game. Despite the name `GameFlowState` in the NFSPluginSDK, the runtime
is *not* an enum — it is a **function-pointer trampoline**.

### 5.1 Dispatcher

```c
void ProcessGameStateMachine(int *state_record) {
  code *fn = (code*)*state_record;
  do {
    if (fn == NULL) break;
    int arg = state_record[1];
    *state_record   = 0;       // clear current
    state_record[1] = 0;       // clear arg
    state_record[2] = 0;       // clear ctx
    (*fn)(arg);                 // run state fn
    bool transitioned = ((code*)*state_record != fn);
    fn = (code*)*state_record;
  } while (transitioned);
  if (state_record[3] != 0)
    ((code*)state_record[3])();  // post-callback
}
```

### 5.2 State-record layout (4 slots = 16 bytes)

| Offset | Field             | Notes                                            |
|--------|-------------------|--------------------------------------------------|
| +0     | current_state_fn  | Function pointer; the "state value" IS this addr |
| +4     | arg               | Passed to the state function                     |
| +8     | ctx               | Auxiliary context (cleared on every dispatch)    |
| +12    | post_cb           | Fired AFTER the loop, regardless of outcome      |

### 5.3 Known state records

* `DAT_00925e70` — primary game-flow record (main loop).
* `DAT_00925e90` — `TheGameFlowManager` (per SDK); a secondary record or an
  int summary; SDK calls it `GameFlowState` but reality is function-ptr.

### 5.4 Sampled state functions

| Address      | Symbol                                | Phase                                  |
|--------------|---------------------------------------|----------------------------------------|
| `0x00664c20` | `StateLoadingFrontEnd`                | Loading screen -> FE root              |
| `0x00659530` | `StateBeginGameFlowLoadTrack`         | Begin track-load sequence              |
| `0x00666fa0` | `StateBeginGameFlowLoadTrackImpl`     | Track-load implementation              |
| `0x00667340` | `BeginGameFlowUnloadTrack`            | Begin track-unload                     |
| `0x00666d00` | `FUN_00666d00`                        | DataLoadingTrack state (read+write)    |
| `0x006672d0` | `FUN_006672d0`                        | Unnamed state (writes record)          |
| `0x006595e0` | `FUN_006595e0`                        | Unnamed (writes record)                |
| `0x00662950` | `FUN_00662950`                        | Unnamed (writes record)                |
| `0x00666aa0` | `DispatchRegionLoaderHandler`         | World-streamer state                   |
| `0x00667010` | `FUN_00667010`                        | Unnamed (writes record)                |

There is no flat numeric enum — each state is its own function. "Transition"
means a state writes `*state_record = next_state_fn` before returning.

### 5.5 Supporting allocator

* `AllocBlockFromGameStatePool @ 0x659250` / `FreeBlockToGameStatePool @ 0x659260`:
  per-state heap allocator (state functions sometimes carry mutable scratch
  in a pool block).
* `FreeBlockIfNonNullToGameStatePool @ 0x4051f0` /
  `ReturnGameStateBlockToPool @ 0x405f30`: free helpers.
* `InitGameModeStateBlock @ 0x5992e0` — separate sub-state machine inside
  race mode.

### 5.6 Modding hook points

| Goal                                          | Hook                                                                       |
|-----------------------------------------------|----------------------------------------------------------------------------|
| Identify the current phase                    | Read function-pointer at `DAT_00925e70`                                    |
| Insert custom logic between transitions       | Write a custom state-fn ptr to `DAT_00925e70` from a hook                  |
| Watch every transition                        | Hook `ProcessGameStateMachine @ 0x6596a0`, log state-fn address each pass  |
| Force a reload                                | Write `StateBeginGameFlowLoadTrack @ 0x659530` to `DAT_00925e70`           |

---

## 6. Career message broadcast

**Domain:** career-progression notifications — race finish, milestone unlock,
reputation award, blacklist progression. Rides on the global hashed bus from
section 3, but is documented separately because it has its own producer
factory and its own well-defined hash vocabulary.

### 6.1 Producer chain

```
ProcessStartRace  @ 0x60dbd0   -> race init
ProcessAddRacer   @ 0x601f90   -> register racer/player
[gameplay tick]
ProcessKnockoutRacer        @ 0x611440
ProcessNotifyRacePlacement  @ 0x60aa00  <-- the central race-end notify
   |
   v
MilestoneProgressEventConstructor @ 0x5dd670
   |   constructs a message event handle with the milestone hash
   v
BusBroadcastEventByHash(DAT_0091e0d0, MNotifyMilestoneProgress)
   |
   v
[multiple listeners fan out:]
   +- HandleFrontendRaceEventDispatch @ 0x58bd10
   |     (multiplexes to FUN_00632d20, FUN_006357a0, etc.)
   +- audio subscribers
   +- save / blacklist update
```

### 6.2 Career anchor functions

| Address     | Symbol                                              |
|-------------|-----------------------------------------------------|
| `0x60dbd0`  | `ProcessStartRace`                                  |
| `0x60deb0`  | `ProcessAbandonRace`                                |
| `0x601f90`  | `ProcessAddRacer`                                   |
| `0x60dae0`  | `ProcessGetRacerIndex`                              |
| `0x611440`  | `ProcessKnockoutRacer`                              |
| `0x60aa00`  | `ProcessNotifyRacePlacement`                        |
| `0x60e030`  | `ProcessAwardPoints` (reputation / skill)           |
| `0x612220`  | `ProcessAwardPlayerBounty`                          |
| `0x5fe600`  | `ProcessAwardBonusTime`                             |
| `0x605140`  | `ProcessChallengeComplete`                          |
| `0x6120c0`  | `ProcessShowRaceOverSummary`                        |
| `0x5dd670`  | `MilestoneProgressEventConstructor`                 |
| `0x5dd5f0`  | `GetMilestoneProgressMessageHash`                   |
| `0x5de370`  | `GetMessageHashMilestoneReached`                    |
| `0x4058e0`  | `GetPlayerRepMessageHash`                           |
| `0x626480`  | `GetEventHashPlayerEnterPursuit`                    |
| `0x604440`  | `GetRacePlacementMessageHash`                       |
| `0x5db8a0`  | `GetRaceTimeBroadcastMessageHash`                   |
| `0x58bd10`  | `HandleFrontendRaceEventDispatch`                   |
| `0x6dfaf0`  | `GetGameMasterDataPointer`                          |

### 6.3 Known career-message hashes (preimage strings)

| Hash preimage                | Producer                                                  |
|------------------------------|-----------------------------------------------------------|
| `MNotifyMilestoneProgress`   | `MilestoneProgressEventConstructor` after race end        |
| `MNotifyMilestoneReached`    | `GetMessageHashMilestoneReached` callsites                |
| `MNotifyPlayerRep`           | `ProcessAwardPoints` reputation award                     |
| `MNotifyRacePlacement`       | `ProcessNotifyRacePlacement`                              |
| `MPlayerEnterPursuit`        | `GetEventHashPlayerEnterPursuit`                          |
| `MPursuitOver`               | pursuit-end fan-out                                       |

### 6.4 Career globals

* `CAREER_DATA` string @ `0x89da2c`
* `CAREER_COMPLETED_DATA` @ `0x89ceb8`
* `GAME_COMPLETED_DATA` @ `0x89ced0`
* `BLACKLIST_PURSUIT_MILESTONES_%02d` @ `0x89a111c`
* `g_pGRaceStatus @ 0x91e000` — active race state; per-racer data at +0x1968

### 6.5 Save-integrity note

`MSG_R_BI_DATACRC @ 0x8b6b7c` is **not** a save-CRC tag despite its name. It
sits in the netcode message-name table next to `MSG_R_SC_RESTARTLOAD` /
`SERVERSTATE_LOADING` / `CLIENTSTATE_LOADING` and has zero code xrefs — an
orphan diagnostic string for network bundle-integrity sync. The actual save
integrity uses **MD5**, not CRC (see `project_save_load.md` /
`ComputeMd5OfSaveBuffer @ 0x57f920`).

### 6.6 Modding hook points

* For "why doesn't milestone X unlock?": hook the listener subscribers
  (`FUN_00632d20`, `FUN_006357a0`) and log the message-payload shape.
* For UI absences: hook `HandleFrontendRaceEventDispatch @ 0x58bd10`.
* For custom rep/milestone behavior: trace
  `ProcessNotifyRacePlacement -> MilestoneProgressEventConstructor` and
  inject a custom listener via
  `BusSubscribeListenerByHash(DAT_0091e0d0, GetMilestoneProgressMessageHash(), cb, ctx)`.

---

## 7. PursuitBreaker triad — one mechanic, three event hashes

This is the canonical example of why hashed buses make modders sad:
**PursuitBreaker is split across three distinct event hashes** on the bus from
section 3. If you only intercept one, you only see a third of the mechanic.

### 7.1 The three hashes

| String                | Address       | Hash cacher                                              | Cached global                                | Role                                                                                       |
|-----------------------|---------------|----------------------------------------------------------|----------------------------------------------|--------------------------------------------------------------------------------------------|
| `"MPursuitBreaker"`   | `0x00896da8`  | `GetMPursuitBreakerEventHash_Cached @ 0x4b5880`          | `DAT_00913c34`                               | Trigger — fired when an environmental breaker is hit. Subscriber: `DispatchStartBreakerToScript @ 0x626510` (invokes script `"StartBreaker"`). |
| `"MBreakerStopCops"`  | `0x00890c9c`  | `GetMBreakerStopCopsEventHash_Cached @ 0x405b70`         | `DAT_0090d940` (gated by bit 0 of `DAT_0090d944`) | Effect — fired AFTER trigger to actually disable nearby cops.                              |
| `"PursuitBreaker"`    | `0x00896dec`  | n/a (registered via inline `stringhash32`)                | n/a                                          | Audio fader — `HandlePursuitBreakerSoundEvent @ 0x4f0fb0` plays the GPATH5 sound effect.   |

Distinct strings, distinct hashes, distinct subscribers — coincidentally
all firing within a few frames of each other.

### 7.2 Sound-fader path

`ConstructPursuitBreakerSoundFader @ 0x4f72a0` builds a fader object (vtables
`PTR_FUN_00899a24` + `PTR_FUN_00899200`) and registers two listeners:

* `stringhash32("MomentStrm")` -> `LAB_004f0ba0`
* `stringhash32("PursuitBreaker")` -> `HandlePursuitBreakerSoundEvent @ 0x4f0fb0`

The handler at `0x4f0fb0` pushes an `"Snd"` event with a MomentStrm payload
built by `ConstructWaveFormatDescriptor` — i.e. the radio-distortion / low-pass
filter audio cue. Asset string `"GPATH5: Pursuit breaker sound filter fader"`
@ `0x00898867`.

### 7.3 Trigger flow (inferred — collision callsite not yet located)

```
[player vehicle collides with breaker object]
     |
     v
[per-frame collision check fires]
     |
     v
BusBroadcastEventByHash(DAT_0091e0d0, hash("MPursuitBreaker"))
     |
     v
DispatchStartBreakerToScript @ 0x626510
     |    pushes "StartBreaker" + byte arg into script VM
     v
script "StartBreaker" function
     |
     v
C++ native bound to the script function:
     (a) flips time-scale strategy at world_root+0x38 (slow-mo)
     (b) broadcasts MBreakerStopCops to actually disable cops
```

`HandlePursuitBreakerSoundEvent` runs on a parallel path on the same bus for
the audio cue.

### 7.4 Negative result — do not conflate

* **GameBreaker / SpeedBreaker** (player slow-mo, RCtrl key) is a separate
  mechanic. Strings: `GAME_ACTION_GAMEBREAKER @ 0x8a5a24`,
  `GAMEACTION_GAMEBREAKER @ 0x8a6608`.
* **PursuitBreaker** (environmental cop-stop) is what section 7 documents.
  Strings: `MPursuitBreaker`, `PURSUIT_BREAKER_%d`, `EPursuitBreaker`.

Both mechanics share the `WorldTickScaleSimulationDt @ 0x6f6cf0` slow-mo
machinery (world-root+0x38 time-scale strategy slot), but the trigger paths
are different — PursuitBreaker fires from collision, SpeedBreaker fires from
user input.

### 7.5 Static-table references

| Address     | Hash / String                            | Notes                                       |
|-------------|------------------------------------------|---------------------------------------------|
| `0x8a54fc`  | `0xDDA7829B` = bChunk(`EBreakerStopCops`)| Sorted hash table                           |
| `0x8a5544`  | bChunk(`EPursuitBreaker`)                | Companion entry                             |
| `0x8a01b4`  | `"PURSUIT_BREAKER_%d"`                   | Format only — no direct xref                |
| `0x8a7220`  | `"EPursuitBreaker"`                      | No code xrefs (table-driven)                |
| `0x8a68d4`  | `"EBreakerStopCops"`                     | No code xrefs (table-driven)                |
| `0x89ffe0`  | `"TIP_PURSUIT_BREAKERS"`                 | Localized UI tip                            |

---

## 8. Event-hash registry

Known string preimages for hashes that ride one of the buses. All hashes are
**bChunk** = Bob Jenkins mix3 with seed `0xABCDEF00` (see
`project_bchunk_hash.md`).

| Preimage string                  | Cacher / consumer                                         | Bus                       |
|----------------------------------|-----------------------------------------------------------|---------------------------|
| `MPursuitBreaker`                | `GetMPursuitBreakerEventHash_Cached @ 0x4b5880`           | DAT_0091e0d0              |
| `MBreakerStopCops`               | `GetMBreakerStopCopsEventHash_Cached @ 0x405b70`          | DAT_0091e0d0              |
| `PursuitBreaker`                 | `HandlePursuitBreakerSoundEvent @ 0x4f0fb0`               | DAT_0091e0d0 (audio)      |
| `MomentStrm`                     | sound-fader listener                                      | DAT_0091e0d0 (audio)      |
| `MNotifyMilestoneProgress`       | `GetMilestoneProgressMessageHash @ 0x5dd5f0`              | DAT_0091e0d0 (career)     |
| `MNotifyMilestoneReached`        | `GetMessageHashMilestoneReached @ 0x5de370`               | DAT_0091e0d0 (career)     |
| `MNotifyPlayerRep`               | `GetPlayerRepMessageHash @ 0x4058e0`                      | DAT_0091e0d0 (career)     |
| `MNotifyRacePlacement`           | `GetRacePlacementMessageHash @ 0x604440`                  | DAT_0091e0d0 (career)     |
| `MPlayerEnterPursuit`            | `GetEventHashPlayerEnterPursuit @ 0x626480`               | DAT_0091e0d0              |
| `MPursuitOver`                   | pursuit-end fan-out                                       | DAT_0091e0d0              |
| `StartBreaker`                   | script-VM function `0xCA58F64D`                           | script VM, NOT bus        |
| `BASE`                           | `bChunk("BASE") = 0xA6B47FAC`                             | reference value           |
| `EPursuitBreaker`                | static hash table @ `0x8a5544`                            | table-driven              |
| `EBreakerStopCops`               | static hash table @ `0x8a54fc` (= `0xDDA7829B`)           | table-driven              |

The PursuitBreaker hash `0xCA58F64D` for `"StartBreaker"` **never appears as
a code immediate** in `.text` or `.rdata` — confirming the runtime-only,
cached-hash idiom.

---

## 9. Comparison table

Side-by-side summary of all five buses for quick reference:

| #   | Name                          | Anchor / address                                       | Subscribe API                                                                  | Broadcast / dispatch API                                                                                | Storage              | Typical use cases                                                                                            |
|-----|-------------------------------|--------------------------------------------------------|--------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------|----------------------|--------------------------------------------------------------------------------------------------------------|
| 1   | FNG event bus                 | `PostUIEventToNamedNode @ 0x516c90`                    | `InsertOrAssignTypeRegistry(...)` (per-widget) + scene-node child registration | `PostUIEventToNamedNode` -> `ScheduleUIDeferredEvent` -> queue at +0x4118 -> `DrainUIDeferredEventQueue_PerFrame @ 0x5c1460` | Per-FE-root deferred queue + subscriber list at +0xe0 | HUD widget updates (speed digits, milestone popup, lap counter); push-model UI events |
| 2   | DAT_0091e0d0 (global hashed)  | `BusBroadcastEventByHash @ 0x61fc10`                   | `BusSubscribeListenerByHash @ 0x61fd00`                                        | `BusBroadcastEventByHash @ 0x61fc10` -> `BusDispatchEventToListenerFilters @ 0x5f9da0`                  | Hash-bucket list (`BusFindOrCreateBucketByHash @ 0x61fb40`) | Audio cues; SpeedBreaker / PursuitBreaker triggers; career messages; cross-subsystem events |
| 3   | TickableBus                   | `TickableBus_DispatchActiveSubscribers @ 0x72e0c0`     | Register `ITickable` subscriber in the bus list (engine-internal)              | Per-frame implicit; one event-type (Tick(dt))                                                           | Ordered subscriber list | EAGL4Anim ticks; particle/emitter animation; audio entity ticks; UI animator                                 |
| 4   | Game state machine            | `ProcessGameStateMachine @ 0x6596a0`                   | Write a function-ptr to state-record +0                                        | The dispatcher loop itself — runs the function-ptr, re-reads on transitions                              | 4-slot record at `DAT_00925e70` (and `DAT_00925e90`) | High-level boot / track-load / race / unload phase management                                                |
| 5   | Career message broadcast      | `MilestoneProgressEventConstructor @ 0x5dd670`         | `BusSubscribeListenerByHash(DAT_0091e0d0, <hash>, ...)`                        | Rides on bus #2 via `BusBroadcastEventByHash`                                                           | Bus #2 hash buckets    | Race finish, milestone unlock, reputation award, pursuit-enter/over notifications                             |

Notes:

* Bus #5 is technically a heavy user of bus #2 — listed separately because of
  the dedicated producer factory (`MilestoneProgressEventConstructor`) and
  the well-defined hash vocabulary.
* Bus #3 (TickableBus) is NOT broadcast-by-hash — it's a per-frame fan-out of
  one implicit `Tick(dt)` event, more like a registered-callback list than an
  event bus in the classic sense.
* Bus #4 is a state machine, not a bus — included because it's the next
  question every modder asks: "how does the game know what phase it's in?"

---

## 10. Modding event buses

This section consolidates the practical hook points for each bus into one
reference.

### 10.1 General workflow

1. **Identify the bus** the event you care about rides on. The five-question
   triage:
    * Is it a UI widget update? -> bus #1 (FNG).
    * Is it a global hashed message between subsystems? -> bus #2.
    * Is it a "give me a frame tick" handler? -> bus #3.
    * Is it a game-phase transition (loading, racing, frontend)? -> bus #4.
    * Is it a race-end / milestone / reputation event? -> bus #5 (on top of #2).
2. **Find the hash preimage** if it's a hashed bus. Search for the
   `Get<Name>EventHash_Cached` pattern around suspected callsites; the string
   xref tells you the preimage.
3. **Pick a hook layer**: producer (block before broadcast), bus-internal
   (filter every event), or listener (subscribe with your own callback). Each
   has different invariants; see per-bus tables above.

### 10.2 Registering a listener on bus #2 (most common case)

```c
// 1. Compute the hash once and cache.
uint32_t my_hash = bChunk("MyEventName");  // mix3, seed 0xABCDEF00

// 2. Subscribe.
BusSubscribeListenerByHash(
    DAT_0091e0d0,       // global bus singleton
    my_hash,            // event key
    my_callback,        // callback signature matches engine convention
    my_ctx              // user context pointer
);
```

Once registered, every broadcast of `my_hash` will invoke `my_callback`
synchronously inside `BusBroadcastEventByHash`. There is no automatic
unregister — the listener lives until the bus is destroyed.

### 10.3 Intercepting all events on bus #2

Hook `BusBroadcastEventByHash @ 0x61fc10`. The hash is `event[6]` (offset
0x18 into the constructed event handle). Log it; cross-reference with the
hash registry (section 8) to identify the event. Unknown hashes can be
brute-forced offline against a wordlist using the mix3 implementation
documented in `project_bchunk_hash.md`.

### 10.4 Force-flushing the FNG queue

```c
DrainUIDeferredEventQueue_PerFrame(ui_root);
```

`ui_root` is the FE/UI context object. This will flush every queued event
synchronously — useful after injecting a synthetic event mid-frame.

### 10.5 Injecting a synthetic FNG event

Construct a 32-byte event object with:

```
event[0]  = (vtable) PTR_FUN_008a2c90
event[1]  = 0xABADCAFE          // prev fence
event[2]  = 0xABADCAFE          // next fence
event[3]  = payload (param_2)
event[4]  = event hash
event[5]  = command / value
event[6]  = target node ptr     // or 0xfffffffc for broadcast, NULL for type-registry
event[7]  = priority
```

Then link it into the doubly-linked list anchored at `ui_root+0x4118` and
bump the counter at `ui_root+0x4114`. The next call to
`FE_PerFrameTick_DrainQueueAndUpdateChildren` will pick it up.

### 10.6 Replacing a game-flow state

```c
// from a hook firing somewhere in the frame:
*(void**)(DAT_00925e70 + 0)  = my_state_fn;       // current state
*(int*)  (DAT_00925e70 + 4)  = my_arg;            // optional arg
*(void**)(DAT_00925e70 + 12) = my_post_callback;  // optional post-cb
```

On the next pass of `ProcessGameStateMachine`, your function runs. To
transition further from inside, write the next state to slot 0 before
returning.

### 10.7 Pitfalls

* **Hash collisions** are possible but rare with mix3+seed. If two events
  share a bucket, your listener will be invoked for both — filter on payload
  fields, not hash alone.
* **Three-hash mechanics** (PursuitBreaker, section 7). Intercepting one of
  the three hashes does *not* give you the whole mechanic. Always check
  whether the user-visible feature has multiple producers.
* **Hash never appears as immediate.** `StartBreaker` (`0xCA58F64D`) is
  computed at runtime only. Byte-scanning `.text` and `.rdata` for an
  immediate will return zero hits — you must locate the cached-hash getter
  via its string xref.
* **TickableBus is per-frame, no filter.** Heavy work in a Tickable callback
  costs a real frame; profile first.
* **State-machine transitions are NOT atomic with frame boundaries.** A
  state function can transition multiple times within one
  `ProcessGameStateMachine` call. If you hook a state, expect to be invoked
  re-entrantly.

---

## Appendix A — Source memory entries

This document is consolidated from the following memory notes (under
`~/.claude/projects/.../memory/`):

* `project_fng_dispatch_complete.md` — FNG bus (wave-17)
* `project_speedbreaker.md` — audio event bus DAT_0091e0d0 (wave-9)
* `project_pursuitbreaker_environmental.md` — three event hashes
* `project_career_milestones.md` — message broadcast
* `project_game_state_machine.md` — function-pointer trampoline

Cross-references:

* `project_bchunk_hash.md` — hash algorithm details
* `project_audio_subsystem.md` — audio entity ticking via TickableBus
* `project_animation_runtime.md` — EAGL4Anim ride on TickableBus
* `project_fe_engine.md` — FE manager that owns the FNG bus queue
* `project_runtime_trace.md` — 23-slot PerPlayerSubsystemTick distinction
* `project_save_load.md` — MD5 save-integrity (correction re. `MSG_R_BI_DATACRC`)
