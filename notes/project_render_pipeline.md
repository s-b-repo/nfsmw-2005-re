---
name: NFSMW Direct3D 9 render pipeline anchors
description: D3D9 device init, IDirect3DDevice9 vtable, render globals, and the CreateDevice→Present flow
type: project
originSessionId: c4edf485-e85f-4e2f-ac31-e021ba66e8d6
---
The render subsystem in `speed.exe` is a thin wrapper around D3D9. The factory + device live as singletons; the device-create path also performs the very-first frame Clear→BeginScene→EndScene→Present.

**Boot path** (called from `InitializeEngine`):
```
RenderAndWindow_Initialize         0x006e69f0
  ├─ Direct3DCreate9(0x20)         → idirect3d9_factory_ptr  @ 0x00982bd8
  ├─ CreateObjectPool ×2           → render_object_pool_a/b  @ 0x00982b7c / 0x00982b80
  ├─ LoadIconA / LoadCursorA / RegisterClassExA("GameFrame")
  ├─ AdjustWindowRect / CreateWindowExA   → game_window_hwnd  @ 0x00982bf4
  └─ D3D9_CreateDeviceAndFirstPresent  0x006bfbd0
        ├─ vt[0x10] GetAdapterCount  + vt[0x14] GetAdapterIdentifier loop
        │     looks for adapter "NVIDIA NVPerfHUD"; if found, uses devType=2 (REF) instead of 1 (HAL)
        ├─ vt[0x40] CreateDevice (HARDWARE_VERTEXPROCESSING / fallback to SOFTWARE)
        │     → idirect3d9device_ptr  @ 0x00982bdc
        ├─ vt[0xA4] BeginScene  ·  vt[0xAC] Clear (TARGET|ZBUFFER|STENCIL, depth=1.0f)
        ├─ vt[0xA8] EndScene  ·  vt[0x44] Present (NULL src/dst/hWnd/dirty)
        └─ done — first frame is the device-create frame.
```

**Other D3D9 setup steps reachable from the boot path:**
- `D3D9_BuildPresentParameters (0x006bfab0)` → fills `d3d9_present_parameters @ 0x0093e82c` (14-dword D3DPRESENT_PARAMETERS struct).
- `D3D9_QueryAdapterCapabilities (0x006c1510)` → vt[0x38] GetDeviceCaps + vt[0x14] adapter info.
- `D3D9_GrabBackBufferAndDepth_RunInit (0x006bd7c0)` → vt[0x48] GetBackBuffer, vt[0xA0] GetDepthStencilSurface, dispatches 6 sub-inits.
- `D3D9_CreateDefaultTexture1x1 (0x006bcdc0)` → vt[0x5C] CreateTexture(1×1) → `default_white_texture @ 0x00982a6c`.
- `D3D9_CreateMainSurfaces (0x006bcfa0)` → main render texture + back-buffer + depth.

**IDirect3DDevice9 vtable slots in use** (verified from decomps):
```
+0x1C  GetDeviceCaps               +0x44  Present
+0x48  GetBackBuffer               +0x5C  CreateTexture
+0x68  CreateVertexBuffer          +0x74  CreateDepthStencilSurface
+0xA0  GetDepthStencilSurface      +0xA4  BeginScene
+0xA8  EndScene                    +0xAC  Clear
+0xD4  SetTextureStageState        +0xE4  SetRenderState
+0x114 SetSamplerState
```

**Resource setup helpers** (called from `RenderAndWindow_Initialize` chain):
- `D3D9_InitializeDefaultRenderStates    0x006cfce0`  — bulk SetRenderState calls (ZENABLE, DITHER, FOG=off, etc.) plus per-stage sampler states
- `D3D9_CreateShadowMapTextures1024      0x006c8770`  — 2× 1024² textures @ `shadow_map_texture_a/b @ 0x00982cf0/0x00982cf8` with surface levels at `shadow_map_surface_a/b @ 0x00982cec/0x00982cf4`
- `D3D9_AllocateStaticVertexBuffers      0x006c2aa0`  — vt[0x68] CreateVertexBuffer for fixed-size geometry buffers
- `D3D9_SetupPostProcessEffects          0x006d6000`  — uses `CalculateDjbStringHash("WINDOWREFLECTION")` to register a post-process effect

**Globals** (all in .data):
- `idirect3d9_factory_ptr      @ 0x00982bd8`  — IDirect3D9*
- `idirect3d9device_ptr        @ 0x00982bdc`  — IDirect3DDevice9*
- `game_window_hwnd            @ 0x00982bf4`  — HWND of "GameFrame"
- `d3d9_present_parameters     @ 0x0093e82c`  — 14-dword PRESENT_PARAMETERS (BackBuffer*, hDeviceWindow=hwnd, Windowed=1, etc.)
- `backbuffer_surface_ptr      @ 0x00982a28`
- `depthstencil_surface_ptr    @ 0x00982a2c`
- `default_white_texture       @ 0x00982a6c`
- `main_render_texture         @ 0x00982a7c`
- `main_backbuffer_surface     @ 0x00982a80`
- `main_depthstencil_surface   @ 0x00982a84`
- `render_object_pool_a/b      @ 0x00982b7c / 0x00982b80`

**Open thread:** the per-frame Present caller wasn't located via byte-pattern (`A1 DC 2B 98 00 8B 08 FF 51 44` returned no matches), suggesting the device pointer is loaded into a non-eax register and the call site uses a register-relative path. The call lives somewhere in the GameFrameTick render-submit tail; finding it needs targeted decomp of the 30+ functions that read `idirect3d9device_ptr` (already enumerable via xrefs).

**How to apply:** When seeing `(**(code **)(*idirect3d9device_ptr + 0xNN))(...)`, decode the slot via the table above. When a function reads only `idirect3d9device_ptr` and dispatches one or two slots, it's a thin per-method wrapper — name it `D3D9_<MethodName>_Wrapper`.
