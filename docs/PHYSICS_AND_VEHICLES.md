# Physics and Vehicles — Consolidated Reference

Source: NFSMW PC `speed.exe` (IMAGE_BASE = 0x00400000, no ASLR, Wine 1:1 mapping).

This document consolidates the EAGL physics integrator, the RigidBody object layout, the per-frame call chain that feeds it, the pvehicle class hierarchy and its 28-key component dispatch, the suspension variants, the cracked handling attributes, and the live-debugger findings from the 2026-05-09 in-race attach.

---

## 1. Overview — corrected execution model

**The physics integrator runs INLINE ON THE MAIN THREAD.** Earlier notes that asserted a "physics worker thread" were **wrong** — a full static enumeration of every `__beginthreadex` callee in `speed.exe` shows only four worker threads exist:

| Thread entry | Identity |
|---|---|
| `FileSystemWorker_JobLoop_DispatchVt1 @ 0x7ed55e` | EAGL FileSystem job worker (passed the literal string `"File System"`) |
| `NetworkWorker_ThreadEntry @ 0x7976b0` | Network worker (priority `DAT_009b5ab0`, stack 0x3800) |
| `WaitableTimer_ThreadEntry @ 0x7ec601` | Waitable-timer thread (`CreateWaitableTimerA`, period `10000000/param`) |
| `AssetStreamingWorker_ThreadEntry @ 0x7ef80a` | Asset streaming worker (loops on `DAT_009bb158`) |

No physics worker exists. The thread infrastructure entry points are also fully named:

* `CreateWorkerThread_Wrapper @ 0x7ec44f` — the sole `__beginthreadex` call site.
* `ThreadEntry_Trampoline_SetStartedThenDispatch @ 0x7ec1d3` — bootstrap that sets `*arg=1` then jumps to `arg[1](arg[2])`.

Physics ticks in the same call frame as the per-frame `WorldPhysicsDispatch_MainThreadCoordinator @ 0x75aad0`. Live breakpoints missed it earlier not because of a thread boundary but because of a `World_GetCurrentState() == 3` gate inside `SubsystemDtAccumulator` — the integrator is skipped entirely outside gameplay state 3.

This single correction reshapes the debugger workflow: any breakpoint on the indirect call site inside `0x75aad0` will fire on the main thread once the game reaches in-race state, with no thread switching required.

---

## 2. EAGL physics integrator — PhysicsWorldCoordinator

The integrator is reached through a per-frame virtual dispatch on the **PhysicsWorldCoordinator** singleton.

### Singleton identity

* Global pointer: `DAT_009885c8` (the "this" of the coordinator).
* Primary vtable: `PTR_FUN_008b0e18`.
* Constructor: `PhysicsWorldCoordinator_ConstructAndInstallSingleton @ 0x6fce10`.
* Integrator entry: `(*DAT_009885c8)[+0x44]()` — virtual slot **+0x44** on the primary vtable.

The concrete function pointer at slot +0x44 is bound at runtime when the coordinator constructor installs its vtable. Static analysis cannot resolve it — it must be captured with a live attach at the indirect-call site inside `WorldPhysicsDispatch_MainThreadCoordinator @ 0x75aad0`.

### Coordinator construction

`PhysicsWorldCoordinator_ConstructAndInstallSingleton` installs seven sub-vtables at fixed offsets on `this`:

| Offset | Vtable |
|---|---|
| +0x00 | `PTR_FUN_008b0e18` (primary — holds the integrator at slot +0x44) |
| +0x08 | `PTR_LAB_008b0e10` |
| +0x2c | `PTR_LAB_008b0dfc` |
| +0x38 | `PTR_LAB_008b0de0` |
| +0x48 | `PTR_LAB_008b0d78` |
| +0x50 | `PTR_LAB_008b0d70` |
| +0x58 | `PTR_LAB_008b0d60` |

The constructor also:

* Wires asset-load completion callbacks.
* Iterates 8 cop slots using `cop%d`-style string-hashed names.
* Constructs the embedded event-report object.
* Stores the singleton pointer at three sites within the constructor (`0x6fd146`, `0x6fd3fb`, `0x6fd402`) — the `DAT_009885c8 = this` self-store happens at all three.

### PhysicsWorldCoordinator vs world_root_singleton

These are **two distinct objects** and were conflated in earlier notes:

| Object | Address | Role |
|---|---|---|
| **PhysicsWorldCoordinator** | `DAT_009885c8` | Vtable-bearing dispatcher. Slot +0x44 = integrator step entry. |
| **world_root_singleton** | (separate global) | 0x90-byte state owner. Allocated by `FUN_006fc3a0` from RigidBody pool `DAT_00925b30`. Holds dt, time-scale, play-state; argument to `WorldTickScaleSimulationDt @ 0x6f6cf0`. |

### Per-frame state reader

The main thread reads physics state via `pvehicle_AggregatePhysicsState_PerFrameStateReader @ 0x694160` — the leaf state collector. It aggregates from sub-objects in roughly this layout:

| Field | Role |
|---|---|
| `this[+0x60]` | physics middleware object (uses vt[1], vt[4], vt[7], vt[8]) |
| `this[+0x64]` | suspension system (vt[2] returns vec3 compression) |
| `this[+0x68]` | state object (vt[1] returns int state code) |
| `this[+0x70]` | track/lane object (vt[+0x34] returns float position parameter) |
| `this[+0x6c]` | 4-wheel/tire array (slip + force data) |

### Key globals around the integrator

| Global | Role |
|---|---|
| `DAT_009885c8` | PhysicsWorldCoordinator (vtable-bearing). vt[+0x44] = integrator. |
| `DAT_00925b30` | Universal RigidBody pool (332-byte slots). |
| `DAT_009b0bc8` | Active vehicle update queue (doubly-linked). |
| `DAT_008a92d4` | Ghost/solid threshold (mass < threshold → ghost body). |
| `_DAT_0089096c`, `_DAT_00890968` | Float clamping bounds (min/max). |
| `_DAT_008aac20`, `_DAT_008aabd8` | Track parameter bounds. |
| `DAT_00925e9c` | dt accumulator. |
| `DAT_009259bc` | seconds-per-step from ProcessSimulationStep. |

---

## 3. RigidBody — 332-byte object

The universal physics body is a 332-byte struct allocated from a single pool.

### Pool and factory

* Pool: `DAT_00925b30` (universal RigidBody pool; 332-byte slots).
* Sole allocator: `RigidBody_FactoryFromAttributes_PhysicsPoolAlloc @ 0x6895a0`. Reads the `SimplePhysics` flag (hash `0xEE0011E3`) to pick the ghost vs solid construction path.
* Component creator: `CreateRigidBodyComponent_PhysicsObjectInit @ 0x688660` — also iterates the `BEHAVIORS` StringKey list (hash `0xDA5F19F9`) via `LookupAttributeIteratorByHash` / `GetAttributeIteratorChildCount` to attach `EffectsSmackable` child components via `FUN_00684bb0`.
* Constructor: `RigidBody_ConstructorAndEAGLPhysicsRegister @ 0x6883e0` — initializes 5 vtables and registers with EAGL via `BChunkHash_JenkinsMix3("Physics")`.
* Inner state init: `RigidBody_InitializeInnerStateTree @ 0x669910`.
* Mass-inverse init: `RigidBody_ComputeMassInverseFromAttribute @ 0x669c00` — **name suspect**: actually reads the `DROPOUT` 2-element Float attribute (hash `0x44F1273B`), not the real `MASS` hash `0x4A56503D`.

### Vtable cluster (5 vtables installed by the constructor)

| Address | Role |
|---|---|
| `PTR_FUN_008aa5b0` | Primary |
| `PTR_FUN_008aa5a8` | Secondary |
| `PTR_FUN_008aa518` | — |
| `PTR_FUN_008aa4f8` | — |
| `PTR_FUN_008aa4dc` | — |

### Field layout (332 bytes total)

```
+0x00       vtable ptr (primary)
+0x04..0x0F flags / state
+0x10..0x3F 4x4 transform matrix (column-major; 16 floats)
+0x40       inertia tensor or ref
+0x44       mass inverse
+0x48..0x7F velocity, angular velocity, forces, torques
+0x80..0xFF per-wheel / suspension data (4 wheels)
+0xF0       countdown timer (DROPOUT timed-force decay)
+0xF4       DROPOUT[0] (timed-force config, index 0)
+0xFC       AUTO_SIMPLIFY (Smackable::mAutoSimplify, LOD cull threshold)
+0x100..0x14B  additional state / caching (and live-observed pos/vel snapshot)
```

Notes:

* The +0x100..+0x140 floats are routinely seen as position / velocity vectors in live attaches (e.g., `-2881.929, -167.801, -3193.314, -110.572`).
* The matrix at +0x10..+0x3F is the body-to-world transform; the integrator updates it from velocity at +0x48.
* Mass inverse at +0x44 is what every impulse path scales force by — write here directly to mass-override at runtime.
* The DROPOUT pair (hash `0x44F1273B`) drives `FUN_0066a0b0`: while `+0xF0 > 0`, the routine applies force `= -(dt * DROPOUT[1])` via SimContext vt[+0x7c], then expires via vt[+0x08].

---

## 4. Per-frame call chain

Full WinMain-to-integrator chain. Profilers, stat-trace, and audio dispatchers are called out explicitly because they are **dead ends** for physics work.

```
WinMain main loop
  └─ GameFrameTick(elapsed_ms)                       0x00663d30
       ├─ ProcessSimulationStep(per_frame_seconds)   0x00661280
       │   └─ SimulationStep_AccumulateAndTrace      0x0065fe90
       │       └─ ProfilerTraceBuffer_Encode         0x0064c7d0
       │      // ↑ profiler / stats only; NOT physics.
       │
       ├─ PeriodicTimerDispatcher_Run                0x007ec59c
       │      // cron-style: stride-20 array of (due, cb); fires when next-due
       │      //   time hits. Asset/network housekeeping, not physics.
       │
       ├─ TickableBus_DispatchActiveSubscribers      0x0072e0c0
       │      // event bus; only known subscriber is a NO-OP stub at 0x004afa70.
       │
       ├─ ComputeElapsedSecondsFromTimer             0x00642e60   → dt_seconds
       │
       ├─ SubsystemDtAccumulator(dt_seconds)         0x0064a680   ← THE dt junction
       │      // accumulates dt into DAT_00925e9c then, once per frame:
       │      ├─ if (IsWorldSimActive() && World_GetCurrentState() == 3) {
       │      │     FUN_00779a30(dt)                 // TrackedObjList ticks
       │      │     ActiveComponents_TickAll(dt)     0x004ba940
       │      │           ├─ for each entry @ DAT_00913e74[0..count]:
       │      │           │     Vehicle_PullSimResultAndUnpackWheels   0x004b15e0
       │      │           │        → VehicleAgent_QuerySimResult_Virtual
       │      │           │           → pvehicle_MatchTypeAndDispatch_vt1   0x6a4040
       │      │           │              → pvehicle_DispatchSubobjVt1AndVt4 0x694700
       │      │           │                 → body[+0x98]->vt[1]/vt[4]  ← LEAF
       │      │           └─ for each entry @ DAT_00913ed4[0..count]:
       │      │                 Camera_PullSimResultIfActive            0x004b1a10
       │      │     FUN_006e7a00(dt)                 // 4 misc subsystem updaters
       │      │
       │      │     WorldPhysicsDispatch_MainThreadCoordinator   0x75aad0
       │      │        ├─ if (DAT_009885c8 != 0):
       │      │        │     (*(DAT_009885c8 + 0x44))()   ← INTEGRATOR (virtual)
       │      │        ├─ FUN_00747950   // vehicle update queue
       │      │        ├─ FUN_007310b0   // world object physics
       │      │        ├─ FUN_00755340   // AI / traffic physics
       │      │        ├─ FUN_00755450   // collision / impact
       │      │        └─ FUN_00755590   // post-step cleanup
       │      │   }
       │      ├─ FUN_00480e40(accumulated_dt)        // PerPlayerEntityUpdate_Dispatch
       │      └─ FUN_00480c10(accumulated_dt)        // PostStateUpdate_DispatchPair
       │              ├─ FUN_0047c880(dt) → PerPlayerSubsystemTick
       │              │     // 23 slots at [0x919624 .. 0x91a034], stride 0x70.
       │              │     // Each slot is a linked-list head; nodes are heap
       │              │     // entities; vtable lives at link[-4]. Indirect call
       │              │     // at 0x47c8af = CALL [EDX + 0x8].
       │              │     // NOTE: this 23-slot array is for AUDIO + UI only —
       │              │     //   NOT vehicles (corrected 2026-05-09 in-race trace).
       │              │
       │              └─ FUN_0064c2d0(dt) → KeyframeTimeline_Advance
       │                    // audio / animation timeline scrubber.
       │
       ├─ ProcessGameStateMachine(&DAT_00925e70)     0x006596a0
       ├─ FUN_004d0610(scene_root, DAT_009259bc)     // frontend / DirectX device
       ├─ ProcessDeferredFreeQueue                   0x00633ef0
       └─ ... render submit chain ...
```

### Key points

* The `World_GetCurrentState() == 3` gate inside `SubsystemDtAccumulator` is the reason boot-time live captures miss the integrator. The integrator only runs in gameplay state 3.
* `ActiveComponents_TickAll` is the per-vehicle path. It walks `DAT_00913e74` (entry-array head). Each entry is an audio entity whose `this[+8]` points to the actual pvehicle body — see Section 9.
* `WorldPhysicsDispatch_MainThreadCoordinator @ 0x75aad0` is the physics-world step driver. The virtual `(*DAT_009885c8)[+0x44]` indirect call inside it is **the integrator**.
* `PerPlayerSubsystemTick` (the 23-slot dispatcher at `&DAT_00919624`) is audio + UI, **not vehicles**. This was a long-standing misunderstanding now corrected by the 2026-05-09 in-race trace.

---

## 5. PVehicle class hierarchy

The "pvehicle" (physics vehicle) is the central drivable entity. Concrete subclasses split along body-class and AI-vs-player lines.

### Inline RTTI inventory @ 0x008add1c

Immediately after the 24-method `vtbl_pvehicle_ComponentList @ 0x008adcc0` is an inline string list that enumerates every pvehicle subclass and component-key. The list spans 0x008add1c..0x008ade94 (null-terminated, contiguous):

```
pvehicle             chopperspecs       damagespecs       rigidbodyspecs
RBVehicle            RBTrailer          RBCop             EffectsVehicle
EffectsCar           EffectsFragment    DamageRacer       DamageHeli
DamageCopCar         SuspensionTraffic  SuspensionTrailer EngineRacer
EngineTraffic        SimpleChopper      DrawHeli          DrawTraffic
DrawNISCar           DrawCopCar         Draw              RaceCar
SoundTraffic         SoundCop           SoundRacer        SoundHeli
SpikeStrip
```

The list terminates at `SpikeStrip`; `NFS Most Wanted` plus language names follow as a separate localization table.

EAGL stores this tag list inline immediately after the vtable so the runtime reflection system can walk it without a separate string table.

### Concrete body classes

| Class | Role |
|---|---|
| `RBVehicle` | Standard car / racer (player + AI) |
| `RBTrailer` | Truck trailer (towed by RBVehicle) |
| `RBCop` | Police cruiser (uses cop-specific AI behaviors) |

### Captured live (2026-05-09 in-race attach)

| Vtable | Count | Label |
|---|---|---|
| `0x008ac0fc` | 4 | `vtbl_pvehicle_AICar` — AI cars / traffic / cops |
| `0x008ac0f4` | (alt MI view) | `vtbl_pvehicle_AICar_SecondaryView` — MSVC multiple-inheritance secondary |
| `0x008ac06c` | 2 | `vtbl_pvehicle_PlayerCar` — player vehicle |
| `0x008ab6a0` | (shared) | `vtbl_pvehicle_SubPhysicsObject` — body[+0x98] sub-physics object |

Both top-level classes share the same sub-physics-object vtable at `0x8ab6a0`. The actual integration call dispatches through this sub-object (see Section 9).

---

## 6. PVehicle's 28-key component dispatch

The pvehicle RTTI inventory at `0x008add1c` doubles as the **component-key wordlist** — every class identity AND every component slot the engine knows how to attach to a pvehicle. The complete 28-entry set:

| Group | Keys |
|---|---|
| **Class identity** | `pvehicle`, `RBVehicle`, `RBTrailer`, `RBCop`, `RaceCar` |
| **Spec records** | `chopperspecs`, `damagespecs`, `rigidbodyspecs` |
| **Effects (visual)** | `EffectsVehicle`, `EffectsCar`, `EffectsFragment` |
| **Damage submodels** | `DamageRacer`, `DamageHeli`, `DamageCopCar` |
| **Suspension** | `SuspensionTraffic`, `SuspensionTrailer` (see Section 7 for the full variant set) |
| **Engine** | `EngineRacer`, `EngineTraffic`, `SimpleChopper` |
| **Draw (render)** | `DrawHeli`, `DrawTraffic`, `DrawNISCar`, `DrawCopCar`, `Draw` |
| **Audio** | `SoundTraffic`, `SoundCop`, `SoundRacer`, `SoundHeli` |
| **Misc** | `SpikeStrip` |

These keys form the matrix the EAGL reflection system uses when attaching subcomponents at spawn time. Each pvehicle is built by reading the `BEHAVIORS` StringKey list (hash `0xDA5F19F9`) and instantiating the named component for each behavior mechanic (`BEHAVIOR_MECHANIC_SUSPENSION`, `BEHAVIOR_MECHANIC_ENGINE`, etc.).

### The 9 behavior-mechanic StringKeys

The schema includes a behavior-mechanic registry, exposed as StringKey attributes:

```
BEHAVIOR_MECHANIC_SUSPENSION
BEHAVIOR_MECHANIC_EFFECTS
BEHAVIOR_MECHANIC_RESET
BEHAVIOR_MECHANIC_DAMAGE
BEHAVIOR_MECHANIC_RIGIDBODY
BEHAVIOR_MECHANIC_ENGINE
BEHAVIOR_MECHANIC_DRAW
BEHAVIOR_MECHANIC_INPUT
BEHAVIOR_MECHANIC_AUDIO
```

Each is the "kind" of behavior; the chosen component-key (e.g. `SuspensionRacer`) is the "model" for that kind.

### Subsystem reference attributes (RefSpec)

The 17 RefSpec attribute names below define the complete vehicle data model — every car/cop/heli/trailer pulls these by reference:

```
engine           transmission    brakes          tires
nos              induction       chassis         rigidbodyspecs
engineaudio      damagespecs     chopperspecs    junkman
aivehicle        frontend        acceltrans      Trailer
EffectLinkageRecord                              emittergroup
```

Notes:

* `junkman` is the meta-tier system that stacks performance bonuses.
* `acceltrans` = acceleration transmission (gear ratios + power-band table).
* `aivehicle` holds AI-only data not present on player cars.
* `chopperspecs` references the helicopter pursuit unit.
* `frontend` is the FE preview record (lower-LOD draw spec).

---

## 7. Suspension variants

Six suspension variants exist. All are dispatched via the sub-physics object's `vt[2]` slot, which returns the vec3 wheel-compression vector for the body's four wheels.

| Variant | Used by | Notes |
|---|---|---|
| `SuspensionSimple` | Static / cheap traffic | Minimal compression model; flat spring constant |
| `SuspensionSpline` | Tuned racing cars | Spline-curve travel; per-wheel ride-height table |
| `SuspensionParams` | Generic data-driven | Reads STIFFNESS / damping / travel from attribute record |
| `SuspensionRacer` | Player + race-AI cars | Full active suspension; consumes `STIFFNESS` (hash `0x7F8EEA1A`) |
| `SuspensionTraffic` | Traffic vehicles | Cheap variant for ambient cars (`SuspensionTraffic` is also in the RTTI inventory) |
| `SuspensionTrailer` | RBTrailer | Trailer-specific (link-joint compensation, no power) |

The relevant Float attribute for suspension tuning is `STIFFNESS` (hash `0x7F8EEA1A`, type Float).

---

## 8. Vehicle attributes — handling knobs

Attributes are stored in `/extracted/app/GLOBAL/attributes.bin` (VPAK, 689,728 bytes). Each row is 16 bytes starting at file offset `0x18000`:

```
[+0x00] u32 attribute_name_hash   (Jenkins mix3, seed 0xABCDEF00)
[+0x04] u32 type_hash             (EA::Reflection::* / Attrib::*)
[+0x08] u16 ?
[+0x0a] u16 ?
[+0x0c] u16 ?
[+0x0e] u16 type_flags
```

Total rows: **345**. Verified cracked: **294 (85.2%)** as of 2026-05-14, post wave-7 community wordlist integration.

### Type hashes

| Hash | Type | Row count |
|---|---|---|
| `0x3C16EC5E` | `EA::Reflection::Float` | 137 |
| `0xA3F0C234` | `EA::Reflection::Text` | 39 |
| `0x939992BB` | `EA::Reflection::UInt32` | 38 |
| `0x064BEC37` | `EA::Reflection::Bool` | 71 |
| `0x2B936EB7` | `Attrib::RefSpec` | 38 |
| `0xA502A824` | `Attrib::StringKey` | 33 |
| `0xDB9D3A16` | `eDRIVE_BY_TYPE` | 5 |
| `0x349D3A16` | (uncracked) | — |
| `0x934A36EC` | (uncracked) | — |

### Handling-relevant attributes (with hashes and roles)

The handling-relevant Float attributes form a tightly-named cluster. The set below covers vehicle dynamics, camera, race rules, particles and damage — by far the most-useful tuning knobs:

| Hash | Name | Type | Role |
|---|---|---|---|
| `0x4A56503D` | `MASS` | Float | Vehicle mass (NOT what `RigidBody_ComputeMassInverseFromAttribute` reads — that reads DROPOUT) |
| `0x7F8EEA1A` | `STIFFNESS` | Float | Suspension stiffness (read by `SuspensionRacer` / `SuspensionParams`) |
| — | `STEERING` | Float | Steering rate (one of the 29 cracked Float attribs from earlier waves) |
| — | `Power` | Float | Engine power |
| — | `Life` | Float | Vehicle / object life |
| — | `Radius` | Float | Object radius |
| — | `FOV` | Float | Camera field of view |
| — | `Width` | Float | Camera/object width |
| — | `HEIGHT` | Float | Object height |
| — | `ANGLE` | Float | Camera/object angle |
| — | `Rotation` | Float | Rotation angle |
| — | `distance` | Float | Camera distance |
| — | `LAG` | Float | Camera lag |
| — | `Priority` | Float | Object/event priority |
| — | `AxlePair` | Float | Axle pair offset/separation |
| `0xB5C0DAC8` | `AUTO_SIMPLIFY` | Float | `Smackable::mAutoSimplify` (RB +0xfc) — LOD cull threshold |
| `0x44F1273B` | `DROPOUT` (2 floats) | Float | Timed-decay despawn animator (RB +0xf4 / countdown +0xf0) |
| `0x360552DA` | `ExplosionEffect` | Float | Push-back/snap-back collision response gate (`FUN_00677100`) |
| `0x0A91596D` | `InitialSpeed` | Float | Race start speed |
| `0x7C11C52E` | `RaceLength` | Float | Total race length |
| `0x7585F041` | `TimeLimit` | Float | Race time limit |
| `0x777ECE27` | `KnockoutTime` | Float | Knockout-mode timing |
| `0xF5A03629` | `MaxHeatLevel` | Float | Pursuit heat ceiling |
| `0x811C6606` | `TRAFFIC_SPEED` | Float | Ambient traffic speed |
| `0x3A5970F4` | `forceMultiplier` | Float | Damage/impact force multiplier |
| `0xA6F789CB` | `damageMultiplier` | Float | Damage multiplier |
| `0xBF2FDB5C` | `SpawnTime` | Float | Cop / object spawn timing |
| `0xDC943CC9` | `NumParticles` | Float | Particle emit count |
| `0xD8165518` | `NumParticlesVariance` | Float | Particle count randomization |
| `0xEFB4BB64` | `LifeVariance` | Float | Particle life randomization |
| `0xF7649E63` | `MaxSize` | Float | Particle max size |
| `0x0FA46807` | `MinScale` | Float | Particle minimum scale |
| `0x4C141ED7` | `HeightStart` | Float | Particle initial height |
| `0x6BBC13EE` | `LengthStart` | Float | Particle initial length |

### Handling-relevant non-Float attributes

| Hash | Name | Type | Role |
|---|---|---|---|
| `0xEE0011E3` | `SimplePhysics` | Bool | Smackable construction flag (ghost vs solid) |
| `0xDA5F19F9` | `BEHAVIORS` | StringKey | Child component list (iterated at `CreateRigidBodyComponent`) |
| `0x665F4D74` | `TILTING` | Bool | Tilt physics flag |
| `0x2B1F54F6` | `PursuitRace` | Bool | Is this race a pursuit-mode? |
| `0x6DF0ABFE` | `RandomOpponent` | Bool | Random AI opponent pick |
| `0x40E94F86` | `SELECTABLE` | Bool | UI-selectable flag |
| `0x3E9156CA` | `Template` | Bool | Is this row a template? |
| `0xB2AC32C7` | `FireOnExit` | Bool | Trigger on exit |
| `0xCE4261AC` | `OneShot` | Bool | One-shot trigger flag |
| — | `CatchUp` | Bool | Rubber-band on/off |
| — | `Directional` | Bool | — |
| — | `Tranny` | Bool | Transmission active? |
| — | `Persistent` | Bool | Persists across reset |
| — | `AutoStart` | Bool | Auto-start mode |
| — | `no_trigger` | Bool | Suppress trigger |
| `0xF833C06F` | `CarType` | Text | Vehicle type identifier |
| `0xC0EEB909` | `PlayerCarType` | Text | Player vehicle reference |
| `0xD686D61E` | `CopSpawnType` | Text | Cop spawn template reference |
| `0xAA27E71C` | `DefaultPresetRide` | Text | Default car preset reference |
| `0x6319B692` | `TrafficPattern` | Text | Reference to traffic pattern row |
| `0x9CA1C8F9` | `CollectionName` | Text | Collection name |
| `0x5AAB860F` | `EventSequencer` | StringKey | Event sequencer reference |
| `0xBF49A7D9` | `BankName` | StringKey | Audio bank reference |
| `0xABA86E60` | `emittergroup` | RefSpec | Particle emitter group reference |
| `0x9E8910EF` | `message_id` | UInt32 | Network/event message ID |

### The 5 originally-mystery hashes (all now cracked)

| Hash | Type (corrected) | Name | Role |
|---|---|---|---|
| `0xEE0011E3` | Bool | `SimplePhysics` | Read by `Smackable_Construct @ 0x6895a0`; gates ghost vs solid construction. |
| `0xB5C0DAC8` | Float | `AUTO_SIMPLIFY` | `Smackable::mAutoSimplify` — LOD/cull threshold at RB +0xfc. |
| `0xDA5F19F9` | StringKey | `BEHAVIORS` | Child-component list (iterated by `CreateRigidBodyComponent_PhysicsObjectInit`). |
| `0x360552DA` | Float | `ExplosionEffect` | Push-back / snap-back gate consumed by `FUN_00677100`. |
| `0x44F1273B` | Float (2-element) | `DROPOUT` | Timed continuous force config (RB +0xf0 timer / +0xf4 value). |

The `SimplePhysics` Bool and the `BEHAVIORS` StringKey are paired in instance row `@0x611B0` — the Bool gates "has child effects?", the StringKey provides "what effects?".

---

## 9. Live-debugger findings (2026-05-09 in-race attach)

The 2026-05-09 wave-9 in-race attach captured the runtime vehicle layout for the first time. Game was in active race, attached via `sudo gdb -p` (Wine's `ptrace_scope=1` requires sudo).

### 6 active vehicles in `active_vehicle_components_arr_a_head @ 0x913e74`

During the in-race capture, `DAT_00913e74` (the entry-array head walked by `ActiveComponents_TickAll`) had **6 entries**. All 6 share a common audio-class vtable at `0x00897740` (the audio class has embedded RTTI string `"Aud: EAX_HeliState"` at +0x10). Each audio entity's `this[+8]` points to the actual vehicle physics body on the heap.

### Two pvehicle body vtables observed

The 6 underlying vehicle bodies split into two classes:

| Vtable | Count | Class |
|---|---|---|
| `0x008ac0fc` | 4 | `vtbl_pvehicle_AICar` — AI cars / traffic / cops |
| `0x008ac0f4` | (alt MI) | `vtbl_pvehicle_AICar_SecondaryView` — multi-inheritance secondary |
| `0x008ac06c` | 2 | `vtbl_pvehicle_PlayerCar` — player vehicle |

These are confirmed pvehicle-family — they live in the same .rdata cluster as `vtbl_pvehicle_ComponentList @ 0x008adcc0` (which has the embedded `pvehicle` RTTI string at the inventory tail).

### Sub-physics object

All bodies share the same sub-physics object class — vtable at `0x008ab6a0` (`vtbl_pvehicle_SubPhysicsObject`). Found at `body[+0x98]`.

### Full integration call chain (state == 3 gameplay path)

```
ActiveComponents_TickAll(dt)                                  0x004ba940
  → for each entry in DAT_00913e74[0..count]  (6 entries during race):
      Vehicle_PullSimResultAndUnpackWheels(audio_entity, dt)  0x004b15e0
        → VehicleAgent_QuerySimResult_Virtual(audio_entity, &out)
            → audio_entity[+8]->vtable[1](audio_entity, &out)
                // Body vtable[1] = pvehicle_MatchTypeAndDispatch_vt1   0x6a4040
                //   id-match check; if match, dispatches to vt[10] for work
            → vt[10] = pvehicle_DispatchSubobjVt1AndVt4         0x694700
                // dispatches to body[+0x98] sub-physics object's vt[1]/vt[4]
                // sub-object vt[1]/vt[4] does the actual work
            → pvehicle_AggregatePhysicsState                    0x694160
                // LEAF state collector — reads from ~7 sub-objects, packs
                //   per-frame physics state into output buffer.
                // Sub-object reads:
                //   this[+0x60] middleware: vt[1]/vt[4]/vt[7]/vt[8]
                //   this[+0x64] suspension: vt[2] returns vec3 compression
                //   this[+0x68] state:      vt[1] returns int state code
                //   this[+0x70] track/lane: vt[+0x34] returns float param
                //   this[+0x6c] 4-wheel/tire array: slip + force
```

### Sample body layout (vehicle 0 at `0x01a511b0`)

```
+0x00  primary vtable    = 0x008ac0fc
+0x08  secondary vtable  = 0x008ac0f4   (MSVC MI)
+0x14  heap subobject    = 0x01a4f240
+0x60  audio back-ref    = 0x01a46310   (the audio entity wrapping this body)
+0x98  sub-physics ptr   = (vtable 0x008ab6a0)
+0x100..0x140 floats     = pos/vel vectors (-2881.929, -167.801, -3193.314, ...)
```

### Layer count

The actual physics integration is **5 levels deep** of virtual dispatch:

1. `ActiveComponents_TickAll` (loop)
2. `Vehicle_PullSimResultAndUnpackWheels` (per entity)
3. `VehicleAgent_QuerySimResult_Virtual` (vt-call)
4. `pvehicle_MatchTypeAndDispatch_vt1` (id-check + delegate)
5. `pvehicle_DispatchSubobjVt1AndVt4` (delegate to sub-physics)
6. Sub-physics-object `vt[1]/vt[4]` (the actual integrator at `body+0x98`) → `pvehicle_AggregatePhysicsState`

### Correction: the 23-slot PerPlayerSubsystemTick array is AUDIO + UI

The 23-slot array at `&DAT_00919624..0x91a034` (stride 0x70) dispatched from `FUN_0047c880` is **NOT vehicle physics**. It dispatches audio + UI entities. The earlier conjecture that this was the per-player vehicle integrator was wrong.

Confirmed audio + UI base classes (4 concrete classes sharing a common base, all in .rdata at 0x00894cc8..0x00894f70):

| Vtable | Class | Step (vt[2]) | Dtor (vt[1]) |
|---|---|---|---|
| `0x894cc8` | `vtbl_AudioEntity_TypeA` | `0x47d3c0` | `0x47aa00` |
| `0x894e48` | `vtbl_UIScreenAnimEntity` | `0x476690` | `0x47aee0` |
| `0x894e90` | `vtbl_SmoothAudioEntity_With_Promote` | `0x4769e0` | `0x47af00` |
| `0x894f70` | `vtbl_AudioEntity_TypeD` | `0x482ec0` | `0x47b290` |

These classes share vt[0] (`IsAliveStub`), vt[3] (`NoOpStub`), vt[14] (`PromoteAudioMemHandleToReady`), vt[15] (setter), vt[17] (`GetSubobjectPropPtr`).

### Wine ASLR / mapping

Wine maps `speed.exe` at its declared `IMAGE_BASE = 0x00400000` with **no relocation** (no ASLR on this PE). All Ghidra static addresses match runtime addresses 1:1 — no translation needed for breakpoints. Module load addresses of relevance:

```
speed.exe                @ 0x00400000  (IMAGE_BASE)
syswow64\d3d9.dll        @ 0x7B3F0000  (Wine emulated)
syswow64\d3dx9_26.dll    @ 0x78390000  (the SDK version this game ships against)
syswow64\DINPUT8.dll     @ 0x75D10000
app\DSOUND.dll           @ 0x76420000  (DSOAL → OpenAL wrapper)
```

ASI mods loaded in this Magipack repack: `NFSMostWanted.WidescreenFix.asi`, `NFSMWExtraOptions.asi`, `NFSMWHDReflections.asi`, `NFSMWHUDAdapter.asi`, `EZ Wheel Wrapper v4.60.001` (loaded via DSOUND/DInput). The EZ Wheel Wrapper appears to hot-patch audio class methods — it can cause vtable corruption (vt[2] slot overwritten to 0xffffffff at runtime when the static .rdata reads a valid function pointer), producing a paradoxical Wine crash at `0x47c8af` reading address `0xffffffff` with `EDX=0x894cc8`.

---

## 10. Modding vehicle physics

### Attribute writing pattern

Every gameplay tuning knob is reachable through the same path:

1. **Hash the name** with `BChunkHash_JenkinsMix3` (Jenkins mix3, seed `0xABCDEF00`). Example: `bChunk("MASS") = 0x4A56503D`.
2. **Search `attributes.bin`** for the hash as a little-endian u32 (search starts at file offset `0x18000`).
3. **Read the 16-byte row** containing it. The second u32 is the type hash; the type tells you how to interpret the value.
4. **Edit in place** for static tuning, OR hook the runtime lookup (`LookupAttributeByHash` is the central API) for dynamic overrides.

The complete cracked-name registry is `docs/attribute_hashes.md` (294/345 verified). For type-flag decoding, see `docs/attrib_table.json`.

### Per-vehicle RefSpec attribute targets

For physics tuning, target the per-vehicle RefSpec attributes — these reference subsystem records and let you swap-in alternate handling/engine/brake records without touching the per-vehicle attribute row:

```
acceltrans   chassis      tires        brakes
suspension   nos          induction    engine
```

Each can point at a different subsystem record per car/AI/cop type, giving very granular control. The `junkman` RefSpec is the meta-tier system that stacks performance bonuses across these.

### Direct RigidBody state injection

For state injection at runtime, write to the RigidBody at:

* `+0x10..+0x3F` — set transform (teleport).
* `+0x44` — set mass inverse (mass override).
* `+0x48..+0x7F` — set velocity, angular velocity, applied forces, applied torques.
* `+0xfc` — set AUTO_SIMPLIFY (LOD cull threshold).

Pool walk: enumerate `DAT_00925b30` (the universal RigidBody pool); each slot is 332 bytes. Filter by `+0x00` vtable to find pvehicle bodies vs trailer / cop / generic bodies.

### Hooking the integrator

To capture the actual integrator function pointer at runtime:

1. Run the game until in-race state 3 (state-machine gate at `World_GetCurrentState() == 3`).
2. Set a hardware breakpoint at the indirect call site inside `WorldPhysicsDispatch_MainThreadCoordinator @ 0x75aad0` (the `call dword ptr [eax+0x44]` instruction).
3. Single-step into the callee — its address is `(*DAT_009885c8)[+0x44]`'s resolved target.

Alternative hook points:

* `ActiveComponents_TickAll @ 0x004ba940` — fires once per frame per active vehicle (6 calls/frame in a typical race).
* `Vehicle_PullSimResultAndUnpackWheels @ 0x004b15e0` — per-vehicle state pull (good for read-only mods).
* `pvehicle_AggregatePhysicsState @ 0x694160` — leaf state collector (last point before state is packed for consumers).

### Spawn-time hook for new pvehicles

To intercept pvehicle creation:

1. Hook `RigidBody_FactoryFromAttributes_PhysicsPoolAlloc @ 0x6895a0` (sole allocator).
2. After return, the new body's `+0x00` vtable is set — check it for AI vs Player (`0x8ac0fc` vs `0x8ac06c`).
3. The `BEHAVIORS` StringKey list is iterated AFTER allocation by `CreateRigidBodyComponent_PhysicsObjectInit @ 0x688660` — hook here to intercept child-component attachment.

### Mod-time vehicle override pattern

The pattern community VLT-style editors use:

1. Identify the target attribute by canonical name.
2. Hash it (`bChunk(name)`).
3. Locate the row in `attributes.bin` at offset `0x18000 + (n * 16)`.
4. Find the value table the row indexes into (separate VPAK section; offsets vary by type).
5. Patch the value. Verify by re-reading at runtime.

For runtime monkey-patching without file edits, replace the `LookupAttributeByHash` callee with a stub that consults an override table first, then falls back to the original lookup.

---

## Appendix: function/address quick reference

| Address | Symbol | Role |
|---|---|---|
| `0x00663d30` | `GameFrameTick` | Top of per-frame loop |
| `0x0064a680` | `SubsystemDtAccumulator` | dt-distribution junction (state==3 gate) |
| `0x0075aad0` | `WorldPhysicsDispatch_MainThreadCoordinator` | Physics-world step driver |
| `0x004ba940` | `ActiveComponents_TickAll` | Per-vehicle tick loop |
| `0x004b15e0` | `Vehicle_PullSimResultAndUnpackWheels` | Per-vehicle state pull |
| `0x006a4040` | `pvehicle_MatchTypeAndDispatch_vt1` | Layer-4 dispatch |
| `0x00694700` | `pvehicle_DispatchSubobjVt1AndVt4` | Layer-5 sub-physics delegate |
| `0x00694160` | `pvehicle_AggregatePhysicsState` | Leaf state collector |
| `0x006fce10` | `PhysicsWorldCoordinator_ConstructAndInstallSingleton` | Coordinator constructor |
| `0x006895a0` | `RigidBody_FactoryFromAttributes_PhysicsPoolAlloc` | Body allocator (uses `SimplePhysics`) |
| `0x00688660` | `CreateRigidBodyComponent_PhysicsObjectInit` | Component creator (uses `BEHAVIORS`) |
| `0x006883e0` | `RigidBody_ConstructorAndEAGLPhysicsRegister` | Body constructor |
| `0x00669910` | `RigidBody_InitializeInnerStateTree` | Body inner-state init |
| `0x00669c00` | `RigidBody_ComputeMassInverseFromAttribute` | NAME SUSPECT — reads DROPOUT, not MASS |
| `0x006fc3a0` | (anon) | world_root_singleton allocator |
| `0x006f6cf0` | `WorldTickScaleSimulationDt` | dt scaler |
| `0x008b0e18` | `PTR_FUN_008b0e18` | PhysicsWorldCoordinator primary vtable |
| `0x008add1c` | (.rdata) | pvehicle inline RTTI inventory |
| `0x008adcc0` | `vtbl_pvehicle_ComponentList` | Component-list vtable (24 methods) |
| `0x008ac0fc` | `vtbl_pvehicle_AICar` | AI car body vtable |
| `0x008ac06c` | `vtbl_pvehicle_PlayerCar` | Player car body vtable |
| `0x008ab6a0` | `vtbl_pvehicle_SubPhysicsObject` | Sub-physics object vtable |
| `0x009885c8` | `DAT_009885c8` | PhysicsWorldCoordinator singleton |
| `0x00925b30` | `DAT_00925b30` | RigidBody pool head |
| `0x009b0bc8` | `DAT_009b0bc8` | Active vehicle update queue |
| `0x00913e74` | `active_vehicle_components_arr_a_head` | Vehicle entry-array (audio wrappers) |
| `0x00919624` | `&DAT_00919624` | 23-slot PerPlayerSubsystemTick array head (audio+UI, NOT vehicles) |
