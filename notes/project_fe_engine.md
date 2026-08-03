---
name: front-end (FNG) UI engine
description: NFSMW front-end is a screen-stack manager keyed on .fng asset names; root context is g_pUIRootContext @ 0x91cadc, manager is g_pFrontEndManager @ 0x91cf90.
type: project
originSessionId: c4edf485-e85f-4e2f-ac31-e021ba66e8d6
---
NFSMW's GUI is a hierarchical FNG screen system: each screen is a `.fng` asset, screens push onto a stack with payload+vtable, input/audio/render route through the same dispatcher.

## Globals
- `g_pUIRootContext @ 0x91cadc` — root UI context. Screen-name pointer at +0xc, payload at +0x10/+0x14.
- `g_pFrontEndManager @ 0x91cf90` — FE state machine. Flags at +0x12C, screen-count at +0x19c.
- `g_FEMessageHandle @ 0x91ca60` — async message-queue handle (set by FE_PostMessage @ 0x5989b0).
- Asset cache: `DAT_0091cfc0[120]` — pending FNG-load slots.

## Anchor functions
- `FE_Initialize @ 0x5538e0` — boot path; allocates 0x164-byte CFEManager (CFEManager_Constructor @ 0x5496a0), wires MainMenu.fng + OL_MAIN.FNG.
- `FE_Shutdown @ 0x533460`
- `FE_LoadAssetScreenByName @ 0x571eb0` — async loader, hash-keys into 120-slot cache.
- `FE_UnloadFNGScreen @ 0x5169b0` / `FE_RecursiveScreenPop @ 0x525a70`
- `FE_ScreenStateDispatcher @ 0x623f80` — race/menu state machine; dispatches by race-status (0/1/2)
- `FE_PauseScreenPush @ 0x62f220` — pause overlay path; pushes Pause_Main.fng with FE_AllocatePauseContext @ 0x5102f0
- `FE_RaceEventMessageHandler @ 0x58bd10` — crafts localized text from race attributes, posts via FE_PostMessage
- `FE_InputDispatcher @ 0x549460` — routes controller input to active screen
- `FE_AudioRoutingTableByScreenHash @ 0x4c2340` — 39-entry hash → audio enable/disable per screen (MainMenu/Pause_*/PostRace_*…)
- `FE_MenuFlowController @ 0x517110` — main vs OL_MAIN.FNG branch based on online flag

## Hash mechanism
FE caches FNG screen names via `CalculateStringHash24` (24-bit CRC variant). The Audio routing table at `FE_AudioRoutingTableByScreenHash` is keyed on those hashes.

**Why:** With this mapped, the front-end is no longer a black box. A modder adding a new screen needs to: (a) drop a `MyScreen.fng` into the bundle, (b) add a hash binding in audio routing if they want audio, (c) push it via FE_PostMessage with the screen-name string.

**How to apply:** When investigating UI behavior, the chain is:
input → FE_InputDispatcher → screen vtable → FE_PostMessage → screen-state-dispatcher (RaceEventMessageHandler) → FE_LoadAssetScreenByName → FNG vtable. For race/pause overlay, add FE_PauseScreenPush.
