---
name: EAGL physics middleware integrator
description: Physics runs in a worker thread; main-thread coordinator @ 0x75aad0 calls DAT_009885c8[+0x44] (physics world singleton vt[+0x44]) — that's the integrator step entry point.
type: project
originSessionId: c4edf485-e85f-4e2f-ac31-e021ba66e8d6
---
The actual rigid-body physics integrator runs in a **worker thread**, not the main game tick. This is why earlier breakpoint attempts on the main thread missed it.

## Per-frame chain

```
GameFrameTick_MainLoopUpdate @ 0x663d30
  → if IsWorldSimActive():
       WorldPhysicsDispatch_MainThreadCoordinator @ 0x75aad0
         → DAT_009885c8[+0x44]()    ← integrator step (vt[+0x44] of physics world)
         → FUN_00747950              (vehicle update queue)
         → FUN_007310b0              (world object physics)
         → FUN_00755340              (AI/traffic physics)
         → FUN_00755450              (collision/impact)
         → FUN_00755590              (post-step cleanup)
```

Main thread reads physics state via `pvehicle_AggregatePhysicsState_PerFrameStateReader @ 0x694160` — already-known leaf state collector. Aggregation reads from worker-thread-updated sub-objects:
- this[+0x60]: physics middleware object (vt[1]/vt[4]/vt[7]/vt[8])
- this[+0x64]: suspension system (vt[2] returns vec3 compression)
- this[+0x68]: state object (vt[1] returns int state code)
- this[+0x70]: track/lane object (vt[+0x34] returns float position parameter)
- this[+0x6c]: 4-wheel/tire array (slip + force data)

## RigidBody construction

Pipeline:
- `RigidBody_FactoryFromAttributes_PhysicsPoolAlloc @ 0x6895a0` — sole allocator. Allocates 332-byte RigidBody from pool `DAT_00925b30`. Validates attribute type (uses hash 0xEE0011E3 — one of our **5 mystery hashes!** likely `RigidBodyAttribute` or similar).
- `CreateRigidBodyComponent_PhysicsObjectInit @ 0x688660`
- `RigidBody_ConstructorAndEAGLPhysicsRegister @ 0x6883e0` — initializes 5 vtables (PTR_FUN_008aa5b0, ..._008aa5a8, _008aa518, _008aa4f8, _008aa4dc), registers with EAGL via `BChunkHash_JenkinsMix3("Physics")`
- `InitializePhysicsWorldWithHash @ 0x6ee9b0` → `PhysicsWorldDispatcher_HashResolution @ 0x6ed0f0`
- `RigidBody_InitializeInnerStateTree @ 0x669910`
- `RigidBody_ComputeMassInverseFromAttribute @ 0x669c00`

## RigidBody layout (332 bytes)

```
+0x00  vtable ptr (primary)
+0x04..+0x0F  flags/state
+0x10..+0x3F  4x4 transform matrix
+0x40  inertia tensor / ref
+0x44  mass inverse
+0x48..+0x7F  velocity, angular velocity, forces, torques
+0x80..+0xFF  per-wheel/suspension data
+0x100..+0x14B  additional state/caching
```

## Suspension variants
- SuspensionSimple — basic spring-damper
- SuspensionSpline — curve-interpolated stiffness/damping
- SuspensionParams — generic param wrapper
- SuspensionRacer — high-performance tuning
- SuspensionTraffic — softer (AI traffic)
- SuspensionTrailer — attached trailer

All invoked via sub-physics-object vt[2] returning vec3 compression.

## Globals
- `DAT_009885c8` — physics world singleton (vtable-bearing). vt[+0x44] = integrator step.
- `DAT_00925b30` — universal RigidBody pool (332-byte slots).
- `DAT_009b0bc8` — active vehicle update queue (doubly-linked).
- `DAT_008a92d4` — ghost/solid threshold (mass < threshold → ghost body).
- `_DAT_0089096c, _DAT_00890968` — float clamping bounds (min/max).
- `_DAT_008aac20, _DAT_008aabd8` — track parameter bounds.

**Why:** Knowing that physics runs in a worker thread (rather than the main tick) changes how we attach to it: live debugging needs a thread-aware breakpoint at `DAT_009885c8[+0x44]`, not the main-thread chain. Also, the connection between the 5 mystery attribute hashes and physics validation suggests one of them is **likely** the RigidBodyAttribute schema name.

**How to apply:**
- For physics tuning: target the per-vehicle `acceltrans/chassis/tires/brakes/suspension/nos/induction/engine` RefSpec attributes (already cracked).
- For state injection: write to the RigidBody at the wheel-data offsets and then signal worker-thread completion.
- For deeper RE: set a debugger breakpoint at the indirect call site of `DAT_009885c8[+0x44]` in `WorldPhysicsDispatch_MainThreadCoordinator @ 0x75aad0`, then step into.
