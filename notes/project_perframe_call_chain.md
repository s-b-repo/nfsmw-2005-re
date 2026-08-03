---
name: NFSMW per-frame call chain (GameFrameTick to integrator)
description: Map of how the engine threads delta-time from WinMain through the per-frame loop down to the per-entity Step
type: project
originSessionId: c4edf485-e85f-4e2f-ac31-e021ba66e8d6
---
The per-frame call chain in `speed.exe` is layered through several accumulators and dispatchers before reaching the actual physics step. Useful for routing future work — knowing which level you're at avoids walking the wrong subsystem.

```
WinMain main loop
  └─ GameFrameTick(elapsed_ms)                       0x00663d30
       ├─ ProcessSimulationStep(per_frame_seconds)   0x00661280
       │   └─ SimulationStep_AccumulateAndTrace …    0x0065fe90
       │       └─ ProfilerTraceBuffer_Encode         0x0064c7d0
       │      // ↑ profiler/stats only; NOT the actual physics step.
       │
       ├─ PeriodicTimerDispatcher_Run                0x007ec59c
       │      // cron-style: stride-20 array walked, callbacks fired when next-due time hits.
       │
       ├─ TickableBus_DispatchActiveSubscribers      0x0072e0c0
       │      // event bus; only known subscriber is a NO-OP stub at 0x004afa70.
       │
       ├─ ComputeElapsedSecondsFromTimer             0x00642e60   → returns dt_seconds
       │
       ├─ SubsystemDtAccumulator(dt_seconds)         0x0064a680   → THE dt-distribution junction
       │      // accumulates dt into DAT_00925e9c, then once per frame:
       │      ├─ if (IsWorldSimActive() && World_GetCurrentState() == 3) {  // gameplay only
       │      │     FUN_00779a30(dt)   // → TrackedObjList_TickEach + SecondaryTrackedList_TickEach
       │      │     ActiveComponents_TickAll(dt)  0x004ba940
       │      │           ├─ for each entry @ DAT_00913e74[0..count]:
       │      │           │     Vehicle_PullSimResultAndUnpackWheels(entry, dt)  0x004b15e0
       │      │           │           // backs up prev pos, queries VehicleAgent_QuerySimResult_Virtual
       │      │           │           // (vt[1] of this+8), unpacks 4 wheels (stride 0x44):
       │      │           │           //   per-wheel pos/contact-flag/friction/material-handle
       │      │           │           // computes velocity = (new_pos - prev_pos) / dt
       │      │           └─ for each entry @ DAT_00913ed4[0..count]:
       │      │                 Camera_PullSimResultIfActive(entry, dt)  0x004b1a10
       │      │     FUN_006e7a00(dt)   // 4 misc subsystem updaters
       │      │   }
       │      ├─ FUN_00480e40(accumulated_dt)         (PerPlayerEntityUpdate_Dispatch)
       │      └─ FUN_00480c10(accumulated_dt)         (PostStateUpdate_DispatchPair)
       │              ├─ FUN_0047c880(dt) → PerPlayerSubsystemTick
       │              │     // CORRECTED 2026-05-08: 23 slots at [0x919624 .. 0x91a034]
       │              │     // 0x70-byte stride. Each slot is a LINKED LIST head,
       │              │     // not a single pointer. List nodes are heap-allocated
       │              │     // entities; the vtable lives at link[-4]. The indirect
       │              │     // call is at 0x47c8af (labeled perplayer_indirect_call_vt2),
       │              │     // CALL [EDX + 0x8] where EDX is the loaded vtable.
       │              │
       │              └─ FUN_0064c2d0(dt) → KeyframeTimeline_Advance
       │                    // audio/animation timeline scrubber for two channels
       │                    // (DAT_00925ab0, DAT_00925ad0). Not physics.
       │
       ├─ ProcessGameStateMachine(&DAT_00925e70)     0x006596a0
       ├─ FUN_004d0610(scene_root, DAT_009259bc)     // frontend / DirectX device path
       ├─ ProcessDeferredFreeQueue                   0x00633ef0
       └─ ... render submit chain ...
```

**Why:** Several promising-looking entry points are dead ends or instrumentation:
- `ProcessSimulationStep` and its descendants (FUN_0065fe90, FUN_0064c7d0) only do profiler bookkeeping.
- The TickableBus subscriber is a no-op stub.
- `FUN_004d0610` is frontend/DirectX, not physics.

**The integrator entry** for per-vehicle work is the `slot[-1].vt[2](dt)` call in `PerPlayerSubsystemTick (0x0047c880)`. The slot array at `&DAT_00919624` is built dynamically (likely populated when a player/vehicle spawns), so static analysis can identify *callees* but not which concrete vtable is wired in at runtime.

**How to apply:**
- Set a runtime breakpoint on `0x0047c890` (the indirect call inside `PerPlayerSubsystemTick`) to capture the actual `vt[2]` target — that's the per-frame `Step` address.
- The vtable layout at slot `[-1]` is the per-player-entity vtable; expect 4 slots (player 1..4) at `&DAT_00919624 + n*0x70*4`.
- Globals on the chain: `DAT_00925e9c` (dt accumulator), `DAT_009259bc` (seconds-per-step from ProcessSimulationStep), `DAT_009203b0` (mission/state context root).
