---
name: ai-vehicle-vtables-traffic-helicopter-shared-base
description: Full slot maps for vtbl_AIVehicleTraffic @ 0x891CF8 (24 slots) and vtbl_AIVehicleHelicopter @ 0x8920D8 (30 slots). 14 shared base-class slots + per-class diverging slots.
metadata: 
  node_type: memory
  type: project
  originSessionId: c4edf485-e85f-4e2f-ac31-e021ba66e8d6
---

Both AI vehicle vtables read directly from binary. Slots 0-14 are mostly shared with the AIVehicle base class; slot 0 (dtor) and slot 10 (per-class Update/OnDriving) diverge; helicopter has 6 additional slots past traffic.

## vtbl_AIVehicleTraffic @ 0x00891CF8 (24 slots)

| Slot | Address | Renamed |
|---|---|---|
| vt[0] | `0x00433680` | `DestructAIVehicleTraffic` (per-class dtor) |
| vt[1] | `0x00406600` | `AIVehicle_BaseUpdate_vt1` (shared base) |
| vt[2] | `0x00405390` | (traffic-specific, unnamed) |
| vt[3] | `0x00431ea0` | (shared base, unnamed) |
| vt[4] | `0x00414f70` | (shared base, unnamed) |
| vt[5] | `0x00408370` | (shared base, unnamed) |
| vt[6] | `0x004081e0` | (shared base, unnamed) |
| vt[7] | `0x00414fc0` | (shared base, unnamed) |
| vt[8] | `0x00410540` | (shared base, unnamed) |
| vt[9] | `0x00410550` | (shared base, unnamed) |
| **vt[10]** | **`0x0042ab40`** | **`UpdateAIVehicleTraffic_OnDriving`** (per-frame Update for traffic) |
| vt[11] | `0x00408a10` | (shared base) |
| vt[12] | `0x00408d70` | (shared base) |
| vt[13] | `0x00408220` | (shared base) |
| vt[14] | `0x00415140` | (shared base) |
| vt[15] | `0x00415290` | (traffic-specific) |
| vt[16] | `0x00408430` | (shared base) |
| vt[17] | `0x00408690` | (shared base) |
| vt[18] | `0x00414ce0` | (shared base) |
| vt[19] | `0x00431eb0` | (shared base) |
| vt[20] | `0x00432490` | (traffic-specific) |
| vt[21] | `0x00423320` | (traffic-specific) |
| vt[22] | `0x00423430` | (traffic-specific) |
| vt[23] | `0x00423370` | `SetAITrafficGoal` (already named) |

## vtbl_AIVehicleHelicopter @ 0x008920D8 (30 slots)

| Slot | Address | Renamed |
|---|---|---|
| vt[0] | `0x004336e0` | `DestructAIVehicleHelicopter` (per-class dtor) |
| vt[1] | `0x00406600` | `AIVehicle_BaseUpdate_vt1` (shared base — same as traffic) |
| vt[2] | `0x004097a0` | (heli-specific, unnamed) |
| vt[3..9] | (shared base, same addresses as traffic) | — |
| **vt[10]** | **`0x0042adb0`** | **`UpdateAIVehicleHelicopter_OnDriving(this, dt)`** — takes `(this, float dt)`, per-frame driving update. Reads mDestinationVelocity, mLookAtPosition, mHeight; commands ISimpleChopper::SetDesiredVelocity. |
| vt[11..14] | (shared base) | — |
| vt[15] | `0x0042a390` | (heli-specific, unnamed — likely SetDestinationVelocity per SDK) |
| vt[16] | `0x0042a0b0` | (heli-specific) |
| **vt[17]** | **`0x00417a20`** | **`FilterHeliAltitudeVector(this, V3&)`** — clamps seek-point Y to mHeight bounds (per SDK Types/AIVehicleHelicopter.h) |
| vt[18] | `0x00416af0` | (heli-specific) |
| vt[19] | `0x00431eb0` | (shared base) |
| vt[20] | `0x00416b90` | (heli-specific) |
| vt[21] | `0x004325b0` | (heli-specific) |
| vt[22] | `0x00432aa0` | (heli-specific) |
| vt[23] | `0x00419da0` | (heli-specific) |
| vt[24] | `0x0043dc10` | (heli-specific) |
| vt[25] | `0x0040b060` | (heli-specific) |
| vt[26] | `0x00432ab0` | (heli-specific) |
| vt[27] | `0x00419de0` | (heli-specific) |
| vt[28] | `0x00432920` | (heli-specific) |
| vt[29] | `0x00432960` | (heli-specific) |

## Shared-base slots (AIVehicle parent)

Slots 1, 3-9, 11-14, 16-19 in both vtables share addresses with what looks like the AIVehicle base class. By SDK convention:

- vt[1] = `Update(dt)` (`AIVehicle_BaseUpdate_vt1 @ 0x406600`)
- vt[3-4] = `Set/GetTarget` (TBD)
- vt[5-6] = `Set/GetDriver` (TBD)
- vt[7-9] = goal-stack methods
- vt[10] = `OnDriving(dt)` (per-class virtual — what we renamed)
- vt[11+] = AI-state queries

Per the NFSPluginSDK `IAIHelicopter` interface, the helicopter adds 13-15 helicopter-specific virtuals starting around vt[15]: GetHeliSheetCoord, Get/SetDesiredHeightOverDest, Set/GetLookAtPosition, SetDestinationVelocity, SteerToNav, StartPathToPoint, Set/StrafeToDest, FilterHeliAltitude (vt[17] verified), RestrictPointToRoadNet, Set/GetFuelTime, Set/GetShadowScale, Set/GetDustStormIntensity.

## How to apply

For mod work:
- **Hook UpdateAIVehicleHelicopter_OnDriving @ 0x42adb0** to change per-frame heli behavior
- **Hook UpdateAIVehicleTraffic_OnDriving @ 0x42ab40** for traffic AI changes
- **Override vt[17] FilterHeliAltitudeVector** to change altitude clamping
- **Replace vt[0] dtors** to inject custom destruction logic (memory leak hook etc.)

For analysis:
- Slots not yet decompiled (vt[2..9, 11..16, 18..29] for helicopter) are the next deep-dive targets
- Cross-reference against SDK Extensions.h / IAIHelicopter.h for the canonical name of each slot

## Outstanding

- Decompile remaining unnamed slots (most are short — could batch-rename in one pass)
- Identify the AIVehicle base vtable (these shared slots come from somewhere)
- Confirm SDK slot-to-name mapping against actual binary behavior
