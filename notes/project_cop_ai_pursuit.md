---
name: cop AI + pursuit state machine
description: Goal-stack AI with cop-class-specific pursuit goals (AIGoalPursuit/HeliPursuit) and tactical AIActionRam/RoadBlock. SetAICopPursuitGoal @ 0x42ab80 is the dispatch root.
type: project
originSessionId: c4edf485-e85f-4e2f-ac31-e021ba66e8d6
---
NFSMW cop AI uses a **stacked goal-action pattern** — each cop unit holds a goal stack with active objectives. Goals/actions are hashed (Jenkins mix3) and looked up in a registry to instantiate the right vtable.

## Pursuit state machine

```
Idle/Patrol
  → AIGoalNone (ground cops) / AIGoalPatrol
Spotted
  → SetAICopPursuitGoal @ 0x42ab80 selects by cop type:
       ground   → AIGoalPursuit
       heli     → AIGoalHeliPursuit
Engaged
  → CreateAIActionRace @ 0x43b800 dispatches per-cop behavior
       loads: AIActionRace, AIActionPursuitOffRoad, AIActionTooDamaged
       evaluated each frame by ProcessAIDecisionEvaluation
Escalated  (high heat → ramming/PIT)
  → CreateAIActionRam @ 0x43b9b0  / CreateAIGoalPit @ 0x43fe90
Backup/Roadblock
  → CreateAIActionStaticRoadBlock @ 0x43be50
Busted/Escaped
  → AIGoalHeliExit @ 0x423510 (timeout) / player-evade
```

## Anchor functions
- `PushAIGoalByHash @ 0x422480` — pushes goal onto cop's stack (registry lookup at DAT_0090d8e8)
- `SetAICopPursuitGoal @ 0x42ab80` — selects ground vs heli pursuit
- `CreateAIActionRam @ 0x43ba28` (alias of `0x43b9b0`)
- `UpdateAIActionRam @ 0x43bb28`
- `CreateAIActionRace @ 0x43b800`
- `CreateAIActionStaticRoadBlock @ 0x43be50`
- `CreateAIGoalPit @ 0x43fe90`
- `AIGoalHeliExit @ 0x423510`
- `AwardPlayerBounty_Impl @ 0x612220`

## Target tracking
- `FUN_00423860`: SetTargetByID — queries target pool at DAT_0090d664
- `FUN_004238b0`: SetWaypointPos (X,Y,Z fallback)
- `FUN_00408810`: line-of-sight raycast (returns LOS bool)

## Bounty accumulation
`AwardPlayerBounty_Impl @ 0x612220` adds to player profile slot at `*(int*)(DAT_0092d87c[0x4]) + 0x414 + 0xa8`, divides by `*(int*)0x8f5a50`, fires event hash 0x20d60dbf (PursuitBountyAwarded).

## Vtables (referenced by name)
- vtbl_AIActionRam, vtbl_AIActionRace
- vtbl_AIGoalPursuit, vtbl_AIGoalHeliPursuit

## Globals
- `DAT_0090d8e8` — AI goal factory registry (hash → vtable)
- `DAT_0090d664` — target pool / lookup table
- `DAT_0092d87c` — active player profile (bounty offset +0x414+0xa8)
- `DAT_8f5a50` — bounty divisor (likely 1.0)
- `DAT_0092058c` — cached MPlayerEnterPursuit hash

**Why:** Pursuit is the headline feature of NFSMW (the "Most Wanted" loop). With this state machine + hash registry mapped, modders can: (a) add new cop classes by registering new AIGoal vtables, (b) tune escalation thresholds via the bounty divisor, (c) inject custom actions into the per-frame ProcessAIDecisionEvaluation chain.

**How to apply:** When investigating cop behavior, traverse goal-stack first (PushAIGoalByHash), then per-action update (CreateAIAction*). For "why does my heat go up so fast?", look at `AwardPlayerBounty_Impl` callers — these are the per-infraction triggers.
