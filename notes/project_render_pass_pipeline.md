---
name: D3D9 per-frame render pass pipeline
description: Full per-frame render order mapped — Clear → ShadowMap → World → HUD → PostProcess → Present. Main render entry D3D9_PerFrame_RenderAndPresent @ 0x6e7220.
type: project
originSessionId: c4edf485-e85f-4e2f-ac31-e021ba66e8d6
---
NFSMW per-frame render pipeline (classical deferred-style):

```
GameFrameTick_MainLoopUpdate @ 0x663d30
  → GameFrame_TriggerPerFrameRender @ 0x64a7c0      [frame-rate limiter]
     → D3D9_PerFrame_RenderAndPresent @ 0x6e7220    ← MAIN RENDER ENTRY
        ├─ ApplyGlobalRenderStateChanges @ 0x6cfad0  (blend/depth/stencil state)
        ├─ ClearRenderTargetAndDepth @ 0x6c5da0       (clear RT + Z for frame start)
        ├─ for each of 24 entity slots:
        │     UpdateEntityTransformAndBounds @ 0x6cf400  (transforms)
        ├─ RenderWorldShadowMapOrLighting @ 0x6d0b00  (shadow vs lighting based on game state)
        │     branches on DAT_00925e90 (3=race/menu, 6=freeplay)
        │     uses shadow textures @ DAT_009b27ec (1024x1024)
        ├─ ResetRenderTargetStack @ 0x6d7500          (restore scene RT)
        ├─ RenderWorldGeometryAndEffects @ 0x6de300   ← scene graph walk
        │     traverses Ecstacy ModelSlotPool linked list @ DAT_0091c160
        │     world chunks → entities → meshes → strips via FERender API
        ├─ ProcessUIOrHUDElements @ 0x504d00         (NOT actually HUD — see correction below; runs anim-interp + camera + flag toggle only)
        │     ProcessAnimationInterpolation @ 0x5030d0  (skeletal interp)
        │     UpdateWorldCamerasAndViewport @ 0x72aa70   (camera matrices)
        ├─ Post-processing chain:
        │     D3D9_SetupPostProcessEffects @ 0x6d6000  (bloom/DoF/motionblur shader setup)
        │     ApplyPostProcessEffect @ 0x6d4dc0        (dispatched via DAT_00982af0)
        ├─ HandleScreenCaptureOrVideo @ 0x6c0910      (screenshot path)
        │     RenderBackbufferToTexture @ 0x6c05e0     (disk I/O)
        └─ Present  →  IDirect3DDevice9->vt[+0xac] (Present)
```

## Key globals
- `g_pIDirect3DDevice9 @ 0x982bdc`
- `g_pIDirect3D9Factory @ 0x982bd8`
- `DAT_0091c160` — Ecstacy scene graph linked list (ModelSlotPool head)
- `DAT_009b27ec` — shadow objects linked list
- `DAT_009196b4..0x919725` — camera array (15 cameras × 0x1c bytes each)
- `DAT_00925e90` — game state enum (3 = race/menu, 6 = freeplay)

## Shader resources (.efx files)
- `fx\shadow_map_mesh.efx` — main shadow projection
- `fx\car_shadow_map.efx` — per-car blob shadow
- Post-process: Bloom, MotionBlur, DoF (MOTIONALPHA), WindowReflection (chunk hash bChunk("WINDOWREFLECTION"))

## D3D9 Device vtable slots (verified)
| Slot | Method |
|------|--------|
| +0x44 | Present |
| +0xa4 | BeginScene |
| +0xa8 | EndScene |
| +0xac | Clear |

**Why:** Knowing the per-frame render order means you can hook any stage (e.g. shadow-map, post-process, HUD) without breaking the others. For screen-space mods, intercept `ApplyPostProcessEffect`. For HUD: do NOT hook `ProcessUIOrHUDElements` — see [[project_hud_rendering]]; the actual HUD walk lives inside the FE-managed render path, not in the in-frame call list.

**CORRECTION (2026-05-14):** `ProcessUIOrHUDElements @ 0x504d00` was misnamed historically. Decompilation shows it only runs `ProcessAnimationInterpolation`, `UpdateWorldCamerasAndViewport`, an anim timer, and a flag toggle. It is NOT the HUD-element walker. The 28 HUD widgets (Hud_Speedometer, Hud_Tachometer, Hud_Minimap, Hud_HeatMeter, etc.) are passive FNG-tree nodes updated via the UI event bus (not direct C++ tick).

**How to apply:** When investigating "why doesn't my mod render correctly?":
- World-mesh issue → look at RenderWorldGeometryAndEffects + scene graph
- Lighting/shadow → RenderWorldShadowMapOrLighting + DAT_009b27ec
- HUD → see [[project_hud_rendering]]; widget updates flow through UI event bus, not the in-frame call list
- Post-effects → ApplyPostProcessEffect + DAT_00982af0
