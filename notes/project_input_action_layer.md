---
name: input-action layer (CDAction)
description: 200-slot binding registry maps DInput8 device codes → game-action enum (GAS/BRAKE/STEERLEFT/NOS/etc); per-frame poll lives in SimTickStepWithJoylogHook chain.
type: project
originSessionId: c4edf485-e85f-4e2f-ac31-e021ba66e8d6
---
NFSMW input flow: **DInput8 raw poll → 200-slot binding registry → game-action enum → vehicle controller**.

## Boot
- `Input_Initialize_DInput8 @ 0x6e2640` — DInput8 bootstrap; calls Input_EnumerateFFDevicesAndAxes
- `Input_EnumerateFFDevicesAndAxes @ 0x6dc590` — enumerates FF axes for 2 device slots (driving + 1stperson + flight)
- `Input_SetFFDeviceDataFormatAndCoopLevel @ 0x6d81f0` — DIDATAFORMAT_JOYSTICK + coop flags
- `Input_AcquireFFDevicesForEntity @ 0x6dc790` — device acquire @ entity offset 0x4470
- `Input_ReleaseFFDevicesAndDInput8 @ 0x6c9f80` — shutdown

## Per-frame
- `Win32_PumpMessagesAndSynthesizeInput @ 0x6c21a0` — PeekMessage/GetMessage/TranslateMessage + SendInput synthesis
- `FrameTail_PumpInputAndFlushJobs @ 0x6df8e0` — end-of-frame input/job flush
- `LookupUIInputBindingByCode @ 0x56ecc0` — 200-slot table walker, 20 bytes/entry, returns binding for given device code (48 xrefs)
- `GetUIInputProfileSlot @ 0x56f100` — fetch binding slot from active control profile
- `GetUIInputProfileFloatField @ 0x56f7b0` — sensitivity / dead-zone float
- `SetUIInputModeFlag @ 0x572e80` / `GetUIInputModeFlag @ 0x575b00` — keyboard/wheel/gamepad mode toggles
- `ConvertControlIndexToFlag @ 0x573020` — UI index → bitmask
- **Action ID table at `0x008f6e84`** — known entries: action 0x9d / key SC_E (0x22) = GAMEBREAKER. The 200-slot table at 0x56ecc0 is NOT input; it's FECarRecord.

## Game actions (GAMEACTION_*)
GAS, BRAKE, HANDBRAKE, STEERLEFT, STEERRIGHT, TURNLEFT, TURNRIGHT, SHIFTUP, SHIFTDOWN, NOS, GAMEBREAKER, RESET, FORWARD, BACK, JUMP, CAM_LOOKBACK.

## Key globals (input objects)
- `cFEngJoyInput @ 0x89b4c8` — input object string
- `cFEngJoyInput::ActionQueue @ 0x89b354` — accumulated per-frame action events
- `SteeringWheelDevice @ 0x8a7b88`

## Vehicle controller bridge
`ConstructAISteeringController @ 0x77b9e0` initializes 3 input register blocks at +0x5c, +0x78, +0x94 (0x50 bytes each). These are the steering/throttle/brake state slots that the AI **and** the player vehicle both write into — same machinery, just different upstream.

**Why:** PlayerCar vs AICar are differentiated by *who fills* these registers, not by *what consumes* them. When investigating a "the player and AI behave differently" bug, look at whoever's filling the controller, not the controller itself.

**How to apply:** Trace any input issue along: `Win32_PumpMessages → DInput8 poll → (true binding lookup TBD) → action queue → controller register → SimTickStepWithJoylogHook → vehicle tick`. Joylog playback skips the upper half by reading inputs from the recording instead.
