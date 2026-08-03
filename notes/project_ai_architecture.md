---
name: NFSMW AI architecture (Goals + Actions + behavior params)
description: Class hierarchy, vtable layout, registry-based dispatch, and key entry points for the AI system
type: project
originSessionId: c4edf485-e85f-4e2f-ac31-e021ba66e8d6
---
NFSMW's AI is a two-layer system: **AIGoals** are persistent strategic states (Pursuit, Patrol, Race, Pit, Heli, etc.); **AIActions** are short-lived tactical behaviors (Ram, RoadBlock, Race, Traffic) selected by goals. Both are registry-keyed by name hash via `BChunkHash_JenkinsMix3`.

## AIGoals — strategic state

**Confirmed strings** (from `list_strings` and decomp):
```
AIGoalNone           AIGoalPursuit       AIGoalPatrol         AIGoalRacer
AIGoalTraffic        AIGoalRam           AIGoalPit            AIGoalStopShort
AIGoalStaticRoadBlock AIGoalHeadOnRam   AIGoalHeliPursuit    AIGoalHeliExit
AIGoalHeliRoadBlock
```

**Vtables identified:**
- `vtbl_AIGoalRacer @ 0x00892720` (primary)  +  `vtbl_AIGoalRacer_RTTI @ 0x00892718` (type tag)
- `vtbl_AIGoalPit   @ 0x00892f70`
- `AIGoalNone` and `AIGoalRacer` use a sub-component pattern: install `PTR_FUN_00890970` (base sub-component vtable) at `this+0x73C` (None) or `this+0x7C4` (Racer), register it via `InsertOrAssignTypeRegistry(handle, &type_id_thunk, this+offset)`, then override the vtable with a class-specific sub-vtable (e.g., `PTR_FUN_00890b90` / `PTR_FUN_00890af0`).

**Ctor entry points** (already named):
- `CreateAIGoalNone`, `CreateAIGoalRacerInstance`, `CreateAIGoalRam`, `CreateAIGoalPit`
- `PushAIGoalByHash` is the dispatcher: maps a name hash → the corresponding ctor.

## AIActions — tactical behaviors

**Confirmed strings (used as registry keys):**
```
AIActionRam              AIActionPursuitOffRoad   AIActionRace
AIActionTooDamaged       AIActionGetUnstuck       AIActionAirborne
AIActionTraffic          AIActionStaticRoadBlock
```

**Vtables identified:**
- `vtbl_AIAction_base          @ 0x00892b20`  (initial vtable installed before the class-specific override)
- `vtbl_AIActionRam            @ 0x00892c88`  (overrides _base after construction)
- `vtbl_AIActionStaticRoadBlock @ 0x00892b40`
- `vtbl_AIActionRace            @ 0x00892b30`

**Vtable layout** (4-slot method groups; an AIAction may have 1–4 groups):
```
+0x00  scalar deleting destructor (varies per class — class identity)
+0x04  ProcessAIDecisionEvaluation (0x42b070, COMMON across all AIActions)
+0x08  ?? at 0x40a6d0 (orphan code, not yet a function — COMMON)
+0x0C  AIAction_BroadcastToChildren (0x42b040, COMMON)
+0x10  next group: another deleting-dtor + the same trio
+0x20  next group: another deleting-dtor + the same trio
+0x30  next group: another deleting-dtor + the same trio
... + inline RTTI string (e.g. "AIActionRam") at the end
```

**Class size from scalar-deleting-dtor argument** (acts as a class fingerprint):
- AIActionRam: `0x18` (24 bytes)
- AIAction_base / variant: `0x1C` and `0x18` (multiple sub-classes)
- one variant at: `0x20` (32 bytes)
- DestroyAIVehicleAndMaybeFree (vehicle host): `0x7EC` (~2 KB — this is the FULL AI vehicle structure)

## Common machinery (shared across the hierarchy)

- `LookupAIBehaviorParam(this, "AIActionXxx")` — fetches behavior parameters from a registry; called repeatedly in every `Create*` ctor.
- `ProcessAIDecisionEvaluation(this, …)` — vt[1] of every AIAction's method-group; evaluates whether the action should fire this frame.
- `AIAction_BroadcastToChildren(this, dt)` — vt[3] of every AIAction's method-group; iterates children at this+0xC and calls vt[4] of each.
- `DispatchAIActionByHash` — dispatches an action by its name hash (the bChunk of e.g. "AIActionRam").

## Registry and lifecycle

- `RegisterAIActionInRegistry` — registers an action class at startup (probably from CRT init).
- `InsertOrAssignTypeRegistry(world_handle, &type_id_thunk, sub_component)` — wires a sub-component into the world's reflection registry.
- `CreateAIVehicleInstance` — instantiates the AI vehicle entity that holds the goal + active actions.
- `DestroyAIVehicleAndMaybeFree` (size 0x7EC) — scalar-deleting-dtor for the AI vehicle wrapper.

## Why this matters

The AI is **fully data-driven by the bChunk(name) registry**: changing a goal's behavior is a matter of replacing its registered behavior parameters (lookup by `AIActionRam`-style key). Modders can hook into the action layer by registering a new tag (e.g. `AIActionTurboRam`) and pushing it via `PushAIGoalByHash`.

## How to apply

- For "what AI runs when X happens": look at the bChunk hash being passed to `LookupAIBehaviorParam` or `DispatchAIActionByHash`; if the hash is known (e.g. via the registry), the answer is the ctor at the matching address.
- For new vtable identification: find the `*this = &PTR_FUN_xxx` line in any `Create*` ctor; that's the vtable.
- For finding action methods: vt[0] is always a deleting destructor (boring); the *real* methods are inside what `ProcessAIDecisionEvaluation` calls — those are the eval/score/decide paths.
