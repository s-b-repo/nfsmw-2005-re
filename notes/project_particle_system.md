---
name: particle/effects pool layout
description: Particles, Emitters, and EmitterGroups are pre-allocated in three CreateObjectPool slots, sized for ~1024/500/200 instances respectively.
type: project
originSessionId: c4edf485-e85f-4e2f-ac31-e021ba66e8d6
---
`Particle_And_Emitter_Pools_Initialize @ 0x4ff0a0` builds three pools at startup:

| Pool | Slot Size | Max Instances | Vtable | Pointer global |
|------|-----------|---------------|--------|----------------|
| ParticleSlotPool      | 0x70 | 0x400 (1024) | 0x899d94 | g_pParticleSlotPool @ 0x916060 |
| EmitterSlotPool       | 0x90 | 500          | 0x899da8 | g_pEmitterSlotPool @ 0x916064 |
| EmitterGroupSlotPool  | 0x80 | 200          | 0x899db8 | g_pEmitterGroupSlotPool @ 0x916068 |

After construction it clears flag bits 0 and 1 in each pool's `[+0x14]` field — likely "auto-expand" / "thread-safe" toggles.

Master enable: `g_nParticleSystemEnable @ 0x9017ec` (default 1).

**Why:** With these caps you can predict OOM behavior — `_malloc`-style pool exhaustion when a track has more emitters than the budget. Modders often hit the 1024 particle cap during big crashes; raising it requires patching the constant.

**How to apply:** When investigating effects spawn/despawn, look for callers of `CreateObjectPool` (already named at 0x4662e0). Effect category strings (CARFX_EXHAUST_SMOKE/SKID_SMOKE/Nitrous) are at .data offsets near the pools — particle-spawn dispatch hashes effect-name strings with bChunk(=Jenkins mix3) and looks them up in attributes data.

Effect classes seen: `EffectsPlayer / EffectsSmackable / EffectsVehicle / EffectsCar / EffectsFragment` (likely subclasses of an EffectsBase).
Shader file: `fx\Particles.efx`
