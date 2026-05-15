---
name: fng-event-bus-full-chain-producer-drainer-handler
description: "Complete end-to-end FNG event-bus dispatch chain mapped. Closes wave-16's open question \"the per-frame queue drainer at this+0x411c\". Drainer = FUN_005c1460 → DrainUIDeferredEventQueue_PerFrame; per-frame caller = FE_PerFrameTick_DrainQueueAndUpdateChildren @ 0x5c53c0."
metadata: 
  node_type: memory
  type: project
  originSessionId: c4edf485-e85f-4e2f-ac31-e021ba66e8d6
---

The complete FNG event-bus dispatch chain — all functions identified and renamed.

## End-to-end flow

```
[gameplay/system code]
   ↓
PostUIEventToNamedNode @ 0x516c90
   ↓
DispatchUIEventToNamedNode @ 0x516be0
   ├─ if name==NULL → fan out via subscriber list at (*this+0xe0)
   └─ if name!=NULL → FindSceneNodeByName(name) → 
                       ScheduleUIDeferredEvent @ 0x5b7780
                          → if (this+0x524e):
                              synchronous dispatch via (*this+0x108+0x54)()
                          → enqueue 0x20-byte event into doubly-linked list:
                              this+0x4118 = head, this+0x411c = tail,
                              this+0x4114 = count
                              vtable PTR_FUN_008a2c90, fence 0xABADCAFE×2

[per-frame tick — main loop]
   ↓
FE_PerFrameTick_DrainQueueAndUpdateChildren @ 0x5c53c0
   ├─ if (this+0x524e): dispatch sync queue first via (*this+0x108+0x5c)()
   ├─ iterate this+0xd0 child handlers, call FUN_005ae960 per slot
   ├─ iterate this+0xe0 subscriber list (full per-handler tick)
   └─ DrainUIDeferredEventQueue_PerFrame @ 0x5c1460
        For each event in queue (this+0x4118 → ... → null):
          UnlinkSceneNodeChild(this+0x4110, event)
          Read event[4] = target marker:
            0xfffffffc → broadcast to all subscribers (this+0xe0)
            0xfffffffa → alt-broadcast
            NULL       → type-registry broadcast
            ptr        → direct call into target node's handler
          Dispatch via:
            DispatchUIEvent_ToSubscriberHandler @ 0x5bbc00 (direct)
            DispatchUIEvent_ToTypeRegistrySubscribers @ 0x5beaa0 (type-registry)
```

## Renames applied (wave-17)

| Address | New name | Role |
|---|---|---|
| `0x005c1460` | `DrainUIDeferredEventQueue_PerFrame` | Per-frame queue drainer |
| `0x005c12f0` | `ConstructUIDeferredQueueOwner` | Ctor — initializes queue head/tail to 0 |
| `0x005bbc00` | `DispatchUIEvent_ToSubscriberHandler` | Direct subscriber dispatch |
| `0x005beaa0` | `DispatchUIEvent_ToTypeRegistrySubscribers` | Type-registry-based dispatch |
| `0x005c53c0` | `FE_PerFrameTick_DrainQueueAndUpdateChildren` | Main FE tick that calls the drainer |
| `0x005c20a0` | `FE_AlternateUpdate_DrainQueue` | Alt-tick caller (mode-specific?) |

## Queue object layout (FE/UI context, ScheduleUIDeferredEvent's `this`)

| Offset | Field | Notes |
|---|---|---|
| `+0x0e0` | Subscriber list head | Linked list of registered handlers |
| `+0x0d0` | Child handler count | Number of slots in handler array |
| `+0x108` | Sync-dispatch vtable | `*+0x54` = sync schedule, `*+0x5c` = sync drain, `*+0x40` = handler list, `*+0x44` = handler init |
| `+0x4110` | Queue node vtable (UnlinkSceneNodeChild root) | `PTR_LAB_008a2c18` |
| **+0x4114** | **Event count** | Incremented on Schedule |
| **+0x4118** | **Queue head ptr** | First event to drain |
| **+0x411c** | **Queue tail ptr** | Last event |
| `+0x524e` | Sync-dispatch enable flag | If set: events dispatched immediately AND queued |

## Event object layout (0x20 bytes)

| Offset | Field |
|---|---|
| +0x00 | vtable = `PTR_FUN_008a2c90` |
| +0x04 | prev ptr in queue (debug fence: 0xABADCAFE initial) |
| +0x08 | next ptr in queue (debug fence: 0xABADCAFE initial) |
| +0x0c | param_2 (caller payload) |
| +0x10 | event hash |
| +0x14 | event command/value (param_1 in Post) |
| +0x18 | target node ptr (or sentinel: 0xfffffffc/0xfffffffa/NULL) |
| +0x1c | priority |

## How the 14 non-walker widgets get their Update

For widgets like Speedometer:
1. Ctor calls `InsertOrAssignTypeRegistry(controller, &LAB_00565120, &widget_data)` — registers the widget under a TYPE tag.
2. Gameplay code (e.g. vehicle physics) calls `PostUIEventToNamedNode(ui_root, event_hash, "SPEED_DIGIT_1", ...)` when speed changes.
3. The event is queued at `ui_root+0x4118`.
4. On the next FE tick, `FE_PerFrameTick_DrainQueueAndUpdateChildren @ 0x5c53c0` calls the drainer.
5. The drainer finds the target node ("SPEED_DIGIT_1") and calls `DispatchUIEvent_ToTypeRegistrySubscribers` → looks up the Speedometer's registered handler via the type-registry → invokes Speedometer's Update with the new speed value.

So non-walker widgets are **event-driven, not tick-driven** — they only Update when something changes (push model), not every frame (pull model). This is more efficient than the walker for sparse-update widgets.

The 10 walker-ticked widgets (TurboMeter, etc.) DO update every frame because they have animations or counters that need to advance constantly.

## Modding implications

| Goal | Hook point |
|---|---|
| Intercept ALL FNG events being posted | Hook `PostUIEventToNamedNode @ 0x516c90` |
| Block events for a specific node | Hook `DispatchUIEventToNamedNode @ 0x516be0`, filter by node-hash |
| Block one event hash globally | Hook `ScheduleUIDeferredEvent @ 0x5b7780`, filter by event hash |
| Drain the queue manually (force flush) | Call `DrainUIDeferredEventQueue_PerFrame @ 0x5c1460` |
| Inject a fake event into the queue | Construct a 0x20-byte event (vtable=0x8a2c90, fence=0xabadcafe) and link into the doubly-linked list at +0x4118 |

## Significance

Closes the LAST major FNG-bus open question. The full chain from "gameplay state change" to "widget redraw" is now mapped end-to-end. Combined with wave-14's slot map and wave-13's walker discovery, the HUD subsystem is now fully reverse-engineered.

## Outstanding (low priority now)

- Type-registry slot layout (the 7 type-registry functions need internal field mapping)
- Sub-dispatchers `DispatchUIEvent_ToSubscriberHandler` and `..._ToTypeRegistrySubscribers` — full decomp of the call path into widget handlers
- The 13 unnamed AIVehicle base-class vtable slots (wave-16 partial)
