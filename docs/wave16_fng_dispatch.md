---
name: fng-event-bus-dispatch-chain-ui-deferred-event-system
description: "How FNG nodes get update calls — PostUIEventToNamedNode → DispatchUIEventToNamedNode → FindSceneNodeByName → ScheduleUIDeferredEvent → per-frame queue at this+0x411c. Answers wave-14's open question about how the 14 non-walker HUD widgets get updated."
metadata: 
  node_type: memory
  type: project
  originSessionId: c4edf485-e85f-4e2f-ac31-e021ba66e8d6
---

The 14 HUD widgets that are NOT walker-ticked (Speedometer, Tachometer, etc.) update via this FNG event bus — a **deferred event queue** anchored on the FE/UI root context.

## Producer side

```
caller (gameplay code)
   ↓
PostUIEventToNamedNode @ 0x516c90
  (this, event_hash, node_name, priority)
   ↓ delegates to:
DispatchUIEventToNamedNode @ 0x516be0
   ├─ if node_name == NULL:     iterate linked list at (*this + 0xe0) and
   │                              ScheduleUIDeferredEvent for each subscriber
   └─ if node_name != NULL:     FindSceneNodeByName(this, node_name)
                                  → ScheduleUIDeferredEvent(event)
```

## Scheduler

`ScheduleUIDeferredEvent @ 0x5b7780` allocates a 32-byte event from `_malloc` and appends to a per-context queue at `this+0x411c`:

```c
event struct (0x20 bytes, vtable PTR_FUN_008a2c90):
  +0x00  vtable
  +0x04  key1     = 0xabadcafe  (debug fence)
  +0x08  key2     = 0xabadcafe  (debug fence)
  +0x0c  param_2  = caller payload
  +0x10  hash     = event hash (e.g. 0x53ec068c)
  +0x14  param_1  = event command/value
  +0x18  param_4  = node target
  +0x1c  param_5  = priority
```

If `this+0x524e` is set, the event is ALSO synchronously dispatched via `(*this+0x108 + 0x54)()` before being queued. This is a "snap-to" hook for events that can't wait for the next frame.

## Per-frame dispatch (TBD location)

The deferred queue at `this+0x411c` is drained each frame by the FE tick (TBD which function). Each pulled event:
1. Reads the target node ptr (param_4)
2. Calls the node's registered handler with (event_hash, payload)

The handler is the widget's `vt[1]` for walker-ticked widgets — but for non-walker widgets like Speedometer, the handler is registered via `InsertOrAssignTypeRegistry(param_1, &LAB_00565120, ...)` during ctor.

`LAB_00565120` is a small mov+ret stub (returns the widget's data ptr) — likely the type-registry's "get my data" thunk. The full type-registry mechanism uses 7 functions:

| Address | Function |
|---|---|
| `0x401f40` | `RemoveSelfFromTypeRegistry` |
| `0x5d5a50` | `EraseTypeRegistryEntry` |
| `0x5d7830` | `PushBackTypeRegistryEntry` |
| `0x5d7930` | `InsertOrAssignTypeRegistry` |
| `0x672e80` | `GetTypeRegistryClassByName` |
| `0x6ee930` | `ConstructTypeRegistryEntry` |
| `0x6eeb60` | `ReleaseTypeRegistryReference` |

The type-registry is a per-widget "data binding" system: each widget registers its data accessor → FNG events look up the data via the registry and invoke the widget's handler.

## Caller inventory (15+ producer sites)

Top callers of `PostUIEventToNamedNode @ 0x516c90`:

| Caller | Address | Likely role |
|---|---|---|
| `ProcessUIDialogDismissed` | `0x56c737` | Dialog box close → notify listeners |
| `ConstructUIBindingDescriptor` | `0x586324` | New widget binding registration |
| `CHudWidgetArray_FlipVisibilityOnGameMasterChange` | `0x5696c0` | HUD on/off (wave-13) |
| `CHudWidgetArray_SetActive` (wave-13) | `0x569570` | ACTIVATE/DEACTIVATE events |
| 11+ more in 0x5b0xxx / 0x573xxx / 0x587xxx / 0x562xxx / 0x56axxx ranges | various | Per-screen state-change notifiers |

## Why this matters for modding

For walker-ticked widgets (TurboMeter, RaceOverMessage, Countdown, etc.): hook the widget's vt[1] Update directly.

For non-walker widgets (Speedometer, Tachometer, etc.): two options:
1. **Hook PostUIEventToNamedNode** for the specific event hash → intercept all events targeting that node
2. **Override the widget's type-registry entry** at `InsertOrAssignTypeRegistry` callsite to redirect the data accessor

## How to find a specific widget's event hash

Each widget's ctor calls `FEObject_GetObject(asset, hashOfNodeName)` to grab handles to its FNG sub-nodes. These node-hashes are also the **event-targets** in PostUIEventToNamedNode. So a widget Update fires whenever an event is posted with one of its registered node hashes.

Example: Speedometer reads `SPEED_DIGIT_1` (hash) — when gameplay code posts an event to that node hash, the Speedometer's handler runs.

## Outstanding

- The per-frame queue drainer at `this+0x411c` — find the function that walks this list each frame
- The handler-resolution chain — given an event hash and a target node, how does the FE find which C++ handler to call? (likely via the type-registry)
- Cross-reference InsertOrAssignTypeRegistry callers to enumerate all widget→type-tag bindings
