---
name: gameplay scripting native bindings
description: NFSMW has an embedded scripting language (.NLT/.WLT/.SAT files); ~150 C++ natives are exposed via RegisterScriptNativesGameplay @ 0x0061e750.
type: project
originSessionId: c4edf485-e85f-4e2f-ac31-e021ba66e8d6
---
The mission/AI/UI scripting layer binds C++ functions as callable natives in `RegisterScriptNativesGameplay @ 0x0061e750` (huge function — ~150 calls to a family of `FUN_0061a***` and `FUN_0061c***` registrar helpers, each registering one native).

**Why:** The agent surfaced events like MPlayerEnterPursuit, MPursuitOver, AIGoalPursuit. Tracing them led to this canonical registration block — the single best entry-point for understanding gameplay logic, since every script-side primitive funnels through one of these natives.

**How to apply:**
- When investigating any gameplay event ("what happens when player wins a race?", "where is bounty awarded?", "who triggers a cop spawn?") — search for the native name as a string, find the script registration in `RegisterScriptNativesGameplay`, follow to the implementation.
- The implementations live at addresses ~0x604xxx–0x612xxx. Many are LABs (not full functions in Ghidra); creating a label is enough — the script binding registrar takes a function-pointer to the LAB.
- The registrar helper (FUN_0061a2f0 / FUN_0061a370 / FUN_0061cf50 / FUN_0061d050 / etc.) varies by parameter count and types. Each helper takes `(const char *name, void *fnptr)` plus optional category flag.
- The global `g_pGRaceStatus @ 0x91e000` is the script-visible race state singleton (registered by FUN_0061adf0(g_pGRaceStatus, "GRaceStatus")).

**Examples already mapped (high confidence):**
- AwardPlayerBounty → AwardPlayerBounty_Impl @ 0x612220
- AwardPoints → AwardPoints_Impl @ 0x60e030
- StartRace → StartRace_Impl @ 0x60dbd0
- AbandonRace → AbandonRace_Impl @ 0x60deb0
- SpawnCop → SpawnCop_Impl @ 0x60a670
- SetCopsEnabled → SetCopsEnabled_Impl @ 0x604f40
- ShowPauseMenu → ShowPauseMenu_Impl @ 0x6050f0
- ShowRaceOverSummary → ShowRaceOverSummary_Impl @ 0x6120c0
- (~30 more renamed; see Ghidra `_Impl` suffix)

**Curiosity:** The native "NotifyActivityFinsihed" is misspelled in the binding table (preserved from EA Black Box source). Still hashes/dispatches by that exact spelling.
