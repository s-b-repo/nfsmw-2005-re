---
name: NFSMW input subsystem (DirectInput8 + action cards)
description: DInput8 boot path, FF wheel/joystick enumeration, device-registry hash dispatch, and the CDAction card layer
type: project
originSessionId: c4edf485-e85f-4e2f-ac31-e021ba66e8d6
---
The input subsystem is built on **DirectInput8** plus a hash-keyed device registry and a high-level "Card Driving Action" abstraction (CDAction*) sitting on top of raw inputs.

**Boot path (called from `InitializeEngine`):**
```
Input_Initialize_DInput8                      0x006e2640
  ├─ Input_ZeroStateBlocks(state_block)       0x006c9d70
  ├─ DirectInput8Create(hModule, 0x800, IID_IDirectInput8, &dinput8_device_root_ptr, NULL)
  │       — IID at iid_idirectinput8_guid @ 0x008c065c (BF798030-...)
  │       — DInput8 ptr stored at dinput8_device_root_ptr @ 0x00982d14
  └─ Input_EnumerateFFDevicesAndAxes(state_block)   0x006dc590
        ├─ vt[0x10] EnumDevices  → finds force-feedback wheels/joysticks/gamepads
        │     callback: Input_EnumerateFFDeviceCallback @ 0x006d8100
        │       ├─ vt[0xC] CreateDevice → IDirectInputDevice8 ptr
        │       ├─ classify by DIDEVICEINSTANCE.dwDevType (param+0x24):
        │       │     0x14 DI8DEVTYPE_DRIVING    → ff_devtype_driving_slot[N] = 1
        │       │     0x15 DI8DEVTYPE_FLIGHT     → ff_devtype_flight_slot[N]  = 1
        │       │     0x16 DI8DEVTYPE_1STPERSON  → ff_devtype_1stperson_slot[N] = 1
        │       └─ vt[0x18] SetProperty(DIPROP_AUTOCENTER=9, OFF) — disable wheel autocenter
        └─ for each FF device, vt[0x10] EnumObjects → axis enumeration

Input_Initialize_DInput8_AtSubOffset           0x006e2690
  // sibling: same body but operates on parent_struct + 0x2228 (a sub-init).
```

**Per-frame:** `Win32_PumpMessagesAndSynthesizeInput @ 0x006c21a0` is called from `FrameTail_PumpInputAndFlushJobs @ 0x006df8e0` once per frame. It calls `PeekMessageA` and synthesizes mouse INPUT events — but the actual `IDirectInputDevice8::GetDeviceState` polling site is not yet pinned to a specific function.

**Device registry (hash-keyed dispatch):**
```
Input_RegisterDeviceByNameHash                0x0063cbf0
  // Hashes a device name with BChunkHash_JenkinsMix3 (e.g. "GameDevice",
  // "MouseDevice", "KeyboardDevice") and walks the registry chain at
  // input_device_registry_head @ 0x00920464 (linked list, 12-byte nodes,
  // {hash, factory_fn, next}). On match, calls factory_fn(0) to obtain
  // the device handler.
```

**Globals:**
- `dinput8_device_root_ptr      @ 0x00982d14`  — IDirectInput8*
- `iid_idirectinput8_guid       @ 0x008c065c`  — 16-byte IID
- `input_device_registry_head   @ 0x00920464`  — head of {hash, factory_fn, next} list
- `ff_device_array_slot[0..1]   @ 0x0093df00 / 0x0093df04`  — IDirectInputDevice8* per FF slot
- `ff_devtype_driving_slot[0..1]    @ 0x00982904 / 0x00982908`
- `ff_devtype_flight_slot[0..1]     @ 0x0093d904 / 0x0093d908`
- `ff_devtype_1stperson_slot[0..1]  @ 0x0093cc58 / 0x0093cc5c`

**Action-card layer (above raw input):**
```
Player_SelectActiveActionCard       0x00479900
  // Hashes "CDActionDrive" / "CDActionTrackCop" / "CDActionTrackCar" / "CDActionIce"
  // by current game state. Stores at:
  //   entity[+0x10]  = bChunk64(name)
  //   entity[+0x18]  = djb24(name)
  //   entity[+0x1c]  = raw name string ptr
PerPlayerEntity_TickActionCard      0x00479de0  (already named, prior session)
  // Per-frame tick: decrements timers (entity+0x2b8, +0x2b4); dispatches
  // vt[6] of the active action-card object (entity+0x20) with arg state at
  // entity+0x2c0; falls through to vt[1] for the action-card update.
```

**Identified CDAction strings (from prior dumps, addresses are speed.exe):**
`CDActionDrive`, `CDActionShowcase`, `CDActionIce`, `CDActionTrackCar`, `CDActionTrackCop`, `CDActionDebug`, `CDActionDebugWatchCar`, etc.

**Why:** Knowing this layout lets you add custom inputs (e.g. modder hot-keys) by registering with the device registry, or trace what triggers a specific in-game action via the CDAction* hash.

**How to apply:**
- For per-frame raw input: trace callers of `dinput8_device_root_ptr` plus the unknown caller of `vt[0x24]` GetDeviceState — these are the polls.
- For action mapping: look at `Player_SelectActiveActionCard` to see when each CDAction* is selected.
- For force feedback: the per-device pointer at `ff_device_array_slot[N]` is where you'd issue `IDirectInputEffect` calls.
