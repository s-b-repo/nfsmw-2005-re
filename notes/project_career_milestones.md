---
name: career mode + milestones
description: Event-driven career-progression model. Race-end events fan out via hashed messages (MNotifyMilestoneProgress, MNotifyPlayerRep) to listeners that update milestones, blacklist, unlocks.
type: project
originSessionId: c4edf485-e85f-4e2f-ac31-e021ba66e8d6
---
NFSMW career mode is **event-driven**: race finish → notify-placement → milestone-evaluator → message-broadcast → UI.

## Anchor functions
- `ProcessStartRace @ 0x60dbd0` (was StartRace_Impl) — race init
- `ProcessAbandonRace @ 0x60deb0`
- `ProcessAddRacer @ 0x601f90` — adds racer/player to race
- `ProcessGetRacerIndex @ 0x60dae0`
- `ProcessKnockoutRacer @ 0x611440`
- `ProcessNotifyRacePlacement @ 0x60aa00` — race-end placement notify
- `ProcessAwardPoints @ 0x60e030` — reputation/skill points
- `ProcessAwardPlayerBounty @ 0x612220`
- `ProcessAwardBonusTime @ 0x5fe600`
- `ProcessChallengeComplete @ 0x605140`
- `ProcessShowRaceOverSummary @ 0x6120c0` — post-race screen
- `MilestoneProgressEventConstructor @ 0x5dd670`
- `GetMilestoneProgressMessageHash @ 0x5dd5f0`
- `GetMessageHashMilestoneReached @ 0x5de370`
- `GetPlayerRepMessageHash @ 0x4058e0`
- `GetEventHashPlayerEnterPursuit @ 0x626480`
- `GetRacePlacementMessageHash @ 0x604440`
- `GetRaceTimeBroadcastMessageHash @ 0x5db8a0`
- `HandleFrontendRaceEventDispatch @ 0x58bd10` (was FE_RaceEventMessageHandler)
- `GetGameMasterDataPointer @ 0x6dfaf0` — global game singleton

## Career data globals
- `CAREER_DATA` string @ 0x89da2c
- `CAREER_COMPLETED_DATA` string @ 0x89ceb8
- `GAME_COMPLETED_DATA` string @ 0x89ced0
- `BLACKLIST_PURSUIT_MILESTONES_%02d` format @ 0x89a111c
- `g_pGRaceStatus @ 0x91e000` — active race state; per-racer data at +0x1968

## Milestone FNG screens
- `InGameMilestones.fng` — in-race progress popup
- `PostRace_MilestoneRewards.fng` — post-race rewards
- `SafeHouseMilestones.fng` — safe house overview
- `PostRaceMilestonesScreen` — full milestone screen

## Message broadcast model
Race events fire as hashed messages (Jenkins mix3) — `MNotifyMilestoneProgress`, `MNotifyPlayerRep`, `MPlayerEnterPursuit`, `MPursuitOver`.
The FE_RaceEventMessageHandler (already named) multiplexes them to UI listeners: FUN_00632d20, FUN_006357a0, etc.

## Save persistence
- **CORRECTION (2026-05-14):** `MSG_R_BI_DATACRC @ 0x8b6b7c` is **NOT** related to save CRC. It sits in the netcode message-name table next to MSG_R_SC_RESTARTLOAD / SERVERSTATE_LOADING / CLIENTSTATE_LOADING and has **zero code xrefs** — it's an orphan/diagnostic string for network bundle-integrity data sync. The actual save integrity uses **MD5** (not CRC); see `project_save_load.md` (`ComputeMd5OfSaveBuffer @ 0x57f920`).

## Award flow
```
AwardPoints (script native)
  → GetGameMasterDataSingleton
  → EntityRouter_DispatchByIdRange (broadcast to audio + UI subscribers)
```

**Why:** Career progression is data-driven — milestones/unlocks are configured via attributes.bin (we cracked MILESTONE_COST_TO_STATE, MILESTONE_INFRACTIONS, MILESTONE_PURSUIT, MILESTONE_PURSUITBOUNTY). Behavior changes don't need code patches.

**How to apply:** When investigating "why doesn't milestone X unlock?":
- Check the milestone evaluator listener subscribers (FUN_00632d20, FUN_006357a0)
- Inspect the message-hash in `MNotifyMilestoneProgress` for argument shape
- Trace from `ProcessNotifyRacePlacement` (race-end) → `MilestoneProgressEventConstructor`
- For UI absences: check `HandleFrontendRaceEventDispatch` routing
