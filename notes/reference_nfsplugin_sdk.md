---
name: nfspluginsdk-by-berkayylmao-mw05-headers
description: Open-source plugin SDK with 181 hardcoded addresses (28 globals + 153 functions) for speed.exe; BSD-3 licensed; canonical type names + class hierarchies for the entire NFS Most Wanted RE.
metadata: 
  node_type: memory
  type: reference
  originSessionId: c4edf485-e85f-4e2f-ac31-e021ba66e8d6
---

The NFSPluginSDK by berkayylmao (BSD-3, github.com/berkayylmao/NFSPluginSDK) ships full C++ headers for NFS Most Wanted (2005). Cloned at `/tmp/NFSPluginSDK/` and mirrored into project at `docs/nfsplugin_sdk_mw05/`. Extracted address index at `docs/sdk_addrs.json` (1937 lines).

## What's in the SDK (Game.MW05)
- `Types.h` — root namespace `NFSPluginSDK::MW05` with all enums + forward declarations (CarSlotId, CarType, eFEGameModes, ePursuitStatus, eImpoundReasons, etc.)
- `Types/` — 178 individual struct/interface headers (RBVehicle, PVehicle, AIVehicle*, AICopManager, GRaceStatus, FECustomizationRecord, …) each with member layout + inline thunks to hardcoded addresses
- `Extensions.h` — PVehicleEx, GRaceStatusEx, etc. helper utilities
- `MW05.h` — 28 `MemoryFieldWrapper<T>` globals (DrawCars, TheGameFlowManager @ 0x925E90, IsInNIS @ 0x91606C, Tweak_GameSpeed @ 0x901B1C, TheOneCopManager @ 0x90D5F4, …)

## Applied to Ghidra (2026-05-14)
- 120 functions renamed (87 renamed in-place + 33 created from data — vtable thunks Ghidra hadn't disassembled)
- 16 globals labeled via `/set_global`
- Naming format: `ClassName_MethodName` (Ghidra validator allows underscores despite warnings)

## High-value SDK confirmations of prior RE
| SDK addr/name | Prior memory note |
|---|---|
| `TheGameFlowManager @ 0x925E90` (GameFlowState enum) | Render pipeline DAT_00925e90 game state |
| `TheOneCopManager @ 0x90D5F4` (AICopManager*) | Cop AI registry / pool |
| `IsInNIS @ 0x91606C` | Cutscene/Non-Interactive Sequence flag |
| `IsFadeScreenOn @ 0x91CAE4` | Loading screen fade |
| `Attrib::StringToKey @ 0x454640` | bChunk hash function (Jenkins mix3) |
| `Attrib::FindCollection @ 0x455FD0` | attributes.bin row lookup |
| `AIVehicle::SetGoal @ 0x422480` | (was PushAIGoalByHash — SDK's name is more accurate) |
| `GRaceStatus::Get @ 0x91e000` | g_pGRaceStatus singleton |

## How to apply this
- When writing a mod DLL: include the SDK headers from `docs/nfsplugin_sdk_mw05/` — pre-typed structs save ~80% of dev time vs deriving from Ghidra
- When naming a function in Ghidra: grep `docs/sdk_addrs.json` for the address first — SDK names beat our heuristics
- The SDK has only ~150 functions out of ~26k — most of the binary is still un-named. SDK covers the public modding surface (vehicles, AI, race state, FE) which is exactly the gameplay layer we're focused on.

**Why:** Three days into solo RE we're at ~200 names; the SDK adds 150 with full type signatures + class hierarchies in a single pull. The SDK author (berkayylmao) has run an active NFS modding community since 2018; treat their addresses as ground-truth for the addresses they list.

**How to apply:** First action on any new function: grep `docs/sdk_addrs.json` — if SDK has it, use that name. The SDK doesn't cover render/audio internals, the script VM, or the EAGL4Anim engine, so RE work still needed there.
