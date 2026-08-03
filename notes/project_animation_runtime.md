---
name: animation runtime (EAGL4Anim)
description: NFSMW uses EA's EAGL4Anim skeletal animation engine; tick driven by TickableBus_DispatchActiveSubscribers; pose eval before world render.
type: project
originSessionId: c4edf485-e85f-4e2f-ac31-e021ba66e8d6
---
NFSMW's animation system is **EAGL4Anim** (EA's proprietary skeletal animation library). Per-frame model:

```
GameFrameTick_MainLoopUpdate @ 0x663d30
  → TickableBus_DispatchActiveSubscribers @ 0x72e0c0   [event dispatcher — runs registered handlers]
  → ActiveComponents_TickAll @ 0x4ba940
       ↳ Vehicle_PullSimResultAndUnpackWheels @ 0x4b15e0  [extracts wheel/suspension state for procedural anim]
  → PerPlayerEntityUpdate_Dispatch @ 0x480e40           [character anim state]
  → D3D9_PerFrame_RenderAndPresent @ 0x6e7220
       ↳ RenderWorldGeometryAndEffects @ 0x6de300       [scene-graph walk applies poses to meshes]
```

## Pool inventory (EAGL4Anim memory pools)

| Pool | Address | Purpose |
|------|---------|---------|
| Anim_CNFSAnimBank_SlotPool | 0x893368 | Animation bank storage |
| AnimCtrlSlotPool | 0x8933e8 | Animation controller instances |
| Anim_CAnimPart_SlotPool | 0x8935a8 | Animation parts |
| Anim_CAnimSkeleton_SlotPool | 0x8935f4 | **Skeleton bone hierarchies** |
| WorldAnimInstanceEntry_SlotPool | 0x8938e7 | World-scale animation instances |
| WorldAnimCtrl_SlotPool | 0x893908 | World animation controllers |
| WorldAnimEntityTreeInfo_SlotPool | 0x893920 | Entity animation tree metadata |
| WorldAnimEntityTree_SlotPool | 0x893944 | Entity animation tree nodes |
| WorldAnimEntity_SlotPool | 0x893964 | Animated world entities |
| EAGL4Anim Memory Pool | 0x895da4 | Master memory arena |
| PosePaletteBank | 0x8954d0 | Pose palette (local→world skeleton transforms) |

## Skeletal math stack
- `ComputeMatrix4x4FromEulerAngles @ 0x6bdc60` — local bone transforms
- `ComputeMatrix4x4Multiply @ 0x4866c0` — bone chain hierarchy
- `Compose3DTransformFromAngles @ 0x46b7e0`
- `TransformVector3ByMatrix3 @ 0x401670`
- D3DXVec3Transform, D3DXVec3TransformCoordArray (vertex skinning, from d3dx9)

## Sources of pose data
1. **Vehicle procedural** — steering wheel, suspension, doors driven from `Vehicle_PullSimResultAndUnpackWheels @ 0x4b15e0` (extracts wheel rotation, suspension travel from physics).
2. **Character cutscenes** — WorldAnimCtrl/WorldAnimEntity pools (mission cutscenes, intros, outros).
3. **Audio-driven** — `AudioEntity_TypeA_Step @ 0x47d3c0` and `AudioEntity_TypeD_Step @ 0x482ec0` drive lip-sync style anims.

## Open questions
- Blend tree logic (BLENDMATRICES, BLENDSTATE strings exist but handler not yet located).
- IK solvers (no explicit IK code; likely baked into clips).
- Cutscene playback trigger path (pools exist; entry point TBD).

**Why:** The TickableBus pattern means modders inject custom anim handlers by registering with the bus, no need to hook the main render. For procedural anim mods (custom steering-wheel rotation, etc.), feed from `Vehicle_PullSimResultAndUnpackWheels`.

**How to apply:** When investigating animation issues:
- Procedural (vehicle parts) → vehicle physics unpack
- Character/cutscene → WorldAnimCtrl
- UI/screen → AudioEntity_TypeD (for audio-synced overlays)
- Skinning issues → MatrixMultiply / TransformVector chain
