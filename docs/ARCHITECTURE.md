# NFS Most Wanted (2005) — speed.exe Architecture & Modding Reference

Canonical reference compiled from 30+ days of static + 6 live-debugger sessions on `speed.exe` (PE32 i386, MSVC 7.10, image base `0x00400000`, 26,316 functions, **6,513 named (24.7%)** as of 2026-05-14).

**See also:**
- [`ANTI_RE_AND_PATTERNS.md`](ANTI_RE_AND_PATTERNS.md) — defensive techniques, coding patterns, misread corrections, and surprising findings
- [`renames.csv`](renames.csv) — full export of all 6,513 named functions (address, name, xref count, isThunk)
- [`sdk_addrs.json`](sdk_addrs.json), [`sdk_enums.json`](sdk_enums.json), [`sdk_structs.json`](sdk_structs.json) — NFSPluginSDK extracted index
- [`nfsplugin_sdk_mw05/`](nfsplugin_sdk_mw05/) — full BSD-3 SDK headers mirrored locally

Game build: NFSMW Magipack repack (with WidescreenFix, ExtraOptions, HDReflections, HUDAdapter ASI mods + DSOAL DSOUND wrapper).

---

## Module map (verified at runtime under Wine 11.7)

```
PE          0x00400000 - 0x00a78fff   speed.exe (image base)
  .text     0x00401000 - 0x0088ffff
  .rdata    0x00890000 - 0x008e9fff
  .data     0x008ea000 - 0x009c6e0f
  .rsrc     0x009c7000 - 0x00a37fff

PE-Wine     0x7B3F0000               syswow64\d3d9.dll
PE-Wine     0x79850000               wined3d.dll
PE-Wine     0x78390000               syswow64\d3dx9_26.dll
PE-Wine     0x75D10000               syswow64\DINPUT8.dll
PE          0x777C0000               app\DINPUT8.dll  (mod)
PE-Wine     0x76420000               app\DSOUND.dll   (DSOAL+EZ Wheel Wrapper)
```

Wine maps `speed.exe` 1:1 at its PE-declared image base (no relocation). All static addresses in this doc match runtime addresses directly.

---

## Per-frame execution graph

```
WinMain main loop
  └─ GameFrameTick(elapsed_ms)                      0x00663d30
       ├─ ProcessSimulationStep(seconds)            0x00661280   [profiler accumulator only — NOT physics]
       │  └─ SimulationStep_AccumulateAndTrace      0x0065fe90
       ├─ PeriodicTimerDispatcher_Run               0x007ec59c   [stride-20 cron-style callbacks]
       ├─ TickableBus_DispatchActiveSubscribers     0x0072e0c0   [event bus — only no-op subscriber registered statically]
       ├─ ComputeElapsedSecondsFromTimer            0x00642e60
       ├─ SubsystemDtAccumulator(dt)                0x0064a680   ← THE dt-distribution junction
       │   if IsWorldSimActive() && World.state == 3:        [== gameplay/in-race state]
       │   {
       │       FUN_00779a30(dt)
       │         → TrackedObjList_TickEach           0x00770cb0
       │         → SecondaryTrackedList_TickEach     0x007799f0
       │       ActiveComponents_TickAll(dt)          0x004ba940   ← ROOT of vehicle physics dispatch
       │         → for each entry in active_vehicle_components_arr_a (live during race):
       │              Vehicle_PullSimResultAndUnpackWheels  0x004b15e0
       │                → VehicleAgent_QuerySimResult_Virtual  0x006e9e40   [calls body[+8]->vt[1]]
       │                  → pvehicle_MatchTypeAndDispatch_vt1  0x006a4040   [id-check, delegates]
       │                    → pvehicle_DispatchSubobjVt1AndVt4  0x00694700  [delegates to body[+0x98]]
       │                      → pvehicle_AggregatePhysicsState  0x00694160 ← LEAF state collector
       │                          (reads ~7 sub-objects, packs out-buf with wheels/throttle/state)
       │                          The actual position integration runs in EAGL middleware via
       │                          this[+0x70].vt[0x34], which returns post-integrated floats.
       │       FUN_006e7a00(dt)   [4 misc updaters: keyframe, world, etc.]
       │   }
       │   FUN_00480e40(dt)  PerPlayerEntityUpdate_Dispatch   [per-player input/action card]
       │   FUN_00480c10(dt)  PostStateUpdate_DispatchPair
       │     → PerPlayerSubsystemTick                  0x0047c880  ← AUDIO+UI dispatcher (NOT vehicles)
       │           23 slots × 0x70 stride at [0x009195e0..0x0091a050]
       │           Each slot is a doubly-linked list of audio/UI entities.
       │           Indirect call at 0x47c8af = perplayer_indirect_call_vt2.
       │           Slot 1 = 3D positional audio entities.
       │           Slot 3 = UI screen animation entities (.fng overlays).
       │           Slots 0,2,4-22 = unused or for entity types we haven t seen.
       │     → KeyframeTimeline_Advance                0x0064c2d0  [audio/anim timeline scrubber]
       ├─ ProcessGameStateMachine(&DAT_00925e70)     0x006596a0
       ├─ FUN_004d0610(scene_root, seconds_per_step) [frontend / DirectX device path]
       ├─ ProcessDeferredFreeQueue                   0x00633ef0
       ├─ FrameTail_PumpInputAndFlushJobs            0x006df8e0
       │   → DeferredJobQueue_FlushMaxThree           0x006de100  [max-3 job dispatch]
       │   → Win32_PumpMessagesAndSynthesizeInput     0x006c21a0  [PeekMessageA + SendInput synth]
       └─ ... eventually:
          D3D9_PerFrame_PresentAndCheckLost          0x006e7220   ← per-frame Present orchestrator
              ├─ if device-reset needed:
              │     D3D9_BuildPresentParameters       0x006bfab0
              │     FUN_006db0d0  (Reset device)
              └─ at 0x006e75ea (labeled d3d9_per_frame_present_call_site):
                    push edi×4 (NULL)        ; Present(src=NULL, dst=NULL, hwnd=NULL, dirty=NULL)
                    push eax                  ; this = g_pIDirect3DDevice9
                    call [vtable+0x44]        ; → wine d3d9!Present at 0x7b3f95a0
```

---

## Subsystem reference

### Render (D3D9)

**Boot path** (in `RenderAndWindow_Initialize @ 0x006e69f0`):
```
Direct3DCreate9(0x20)               → idirect3d9_factory_ptr  @ 0x00982bd8
RegisterClassExA("GameFrame")
CreateWindowExA                     → game_window_hwnd        @ 0x00982bf4
D3D9_CreateDeviceAndFirstPresent    @ 0x006bfbd0
  ├─ vt[0x10] GetAdapterCount + vt[0x14] GetAdapterIdentifier
  │  (looks for "NVIDIA NVPerfHUD" → uses devType 2/REF if found)
  ├─ vt[0x40] CreateDevice (HARDWARE_VERTEXPROCESSING)
  │   → idirect3d9device_ptr @ 0x00982bdc
  ├─ vt[0xA4] BeginScene · vt[0xAC] Clear · vt[0xA8] EndScene · vt[0x44] Present
```

**IDirect3DDevice9 vtable slots** (verified):
| Slot | Method |
|---|---|
| +0x1C | GetDeviceCaps |
| +0x44 | **Present** |
| +0x48 | GetBackBuffer |
| +0x5C | CreateTexture |
| +0x68 | CreateVertexBuffer |
| +0x74 | CreateDepthStencilSurface |
| +0xA0 | GetDepthStencilSurface |
| +0xA4 | BeginScene |
| +0xA8 | EndScene |
| +0xAC | Clear |
| +0xD4 | SetTextureStageState |
| +0xE4 | SetRenderState |
| +0x114 | SetSamplerState |

**Resource setup helpers:**
- `D3D9_InitializeDefaultRenderStates` 0x006cfce0 — bulk SetRenderState
- `D3D9_CreateShadowMapTextures1024`   0x006c8770 — 2× 1024² shadow textures
- `D3D9_AllocateStaticVertexBuffers`    0x006c2aa0
- `D3D9_SetupPostProcessEffects`        0x006d6000 — uses `bChunk("WINDOWREFLECTION")`
- `D3D9_DefineVertexDeclaration`        0x006bf3e0 — D3DVERTEXELEMENT9 array

**Globals:**
| Address | Name |
|---|---|
| 0x00982bd8 | `g_pIDirect3D9Factory` (= `idirect3d9_factory_ptr`) |
| 0x00982bdc | `g_pIDirect3DDevice9` (= `idirect3d9device_ptr`) |
| 0x00982bf4 | `g_pGameWindowHwnd` (= `game_window_hwnd`) |
| 0x0093e82c | `d3d9_present_parameters` (14-dword PRESENT_PARAMETERS) |
| 0x00982a28 | `backbuffer_surface_ptr` |
| 0x00982a2c | `depthstencil_surface_ptr` |
| 0x00982cf0/8 | `shadow_map_texture_a/b` |

### Streamer (BUN/LZC asset bundles)

```
OpenAssetBundleStream(path, mode, prio, ...)        0x0065fd30
  pops node from asset_stream_node_pool @ 0x00925878
  ConstructAssetBundleStream(node, path, mode, prio, ...)
  splices into circular list at:
    asset_stream_list_head_sentinel @ 0x009259a4
    asset_stream_list_tail          @ 0x009259a8

OpenAssetBundleAndBindCallback(path, mode, prio, cb, arg, ...)  0x00661760
  Convenience: OpenAssetBundleStream + BindBundleLoadCallback in one call.

Boot loaders (block on asset_load_pending_count_a/b @ 0x00925858/c):
  LoadGlobalAssets_GLOBALA_Blocking   0x00662b30   loads "GLOBAL\GLOBALA.BUN"
  LoadFrontendBootAssets              0x00664780   loads MemoryFile, attributes.bin (VPAK "db"),
                                                   GLOBALB.LZC, CARS\BRAKES\GEOMETRY/TEXTURES.BIN
  UI_LoadDynamicAssetByContext        0x00662b80   asset name from GetGlobalUIRootContext()

State-machine entry points (named in prior session):
  StateBeginGameFlowLoadTrack         calls TRACKS\STREAM%s.BUN format
  StateLoadingFrontEnd                FRONTB.LZC, FRONTA.BUN
  DispatchRegionLoaderHandler         INGAMEB.LZC + region BUNs
```

**File formats:**
- `.BUN`: EA EAGL bChunk container. 8-byte chunk headers `{u32 chunk_id, u32 size}`. Top-level chunk_id `0xB3300000` is the BPACK container. Children: `0xB3310000` (manifest), `0xB3320000` (asset payload).
- `.LZC`: JDLZ-compressed (Joe Davenport LZ), version 0x02. **Decompressor at speed.exe 0x0064db40.** Header layout: `'JDLZ' (u32) + version(u8=0x02) + reserved(3) + decompressed_size(u32) + compressed_size_inc_header(u32)`. Compressed stream starts at offset 0x10 with `flag1_byte | flag2_byte | payload`. Algorithm reverse-engineered: flag1 LSB **0=literal, 1=back-ref** (NOTE: opposite of public Underground/Carbon JDLZ); flag2 LSB chooses form A (offset 1..16, length 3..4098 — RLE-style) vs form B (offset 17..2064, length 3..34). Working Python at `/home/cortix/tools/nfsmw_bun_reader/jdlz_nfsmw.py`.
- `attributes.bin` / `gameplay.bin`: VPAK format (`'VPAK' + version(u32) + ...`).

### Input (DirectInput8 + CDAction layer)

**Boot path** (in `InitializeEngine`):
```
Input_Initialize_DInput8                  0x006e2640
  ├─ Input_ZeroStateBlocks(state_block)   0x006c9d70
  ├─ DirectInput8Create(hModule, 0x800, IID_IDirectInput8, &dinput8_device_root_ptr, NULL)
  │       IID @ 0x008c065c
  │       DInput8 ptr @ 0x00982d14
  └─ Input_EnumerateFFDevicesAndAxes      0x006dc590
        ├─ vt[0x10] EnumDevices
        │     callback: Input_EnumerateFFDeviceCallback @ 0x006d8100
        │       ├─ vt[0xC] CreateDevice → IDirectInputDevice8 ptr
        │       ├─ classify by DIDEVICEINSTANCE.dwDevType (param+0x24):
        │       │     0x14 DI8DEVTYPE_DRIVING    → ff_devtype_driving_slot[N]   = 1
        │       │     0x15 DI8DEVTYPE_FLIGHT     → ff_devtype_flight_slot[N]    = 1
        │       │     0x16 DI8DEVTYPE_1STPERSON  → ff_devtype_1stperson_slot[N] = 1
        │       └─ vt[0x18] SetProperty(DIPROP_AUTOCENTER, OFF)
        └─ for each FF device: vt[0x10] EnumObjects → axes
            callback: ff_device_enum_objects_callback @ 0x006d82f0
            
Input_AcquireFFDevicesForEntity            0x006dc790
  → Input_SetFFDeviceDataFormatAndCoopLevel 0x006d81f0
        vt[0x2C] SetDataFormat (using didataformat_joystick @ 0x008c152c)
        vt[0x34] SetCooperativeLevel(hwnd, FOREGROUND|NONEXCLUSIVE)

Input_FFDevice_SetAxisRangeProperty        0x006d8270
  vt[0x18] SetProperty(DIPROP_RANGE, ±10000)
```

**Per-frame**: `Win32_PumpMessagesAndSynthesizeInput @ 0x006c21a0` runs `PeekMessageA` + synthesizes mouse INPUT events. The actual `IDirectInputDevice8::GetDeviceState` polling site lives behind the device-registry hash dispatch (see below) — direct call site not pinned statically.

**Hash-keyed device registry:**
```
Input_RegisterDeviceByNameHash             0x0063cbf0
  Hashes a device name with BChunkHash_JenkinsMix3 (e.g. "GameDevice",
  "MouseDevice", "KeyboardDevice") and walks input_device_registry_head @ 0x00920464
  (linked list, 12-byte nodes {hash, factory_fn, next}).
  On match, calls factory_fn(0) to obtain the device handler.
```

**CDAction layer (above raw input):**
```
Player_SelectActiveActionCard       0x00479900
  Hashes "CDActionDrive" / "CDActionTrackCop" / "CDActionTrackCar" / "CDActionIce"
  by current game state. Stores at:
    entity[+0x10]  = bChunk64(name)
    entity[+0x18]  = djb24(name)
    entity[+0x1c]  = raw name string ptr
PerPlayerEntity_TickActionCard      0x00479de0
  Per-frame tick: decrements timers (entity+0x2b8, +0x2b4); dispatches
  vt[6] of the active action-card object (entity+0x20) with state at entity+0x2c0;
  falls through to vt[1] for the action-card update.
CDActionTrackCar_Activate           0x00479d80
```

CDAction strings: `CDActionDrive`, `CDActionShowcase`, `CDActionIce`, `CDActionTrackCar`, `CDActionTrackCop`, `CDActionDebug`, `CDActionDebugWatchCar`.

### Vehicle physics (in-race)

The 23-slot `PerPlayerSubsystemTick` array holds **AUDIO+UI** entities, NOT vehicles. The actual vehicle physics flows through a different array: `active_vehicle_components_arr_a_head @ 0x00913e74`.

**Live snapshot (in race, 6 vehicles spawned):**
```
active_vehicle_components_arr_a_head  →  array of 6 audio entity pointers
                                          (4 with vtbl 0x00897740 = "Aud: EAX_HeliState")
                                          
Each audio entity at +0x08 → vehicle physics body on heap:
   body[+0x00]  primary vtable
   body[+0x08]  secondary vtable (MSVC multi-inheritance)
   body[+0x14]  heap subobject (state holder)
   body[+0x60]  audio back-ref (the audio entity that wraps this body)
   body[+0x98]  sub-physics object pointer  ← vt[1]/vt[4] called per-frame
   body[+0x100..+0x140] position + velocity floats (e.g., world coords -2881,-167,-3193)
```

**Two pvehicle vtables observed:**
| Vtable | Count | Class |
|---|---|---|
| `vtbl_pvehicle_AICar @ 0x008ac0fc` (+ `vtbl_pvehicle_AICar_SecondaryView @ 0x008ac0f4`) | 4 | AI cars / cops / traffic |
| `vtbl_pvehicle_PlayerCar @ 0x008ac06c` | 2 | player vehicle |

Both share **sub-physics object vtable** `vtbl_pvehicle_SubPhysicsObject @ 0x008ab6a0`.

**Vehicle integration call chain (named end-to-end):**
```
ActiveComponents_TickAll(dt)                 0x004ba940
 → for each entry:
    Vehicle_PullSimResultAndUnpackWheels     0x004b15e0   per-vehicle data refresh
       backs up prev pos (this[+0x14] → +0x70..+0x78)
       queries new state via VehicleAgent_QuerySimResult_Virtual
       computes velocity = (new − old) / dt at this[+0x90]
       unpacks 4 wheels (stride 0x44):
         per-wheel pos/contact-flag/friction/material-handle
     → VehicleAgent_QuerySimResult_Virtual    0x006e9e40   vt-call body[+8]→vt[1]
       → pvehicle_MatchTypeAndDispatch_vt1    0x006a4040
            id-match check; delegates to vt[10] of self
         → pvehicle_DispatchSubobjVt1AndVt4   0x00694700
              → pvehicle_AggregatePhysicsState 0x00694160  ← LEAF
                   reads ~7 sub-objects:
                     this[+0x60].vt[1/7/8]   interp factor / float / byte flag
                     this[+0x64].vt[2]       suspension vec3
                     this[+0x68].vt[1]       state int
                     this[+0x70].vt[0x34]    track-bound float ← actual integration leaf
                     this[+0x74].vt[0xC]     gating predicate
                   packs output buffer with all per-frame physics state
```

The actual `pos += vel*dt` integration is **inside `this[+0x70].vt[0x34]`** — that points into EAGL physics middleware code. Not yet named.

**RigidBody construction layer (anchored from prior sessions):**
- `RigidBody_AllocAndInitFromAttributes @ 0x006895a0` — sole caller of `CreateRigidBodyComponent @ 0x00688660`
- `CreateRigidBodyComponent` allocates 0x14C bytes from pool, sets up: SmackTrigger sub-component @ +0xB4, AIParams @ +0xC0, VehicleParamsCluster @ +0xC8
- Mass-properties block at body[+0xE4..+0xF8] (damping=0.125 at +0xEC, 1/mass at +0xF4)
- See `vtbl_pvehicle_ComponentList @ 0x008adcc0` (24-method vtable) and the inline RTTI inventory at `0x008add1c` for the full pvehicle subclass list.

### AI (Goals + Actions)

**Two-layer system**: AIGoals (strategic state — Pursuit, Patrol, Race, Pit, Heli, …) ; AIActions (tactical behaviors — Ram, RoadBlock, Race, Traffic). Both registry-keyed by `BChunkHash_JenkinsMix3(name)`.

**Confirmed AIGoal vtables:**
- `vtbl_AIGoalRacer @ 0x00892720` (+ `vtbl_AIGoalRacer_RTTI @ 0x00892718`)
- `vtbl_AIGoalPit   @ 0x00892f70`
- AIGoalNone uses sub-component pattern at this+0x73C
- AIGoalRacer uses sub-component pattern at this+0x7C4

**Confirmed AIAction vtables:**
- `vtbl_AIAction_base            @ 0x00892b20` (initial vtable)
- `vtbl_AIActionRam              @ 0x00892c88`
- `vtbl_AIActionStaticRoadBlock  @ 0x00892b40`
- `vtbl_AIActionRace             @ 0x00892b30`

**Vtable layout** (4-slot method groups; an action may have multiple groups):
```
+0x00  scalar deleting destructor (varies — class identity)
+0x04  ProcessAIDecisionEvaluation (0x42b070)  COMMON
+0x08  ?? (orphan code at 0x40a6d0)             COMMON
+0x0C  AIAction_BroadcastToChildren (0x42b040)  COMMON
+0x10..  next group (deleting-dtor + same trio)
```

**Common machinery:**
- `LookupAIBehaviorParam(this, "AIActionXxx")` — fetches behavior params from registry
- `ProcessAIDecisionEvaluation` — vt[1] of every AIAction method-group; decides if the action fires this frame
- `AIAction_BroadcastToChildren(this, dt)` — vt[3]; iterates children at this+0xC and calls vt[4]
- `DispatchAIActionByHash`, `PushAIGoalByHash`, `RegisterAIActionInRegistry` (named in prior session)

### Hash (bChunk = Jenkins mix3)

`BChunkHash_JenkinsMix3 @ 0x005cc240` (inner @ 0x005cc090) is **Bob Jenkins's 1996 "hash" function (mix3)** — the ancestor of lookup3.
- Block size: 12 bytes (3×u32 per round)
- State: `a = b = 0x9E3779B9` (golden-ratio constant), `c = initval`
- Seed: `0xABCDEF00`
- Shift sequence: `13/8/13/12/16/5/3/10/15`
- Custom calling convention: pointer in EAX, len/seed/len in ECX/EDX/stack

**Cracked attribute hashes:**
| Hash | Name |
|---|---|
| `0xA6B47FAC` | `"BASE"` (root type-class tag) |
| `0xFB19212F` | `"MOMENT"` (inertia override key) |
| `0xD59062C8` | `"OBJECT_COLLISION"` (impact event, always fires) |
| `0x80B88C1D` | `"VEHICLE_COLLISION"` (impact vs vehicle) |
| `0x2F698829` | `"PLAYER_COLLISION"` (impact vs player) |
| `0x7EBE81C0` | `"WORLD_COLLISION"` (kinematic-only impact) |

**All 5 original mystery hashes cracked**: `0xB5C0DAC8 = AUTO_SIMPLIFY` (wave-6, Smackable LOD threshold), `0xDA5F19F9 = BEHAVIORS` (wave-6, child component list), `0xEE0011E3 = SimplePhysics` (wave-7, Smackable construction flag), `0x360552DA = ExplosionEffect` (wave-7, push-back effect RefSpec), `0x44F1273B = DROPOUT` (wave-7, timed-decay parameter — confirms FUN_0066a0b0 is a drop-out / despawn animator).

### Audio (slot 1 of PerPlayerSubsystemTick)

**Class hierarchy** at .rdata 0x00894cc8..0x00894f70 — 4 derived classes share one base:

| Vtable | Class | Step (vt[2]) | Dtor (vt[1]) |
|---|---|---|---|
| `0x894cc8` | `vtbl_AudioEntity_TypeA` | `AudioEntity_TypeA_Step` (0x47d3c0) | `0x47aa00` |
| `0x894e48` | `vtbl_UIScreenAnimEntity` | `UIScreenAnim_ComputeTransformFromTrackedFng` (0x476690) | `0x47aee0` |
| `0x894e90` | `vtbl_SmoothAudioEntity_With_Promote` | `SmoothEntity_DampedParamInterpStep` (0x4769e0) | `0x47af00` |
| `0x894f70` | `vtbl_AudioEntity_TypeD` | `AudioEntity_TypeD_Step` (0x482ec0) | `0x47b290` |

**Common base methods** (all 4 vtables share):
- vt[0] = `0x468bb0` IsAliveStub (`return 1`)
- vt[3] = `0x4687f0` NoOpStub (empty)
- vt[14] = `0x468800` `PromoteAudioMemHandleToReady`
- vt[17] = `0x468020` GetSubobjectPropPtr (`return *(this+0x1c) + 0x60`)

`SmoothEntity_DampedParamInterpStep` (vt[2] of 0x894e90) does **damped harmonic oscillator interpolation**:
```
envelope = 1 − exp(−t² · k1) · cos((angle + bias) · t² · k2)
for f in {+0x90, +0x94, +0x98, +0x9C, +0xA0}:
    this[+f] = envelope · target[f] + (1 − envelope) · source[f]
Compose3DTransformFromAngles → transform passed to subobject
```

### SmackTrigger (impact event publisher)

`SmackTrigger_OnContactEvent` (now `AIParams_OnContactEvent` 0x006772c0) — vt[2] of `vtbl_AIParams` post-step sub-component.

Algorithm:
1. Validate via parent body's collision predicate (vt[0x74])
2. Compute speed magnitude = sqrt(p[8]² + p[9]² + p[10]²); gate on threshold
3. Determine which side of the contact `this` is on (sim-id match)
4. Pack contact normal + flags + material at fixed offsets
5. Hand off to `RigidBody_DispatchImpactEvent` 0x00669e30 → fires events:
   - `OBJECT_COLLISION` (always)
   - `PLAYER_COLLISION` (vs player physics agent)
   - `VEHICLE_COLLISION` (vs vehicle classification)
   - `WORLD_COLLISION` (kinematic-only)

---

## Modding hook reference

### Where to hook for common tasks

| What you want to do | Hook here |
|---|---|
| Override per-frame physics state for any vehicle | `pvehicle_AggregatePhysicsState @ 0x00694160` (intercept the output buffer) |
| Inject custom entity into per-frame audio/UI loop | Add to a slot list at `0x009195e0 + N*0x70` (slot N+1 head address `0x919624 + N*0x70`) |
| Hook every Present (HUD overlays, frame capture) | `D3D9_PerFrame_PresentAndCheckLost @ 0x006e7220` or detour `[g_pIDirect3DDevice9->vtbl + 0x44]` |
| Hot-reload attributes without restart | Detour `OpenAssetBundleStream @ 0x0065fd30` and re-issue your bundle paths |
| Hook collision events | Subscribe to event hashes 0xD59062C8 / 0x80B88C1D / 0x2F698829 / 0x7EBE81C0 via `RigidBody_PublishEventToSubscribers @ 0x00669d70`'s subscriber registry |
| Capture player input (raw axes) | Walk `input_device_registry_head @ 0x00920464` for "GameDevice" hash; intercept its factory fn |
| Skip CD/disc check (already known modder fix) | NOP at `CheckDiscPresent @ 0x6cbb70` or set the `"foobar"` devmode flag |
| Read CD key | `LoadGameRegistryConfig @ 0x6cb680` reads from HKLM ergc |
| Override AI behavior for a goal | Detour the goal's vt[2] (Tick) — see vtables under AI section |
| Add a new CDAction (driver action) | Register via `bChunk("CDActionXxx")` in the action registry; hook in `Player_SelectActiveActionCard @ 0x00479900` |

### Key globals to read at runtime

```
0x00982bdc   g_pIDirect3DDevice9               IDirect3DDevice9*
0x00982bf4   g_pGameWindowHwnd                 HWND of "GameFrame"
0x00982d14   dinput8_device_root_ptr           IDirectInput8*
0x009885e0   world_root_singleton              World* (NULL when no world loaded)
0x00913e74   active_vehicle_components_arr_a_head    array of audio-wrappers per active vehicle
0x00913e7c   active_vehicle_components_arr_a_count   (typically 6 during single-player race)
0x00919624   slot 0 head of PerPlayerSubsystemTick (audio entity slot 1 list head is at +0x70)
0x00919650   slot 1 BASE (audio entity slot)
0x00925878   asset_stream_node_pool             pool of asset-stream nodes
0x009259a8   asset_stream_list_tail             active asset streams head
0x00925858/c asset_load_pending_count_a/b       both 0 when all loads done
```

### Function-tag inventory (queryable via `GET /search_functions_by_tag?tag=X`)

`Engine` (51) · `AI` (37) · `Physics` (36) · `Streamer` (21) · `Render` (16) · `Input` (14) · `Hash` (11) · `Boot` (5)

---

## Wave-1 subsystem expansion (2026-05-09)

### Gameplay scripting natives
`RegisterScriptNativesGameplay @ 0x0061e750` is the canonical bind table — ~150 C++ natives exposed to the gameplay scripting language (NLT/WLT/SAT). When investigating any in-game event ("where is X awarded?", "who triggers Y?"), find the native name as a string, find its registration line in this function, follow to the implementation. ~30 implementations renamed with `_Impl` suffix (StartRace_Impl @ 0x60dbd0, AwardPlayerBounty_Impl @ 0x612220, AwardPoints_Impl @ 0x60e030, SpawnCop_Impl @ 0x60a670, SetCopsEnabled_Impl @ 0x604f40, ShowPauseMenu_Impl @ 0x6050f0, AbandonRace_Impl @ 0x60deb0, etc.). Many implementations are LABs not full functions; ~36 LAB labels added.

Singleton `g_pGRaceStatus @ 0x91e000` is the script-visible race-state object (registered as "GRaceStatus").

### Replay / Joylog
Two distinct replay layers:
- **Joylog (low-level deterministic capture)**: master switch `g_nJoylogEnabled @ 0x9258c8`. `InitializeJoylogReplayOrCapture @ 0x660530` decides playback (ReplayJoylog.jlg present) vs capture (writes CaptureJoylog.jlg). Buffer is 0x4118 bytes; flags at `g_nJoylogPlaybackActive @ 0x9258d4` / `g_nJoylogCaptureActive @ 0x9258d8`. Sim-step generator `SimTickStepWithJoylogHook @ 0x661280` reads tick counts from the playback buffer or accumulates real-time dt + writes ticks to capture buffer.
- **CarReplay (per-vehicle state)**: GetCarReplaySingleton; `BeginCarReplayRecording @ 0x56c3e0` registers self ("TheHost") plus up to 3 multiplayer clients ("ClientN"). ReplayCameras array @ 0x00895098.

### Particle system
`Particle_And_Emitter_Pools_Initialize @ 0x4ff0a0` allocates three CreateObjectPool slots. Master enable `g_nParticleSystemEnable @ 0x9017ec`.

| Pool | Slot Size | Max | Vtable | Pointer |
|------|-----------|-----|--------|---------|
| ParticleSlotPool      | 0x70 | 1024 | 0x899d94 | 0x916060 |
| EmitterSlotPool       | 0x90 | 500  | 0x899da8 | g_pEmitterSlotPool @ 0x916064 |
| EmitterGroupSlotPool  | 0x80 | 200  | 0x899db8 | g_pEmitterGroupSlotPool @ 0x916068 |

Effect classes: EffectsPlayer/Smackable/Vehicle/Car/Fragment. Shader: `fx\Particles.efx`.

### Audio (expanded)
Four entity types tick under PerPlayerSubsystemTick (slot 1 = audio):

| Class | Role | Vtable global |
|-------|------|---------------|
| AudioEntity_TypeA   | 3D positional sounds                                   | g_pVtableAudioEntityTypeA @ 0x894cc8 |
| AudioEntity_TypeD   | 2D ambient/non-spatial loops                           | g_pVtableAudioEntityTypeD @ 0x894e48 |
| SmoothAudioEntity   | Damped parameter interpolator (RPM, throttle)          | 0x894e90 |
| UIScreenAnimAudio   | UI-screen-anim overlays (front-end clicks/transitions) | 0x894f70 |

Master mixer `g_pNFSMixMaster @ 0x911fa8`. Audio arena `g_pAudioMixerArenaBase @ 0x008ee558` (~5.6 MB, allocated by `InitializeAudioMixer @ 0x4cc3a0`, served by `AllocFromAudioMixerArena @ 0x4ac010`). Banks: CARSFX_TrafficEngine/Skids/Nitrous/Turbo/BottomOut + cop-chatter. Music: MW_Music.mus + MW_Music.mpf.

### Customization (vinyl + parts)
- `VinylLoadPerCarBundle @ 0x75bb40` — loads `CARS\<name>\TEXTURES.BIN`, `VINYLS.BIN` or `PREVINYL.BIN` (chosen by char flag at param+7 and DAT_009b09fc).
- `GetCustomizationPartHashByCategory @ 0x7b5ef0` — validates part-category ID (0x101..0x70b) and hashes "CUSTOMIZATION_%s_%d". Returns 0x9BB9CCC3 sentinel on invalid.

ID groups (high byte): **0x1xx** body kits/spoiler, **0x2xx** engine/drivetrain (PD_ENGINE_%d_%d), **0x3xx** exhaust/nitrous, **0x5xx** suspension/tires, **0x6xx** brakes, **0x7xx** vinyl/paint (VINYL_LAYER0, VINYL_COLOUR0_R/G/B). FNG screens: Showcase.fng, CustomizePerformance.fng.

### Front-end (FNG) UI engine
Hierarchical screen-stack manager keyed on .fng asset names. Globals:
- `g_pUIRootContext @ 0x91cadc` — root context; screen-name ptr @ +0xc, payload @ +0x10/+0x14
- `g_pFrontEndManager @ 0x91cf90` — FE state (flags +0x12C, screen count +0x19c)
- `g_FEMessageHandle @ 0x91ca60` — async message queue handle
- Asset cache `DAT_0091cfc0[120]` — pending FNG-load slots

Anchors:
- `FE_Initialize @ 0x5538e0` — boot path; allocates 0x164-byte CFEManager (`CFEManager_Constructor @ 0x5496a0`)
- `FE_Shutdown @ 0x533460`
- `FE_LoadAssetScreenByName @ 0x571eb0` — async loader, hash-keys 24-bit CRC into 120-slot cache
- `FE_ScreenStateDispatcher @ 0x623f80` — race/menu state machine
- `FE_PauseScreenPush @ 0x62f220` — pushes Pause_Main.fng
- `FE_RaceEventMessageHandler @ 0x58bd10` — localized text from race attributes
- `FE_InputDispatcher @ 0x549460` — controller input → active screen
- `FE_AudioRoutingTableByScreenHash @ 0x4c2340` — 39-entry hash → audio enable/disable per screen
- `FE_PostMessage @ 0x5989b0` — async message post
- `FE_UpdateHUDLayers @ 0x667340` — post-screen-load HUD overlay refresh (FadeScreen.fng + Pause_Main.fng)

### Network / multiplayer
Host-authoritative GameSpy + LAN replay-sync model. Globals:
- `g_nIsNetClient @ 0x9b416c` — 0=host, 1=client (branches the entire session loop)
- `g_dwNetClientVehicleSlots @ 0x9b40f8 [3]` — remote-client vehicle handles (0 = unoccupied)
- `g_nNetSessionState @ 0x9b41fc` — 1 idle / 2 init / 4 racing / 5 post-race / 6 finished
- Game name @ 0x9b4180 (char[64])
- `g_pNetCarReplaySingletonRef @ 0x9b4218`

Anchors:
- `Net_ParseMultiplexerConfigFile @ 0x78a900` — keys ISSERVER, NUMCLIENTCARS, SERVERIP, SERVERPORT, CLIENTIP%d, FORCE CLIENTSHUTDOWN, NetworkDebug, NetworkUserName, LobbyServerAddr/Port
- `Net_SessionInitialize @ 0x7617d0` — state 1→2; calls `Net_QuantizerInitializeAndServerCheck @ 0x7a15d0`
- `Net_ClientReplayHandshake @ 0x7a1310`
- `Net_MultiplayerSessionUpdateLoop @ 0x761b30` — big switch on session state
- `Net_ServerTimeoutCheck @ 0x7a12e0` / `Net_ClientTimeoutCheck @ 0x7a13c0`
- `Net_QuantizerInitialize @ 0x78a220` — m_messageTypeQuantizer + m_driverNumberQuantizer (bandwidth compression)
- `Net_RegisterClientVehicleWithReplay @ 0x78c1d0`, `Net_GetCarReplayFrameState @ 0x78c380`, `Net_GetCarReplayRecordedFrameCount @ 0x78c2a0`
- Event hashes: `GetEventHash_MPlayerEnterPursuit @ 0x626480`, `GetEventHash_MPursuitOver @ 0x626550`

### Allocator architecture
Hierarchical: main heap → 16 sub-pool arenas → named slot pools. Block header (0x14 bytes preceding user_ptr): `prev_block_ptr | next_block_ptr | pool_index | magic 0x22 | alignment_shift | original_size`.

Anchors:
- `Heap_AllocWithArenaRouting @ 0x4653d0` — main heap, routes by size/flags
- `Heap_FreeBlock @ 0x4655f0` — dual-linked free + magic 0x22 validate
- `Heap_InitializeArenaGlobals @ 0x4652a0`
- `CreateObjectPool @ 0x4662e0` — factory (53 callsites)
- `Pool_PopBlock @ 0x465340` — pop with auto-expand
- `Pool_AllocateBlockWithHeader @ 0x465d80`
- `Pool_ReturnBlockToFreeList @ 0x4650a0`
- `Pool_ExpandIfAutoExpandFlagSet @ 0x465de0`
- `Pool_InitializeHeader @ 0x4f5170`
- `SubPool_DestroyMaybeFreeArena @ 0x464e10`
- `Arena_QueryLargestFreeBlock @ 0x464080`
- `DeferredFreeQueue_Process @ 0x6626b0` — drains pending frees during ticks
- `DeferredFreeQueue_AddSize @ 0x627420` — pending bytes counter (DAT_00920394)

Pool inventory (sample): Particle/Emitter/EmitterGroup, AIVehicleSlot 0x14×3072, AIVehicle 0x54×16, VehicleDamagePart 0x70×240, VehiclePartDamageZone 0x18×100, NFSAnimBank, AnimCtrl/AnimPart/AnimSkeleton, World*Anim*, FERender*, eStrip, eAnimTexture, ShadowMapMesh, TexturePack, eLightMaterialPlatInfo, Audio Memory, Speech Event/Cache, ResourceFile, QueuedFile, Ecstacy:Model, vertexBufferHeader/textureHeader, EAGL4Anim Memory, EAGL4::SymbolPool, LanguageMemoryPool.

### World streamer + AI path graph
Region-grid streaming with three parallel pipelines:
- **InGame bundles**: InGameA.BUN, InGameB.LZC, optional InGameSplitScreen.BUN
- **Track bundles**: TRACKS\<name>.BUN on-demand
- **Spline curve cache**: `EnsureSplineCurveCacheReady @ 0x794f80` (Catmull-Rom-ish, 6 nodes × 8 bytes)

`DispatchRegionLoaderHandler @ 0x666aa0` orchestrates all three. Hash keys: 0x1974ff09 (InGame), 0xcda340f8 (Track), 0xeff164cb (exit), 0x98667b3e (state push).

AI path graph: 6-byte nodes at `DAT_009a3a64`, accessed via `GetAITrackPathSegmentPtr @ 0x723c90` (returns base + idx*6). Road network singleton: WRoadNetwork @ 0x8b5df0. World origin defaults at DAT_008a2fb4/8/c.

AI path follower state (~0x40 bytes):
```
+0x10 : current pos (3×float)
+0x1c : current segment idx
+0x20 : target pos (3×float)
+0x2c : active flag
+0x30 : velocity vec (3×float)
+0x3c : speed magnitude
```

Other anchors: `LoadGlobalAssetsBlocking_GLOBALA @ 0x662b30`, `NextRegionTransition @ 0x666390`, `ProbeRegionContainsKey @ 0x6661d0` (sentinel `-0x64ca01c6` = miss), `ResetAIPathFollowerState @ 0x409e60`, `GetTrackStreamerSingleton @ 0x79ca30`, `CreateAIActionRace @ 0x43b800`, `CreateAIActionStaticRoadBlock @ 0x43be50`, `CreateAIActionRam @ 0x43ba28`, `UpdateAIActionRam @ 0x43bb28`.

### Damage subsystem
Class hierarchy (strings): **DamageVehicle** @ 0x8ad648 (base), **DamageRacer** @ 0x8adda0, **DamageCopCar** @ 0x8addb8. Configuration: `damagespecs` @ 0x8add38.

Per-vehicle init: `Vehicle_DamageInitConstructor @ 0x6b9920` (THISCALL) — registers DamageVehicle ptr at this+0x4c, plus 5 damage-event slots at +0x50/+0x54/+0x58/+0x5c/+0x60.

Damage state struct (vehicle + offsets) — flag pointers stored via `Damage_StoreVehiclePartFlags @ 0x756e90` into mission-flag table at `DAT_009b26a8`:
```
+0x100 DAMAGE0_FRONT       +0x10C DAMAGE0_REAR
+0x104 DAMAGE0_FRONTLEFT   +0x110 DAMAGE0_REARLEFT
+0x108 DAMAGE0_FRONTRIGHT  +0x114 DAMAGE0_REARRIGHT
+0x168/16C/170/174  DECAL_*_DOOR/QUARTER_*
```

Per-part deformation lookup: `bChunk("KIT%02d_DAMAGE0_<part>")` → mission flag → mesh blend amount.

Pools (`Damage_InitializePartZonePools @ 0x73eb20`): VehicleDamagePartSlotPool 0x70×240 @ DAT_009b0a78, VehiclePartDamageZoneSlotPool 0x18×100 @ DAT_009b0a7c.

Events: `MNotifyEngineBlown` @ 0x8a6b24 (`GetMessageHashEngineBlown @ 0x621a2a` cache pattern), EEngineBlown @ 0x8a6b54, ETireBlown @ 0x8a7664. Cop-RAM: `CreateAIActionRam @ 0x43ba28`, `UpdateAIActionRam @ 0x43bb28` applies `DamageMultiplier × ImpactSpeed^2`. AIActionTooDamaged flag @ 0x892c00.

`GetDamageParamsHash @ 0x668850` — Jenkins-mix3("DamageParams") seeds the data-driven damage table.

### Input action layer (CDAction, expanded)
Flow: **DInput8 raw → 200-slot binding registry → game-action enum → AI/PlayerCar shared controller**.

**Wave-8 fully mapped the real binding system**: 76-row master action template at `0x008f6d80` (stride `0x34` = 13 dwords; row index IS the action ID; 4 slots per row, each `{type, control, sub}`). Per-frame poll: `PollAllGameActionBindingsPerFrame @ 0x6349b0` iterates all 76×4 slots and writes max-aggregate axis floats to `controller[+0x20][R]`. Slot reader: `ReadGameActionBindingAxisFromDevice @ 0x628940`. Runtime mirror at `DAT_0091f418` (copied by `CopyGameActionBindingTemplateToRuntime @ 0x628410`).

GAMEBREAKER = action ID **1** (row 1, base `0x008f6e84`). Default keys: slot 0 = `0x9d` (DIK_RCONTROL), slot 1 = `0x22` (DIK_G). The prior "action_id 0x9d / key SC_E 0x22" claim was a misreading — `0x9d` is the DInput scan code (key), not the action ID; `0x22` is `DIK_G`, not `SC_E`. The table is interleaved `GAME_ACTION_*` / `HUDACTION_*` / `FE_ACTION_*` — one unified action-ID space.

Profile reads: `GetUIInputProfileSlot @ 0x56f100`, `GetUIInputProfileFloatField @ 0x56f7b0`. Mode toggles: `SetUIInputModeFlag @ 0x572e80`, `GetUIInputModeFlag @ 0x575b00`. Rebind UI: `DetectGameActionRebindFromDeviceEvent @ 0x634490`, `InstallGameActionBindingIntoSlot @ 0x6285f0`. Replay-log replacement: `ApplyGameActionRebindFromReplayLog @ 0x634900`. Display name formatter: `FormatGameActionBindingDisplayName @ 0x6280c0` (uses `IDirectInputDevice8::GetObjectInfo`).

Still TBD: the publisher that reads `controller[+0x20][R]` axis crossings and emits hashed events onto bus `DAT_0091e0d0`.

~~`LookupUIInputBindingByCode @ 0x56ecc0`~~ — that function is actually `FEPlayerCarDB_GetCarRecordByHandle` (200-slot × 0x14 byte FECarRecord pool, NOT input bindings).

Game-action enum (GAMEACTION_*): GAS, BRAKE, HANDBRAKE, STEERLEFT, STEERRIGHT, TURNLEFT, TURNRIGHT, SHIFTUP, SHIFTDOWN, NOS, GAMEBREAKER, RESET, FORWARD, BACK, JUMP, CAM_LOOKBACK.

Controller bridge: `ConstructAISteeringController @ 0x77b9e0` — 3 input register blocks at +0x5c/+0x78/+0x94 (0x50 bytes each). The same machinery serves AI **and** player; the difference is only who fills the registers.

---

## Wave-5 subsystem expansion (2026-05-14)

After integrating berkayylmao's [NFSPluginSDK](https://github.com/berkayylmao/NFSPluginSDK) (181 hardcoded addresses + 65 enums + 245 structs + 178 type headers — see `docs/sdk_*.json`), 8 parallel subagents mapped the remaining major subsystems in ~25 wall-clock minutes. Key additions:

### Script VM = **vanilla Lua 5.0.2** (confirmed)
The "Lua-like custom stack machine" hypothesized in earlier sessions is actually **literal Lua 5.0.2**, byte-identical error strings (`"binary string"`, `` "`for' initial value must be a number" ``). All 35 opcodes mapped, jump table @ `0x60fbbc`.

Key entries:
- `ExecuteLuaVMOpcodes @ 0x60e9d0` = **luaV_execute** (main dispatch)
- `CallLuaScriptFunctionD @ 0x6126a0` = **luaD_call**
- `PrecallLuaFunctionFrame @ 0x60e7d0` = **luaD_precall**
- `HandleLuaReturnFromFrame @ 0x606d50` = **luaD_poscall**
- `ResumeLuaCoroutineState @ 0x6150e0` = **lua_resume**
- `SuspendLuaCoroutineYield @ 0x6138b0` = **lua_yield**
- `HandleLuaCallHookEntry @ 0x606c20` / `HandleLuaTraceexecHook @ 0x607f20` (hook entries)
- `CloseLuaOpenUpvaluesUpTo @ 0x60b9d0` (luaF_close)

**Twist**: this build flips POS_A to the high bits (canonical Lua 5.0 has `POS_A=6`; this build has it at 24). Opcodes & semantics unchanged. The "Run"/"Suspend" gameplay natives @ 0x6048d0/0x6048e0 are **NOT** coroutine primitives — they manipulate gameplay "Activity" objects.

### Race rules engine
**Mode enum (11 values)** from PTR_s_circuit_008f5cd8:
```
0 = p2p (sprint)
1 = circuit
2 = drag
3 = knockout
4 = tollbooth
5 = speedtrap
6 = checkpointrace
7 = cashgrab
8 = challenge
9 = speedtrapjump
10 = milestonejump
```

Dispatch is **switch-based, not vtable-based**. 112 xrefs to `GetEventRaceModeId @ 0x5faa20`. Per-mode rule sites scattered across notify-handlers and UI helpers.

Key globals: lap times at `GRaceStatus+0x19BC`, checkpoint times at `GRaceStatus+0x1C3C` (3D float table `[event][racer][cp]` stride 4).

**MW does NOT ship with Drift mode** — `drift` at 0x89abcc is leftover Underground-era localization, NOT in the mode enum.

### AI Racer (non-cop)
- `vtbl_AIVehicleRacer @ 0x892ad0` (class size 0x7EC) — per-frame tick @ `0x42f140`
- `vtbl_AIGoalRacer @ 0x892720` (class size 0x7CC) — per-frame tick @ `0x42aa80`
- `ComputeRacerRubberBandTargetSpeed @ 0x5ff990` — the rubber-band core
- `GetRacerDifficultyBucketFromAttribs @ 0x5fac10` — 3 buckets via attribute hash `0x88a7e3be`, thresholds `< 0x22 / 0x22..0x42 / > 0x42`

**No drafting code exists.** **AI does NOT use nitrous** (zero xrefs to `EPlayerTriggeredNOS`). Catch-up is purely rubber-band speed multiplier driven by `g_pGRaceStatus+0x4484` (per-race gain) × `DAT_008a37d8 = {0.0, 0.5, 1.0}` (difficulty mult) × ramp tables at `0x8f5b58..0x8f5b94`.

### Save/Load = **MD5** trailer (not CRC)
Path: `%USERPROFILE%\Documents\NFS Most Wanted\<PlayerName>` (no extension; PS2 MemoryCard-style entry preserved). ~63KB file ending in a **16-byte MD5 digest** of the preceding payload.

Confirmed MD5 by:
- IV constants `A=0x67452301, B=0xefcdab89, C=0x98badcfe, D=0x10325476` at `ComputeMd5OfSaveBuffer @ 0x57f920`
- Canonical RFC-1321 T-table at `Md5CompressBlock @ 0x650410`

Key entries:
- `WriteProfileToFile @ 0x5188f0` (top-level save trigger)
- `BuildProfileSaveBuffer @ 0x58fd10` (~63KB layout assembler)
- `CheckShouldAutosaveNow @ 0x5184d0` (per-tick + post-race trigger)
- `LoadProfileFromFile @ 0x5268b0`
- `EnsureProfileDirectoryExists @ 0x6cbf00` (SHGetFolderPathA → CreateDirectoryA)

**`MSG_R_BI_DATACRC @ 0x8b6b7c` is NOT save CRC** — verified to be an orphan netcode-table string sitting next to MSG_R_SC_RESTARTLOAD with zero code xrefs.

### Cutscenes = **On2 VP6 + MAD audio** (NOT Bink)
Statically linked, no binkw32.dll import. Verified via `VP6_CODEC_INTERNAL::*` strings at 0x8c27e8 and the EA SCHl/MVhd container magic (`MV0K` = 0x4d56304b is keyframe). On-disk extension `.vp6`.

- `g_pMoviePlayerSingleton @ 0x91cb10` (328 bytes)
- `ProcessMovieOpenAndBegin @ 0x542a40` (top-level entry — opens .vp6, inits codecs)
- `ProcessMoviePlayerPerFrameTick @ 0x525f70`
- 38-entry **path→flags** table @ `0x008f3818` covering: 15 blacklist intros, 13 storyfmv, 6 tutorials, ealogo/psa/intro/attract
- `g_dwSkipMoviesFlag @ 0x926144` toggled by `multiplex.cfg SKIPMOVIES=1`
- Movie-finished event hash: `0xc3960eb9`

**No real-time engine cutscenes** in MW — all cinematics are pre-rendered .vp6 FMV. Blacklist character names live in `LANGUAGES\ENGLISH.BIN` under `BLACKLIST_RIVAL_%02d_NAME`, NOT in speed.exe.

### EA Trax music = **two systems**
1. **Interactive in-race score**: `MW_Music.mus` (sequence) + `MW_Music.mpf` (pattern/transition). Driven by hashed events `Pathfinder5`, `Event`, `PartUpdate`, `Swap`, `InteractiveDone`. Stem rotation 4-slot seeded in ctor.
2. **Licensed EA Trax**: streamed via **EAXS_StreamManager** (proprietary; allocator stub creates 0x24-byte voice wrappers via vtable `PTR_FUN_00896ae8`). Per-track filename from attribute sub-field `0x58f80e5e`.

Playlist data @ `g_pSaveOptions+0x324` (0x108 bytes, ~33 entries × 8). Per-entry `mode`: 0=OFF, 1=FE-only, 2=IG-only, 3=AL (both). Mode flag for whole jukebox: `+0x7c` (0=Interactive, 1=EA Trax).

Track metadata schema (20 bytes/entry, in `g_pMusicTrackDBBegin..End`):
```
+0x00 const char* title
+0x04 const char* artist
+0x08 const char* defaultMode  ("FE" | "IG" | "AL")
+0x0c const char* filename     (from sub-attr 0x58f80e5e)
+0x10 u32         flagsOrDur
```

Volume duck queue @ `g_abAudioVolumeFadeSlots @ 0x91d928` — 63 × 12-byte slots. Music duck uses type=2. Cop chatter slot 5 sets controller+0xac |= 0x20000 and triggers a duck fade.

### SpeedBreaker = "GameBreaker" internally
- Time-scale field: `world_root+0x24` (float, 1.0=normal, drops during active)
- Scaled dt stored at `world_root+0x1c = (+0x24)*(+0x18)`
- Strategy slot @ `world_root+0x38` — controller installed during activation
- Input: action ID **1** (row 1 of 76-row template @ `0x008f6d80`); row at `0x008f6e84` has default keys `0x9d` (DIK_RCONTROL) + `0x22` (DIK_G)
- Entry script native: `"StartBreaker"` (script-side; C++ binding TBD)
- HUD widget: `ConstructHudSpeedBreakerMeter @ 0x59e420`

**dt-scale coverage**:
- **Scaled**: EAGL physics integrator, AI tick, particle bus, animation bus
- **NOT scaled**: HUD/UI animator, audio mixer, render/Present, network session loop

**Important disambiguation**: "GameBreaker" (slow-mo / signature mechanic) ≠ "PursuitBreaker" (environmental cop-stop trigger, a completely different system).

### HUD rendering
28 named widgets (`Hud_Speedometer`, `Hud_Tachometer`, `Hud_Minimap`, `Hud_HeatMeter`, `Hud_BustedMeter`, `Hud_GetAwayMeter`, `Hud_NitrousGauge`, `Hud_SpeedBreakerMeter`, `Hud_Infractions`, `Hud_PursuitBoard`, `Hud_MilestoneBoard`, `Hud_TurboMeter`, `Hud_Countdown`, `Hud_LeaderBoard`, `Hud_RaceInformation`, `Hud_ShiftUpdater`, `Hud_TimeExtension`, `Hud_DragTachometer`, `Hud_EngineTempGauge`, `Hud_RadarDetector`, `Hud_MenuZoneTrigger`, `Hud_CostToState`, `Hud_Reputation`, `Hud_WrongWayIndicator`, `Hud_GenericMessage`, `Hud_RaceOverMessage`).

**UPDATED 2026-05-15 (wave-11/12/13/14)**: HUD widget vtable is **2-slot only** (slot[0]=dtor, slot[1]=Update — NOT slot[3] as earlier waves assumed). The per-frame walker is **`CHudWidgetArray_Tick @ 0x58ca30`** (vt[1] of CHudWidgetArray vtable at `0x008a2538`). The walker is **inline, not a loop** — iterates 11 hardcoded slots on CHudWidgetArray at fixed offsets:

```c
widget = *(int**)(this + offset);  // for offset in 0x2dc..0x32c
if (widget && ((widget[6] & widget[8]) || (widget[7] & widget[9])))
    (*widget->vt[1])();  // call Update if mode-filter passes
```

Slot at `+0x314` has **no mode-filter** — always called unconditionally. Currently empty in retail; clean asi-hook point.

**24-widget storage layout** (cross-referenced from `CHudWidgetArray_Ctor @ 0x5a6600`):

| Offset | Widget | Walker-ticked? |
|---|---|---|
| `+0x2c0` | Speedometer | ❌ |
| `+0x2c4` | Tachometer | ❌ |
| `+0x2c8` | DragTachometer | ❌ |
| `+0x2cc` | ShiftUpdater | ❌ |
| `+0x2d0` | CostToState | ❌ |
| `+0x2d4` | Reputation | ❌ |
| `+0x2d8` | HeatMeterInRace | ❌ |
| `+0x2dc` | TurboMeter | **✅** |
| `+0x2e0` | EngineTempGauge | **✅** |
| `+0x2e4` | NitrousGauge | ❌ |
| `+0x2e8` | SpeedBreakerMeter | **✅** |
| `+0x2ec` | RaceOverMessage | **✅** |
| `+0x2f0` | GenericMessage | **✅** |
| `+0x2fc` | LeaderBoard | ❌ |
| `+0x300` | PursuitBoardInRace | ❌ |
| `+0x304` | MilestoneBoard | ❌ |
| `+0x308` | BustedMeter | ❌ (passive — Update is no-op) |
| `+0x30c` | TimeExtension | ❌ |
| `+0x310` | WrongWayIndi | **✅** |
| `+0x314` | (empty) | **✅** always |
| `+0x318` | Countdown | **✅** |
| `+0x31c` | RadarDetector | **✅** |
| `+0x324` | GetAwayMeter | ❌ (stub Update) |
| `+0x328` | MenuZoneTrigger | **✅** |
| `+0x32c` | Infractions | **✅** |

Non-walker widgets update via **FNG event bus** (`PostUIEventToNamedNode` on UI root `DAT_0091cadc`) — node-handler-driven, not per-frame ticked.

Per-widget Update addresses (waves 8/11/12 mapped):

| Widget | Update fn | Data source |
|---|---|---|
| Hud_Speedometer | `0x57a540` | MPH/KPH attribs → SPEED_DIGIT_* + 3rdPersonSpeedUnits |
| Hud_Tachometer | `0x57a6e0` | RPM @ this+0x54 → 3rdPersonNeedle rotation |
| Hud_DragTachometer | `0x57d130` | RPM_fill bar + needle rotation |
| Hud_EngineTempGauge | `0x5685e0` | temp @ this+0x38 → ENGINE_HEAT_ICON_GROUP swap |
| Hud_ShiftUpdater | `0x569780` | state @ this+0x50 → Pulse{Blue,Green,Red} on Shift_light |
| Hud_Minimap | `0x59db50` + cops `0x531060` + cop-icon `0x595af0` | IVehicle handle + atan2 → TRACK_MAP%d |
| Hud_WrongWIndi | `0x568800` | timer vs DAT_00925ae8 → WRONGWAYIMAGE toggle |
| Hud_MilestoneBoard | `0x57ae30` (setter) | per-icon value setter |
| Hud_LeaderBoard | `0x568950` (setter) | 4-entry table LBData_%d / LeaderText_%d |
| Hud_RaceInformation | `0x5a2ad0` | speed-trap → SPEEDTRAP_SPEED + BOUNTY_TEXT |
| Hud_HeatMeter | `0x7a5aa0` | 10× HEAT_BASE_LED_%d state hashes + HEAT_X%.0f |
| Hud_PursuitBoard | `0x52e0c0` + `0x546a50` + `0x52d640` | CAR_USED_%d / BOUNTY_%d / PURSUIT_ID_%d |
| Hud_GetAwayMeter | stub @ `0x565b10` | caches Getaway_Distance_Bar (driven externally) |

15 widgets still un-traced (Hud_BustedMeter, Hud_NitrousGauge, Hud_TurboMeter, Hud_SpeedBreakerMeter, Hud_Reputation, Hud_CostToState, Hud_TimeExtension, Hud_Coundown, Hud_Infractions, Hud_RadarDetector, Hud_MenuZoneTrigger, Hud_GenericMessage, Hud_RaceOverMessage). Their in-race binders live behind the still-unmapped widget-array-initializer parent function — runtime memory-breakpoint on widget-name strings is the next step.

**CORRECTION**: `ProcessUIOrHUDElements @ 0x504d00` is NOT the HUD dispatcher (misnamed historically). It only runs `ProcessAnimationInterpolation`, `UpdateWorldCamerasAndViewport`, an animation timer, and a flag toggle.

FNG screens used: `HUD_SingleRace.fng`, `HUD_Drag.fng`, `HUD_Player1.fng`, `HUD_Player2.fng`, `HUD_Drag_Player1.fng`, `HUD_Drag_Player2.fng`, `CustomHUD.fng`, `CustomHUDColor.fng`, `Pause_Main.fng`, `FadeScreen.fng`.

Globals: `g_pUIRootContext @ 0x91cadc`, `g_pFrontEndManager @ 0x91cf90` (+300 = HUD flags), FNG-handler table `0x008f4320..0x008f4500`, HUD widget-name table `0x008a27cc..0x008a2994`. PursuitBountyAwarded event hash `0x20d60dbf` has 65 listeners registered via `RegisterPursuitBountyEventListeners @ 0x648590` — **all 65 are audio callbacks** via NFSMixMaster command queue DAT_0091e0d0 (wave-8 verified by decompiling 12 of 65 spanning the range; NOT HUD updaters as previously suspected).

### NFSPluginSDK integration
The berkayylmao/NFSPluginSDK BSD-3 plugin SDK was integrated this wave. From it we extracted and applied:
- **181 hardcoded addresses**: 28 global variables + 153 functions
- **65 enums** (CarType / DriverClass / eFEGameModes / ePursuitStatus / ePostRaceOptions / etc.) → 53 successfully created in Ghidra type DB
- **245 structs** (PVehicle, RBVehicle, AIVehicle, AIPursuit, GRaceStatus, FECustomizationRecord, AICopManager, etc.) → 137 successfully created in Ghidra
- **178 type headers** mirrored locally at `docs/nfsplugin_sdk_mw05/`

136 SDK-derived names were live-applied to Ghidra; 33 of those required `create_function` first (vtable thunks Ghidra hadn't auto-discovered).

Validations from SDK that confirm prior RE:
- `TheGameFlowManager @ 0x925E90` (GameFlowState enum) — matches our DAT_00925e90 game-state global
- `TheOneCopManager @ 0x90D5F4` (AICopManager*) — matches our cop AI pool
- `IsInNIS @ 0x91606C` — Non-Interactive Sequence (cutscene) flag
- `Attrib::StringToKey @ 0x454640` — the Jenkins mix3 hash function we'd already cracked
- `Attrib::FindCollection @ 0x455FD0` — attributes.bin row lookup

---

## Known unsolved threads

1. **EAGL physics integrator algorithm**: `this[+0x70].vt[0x34]` returns post-integrated position. Implementation lives in EAGL middleware code; not yet identified.
2. **Per-frame Input poll site**: Direct `IDirectInputDevice8::GetDeviceState` call site in speed.exe code not pinned (likely behind the device-registry hash dispatch).
3. **All 5 original mystery hashes now cracked** (wave-7 via community wordlists): `0xB5C0DAC8 = AUTO_SIMPLIFY`, `0xDA5F19F9 = BEHAVIORS`, `0xEE0011E3 = SimplePhysics`, `0x360552DA = ExplosionEffect`, `0x44F1273B = DROPOUT`. 51 of 345 attribute *names* still uncracked overall (14.8%). Verified cracked count: **294/345 = 85.2%**. See `docs/attribute_cracks_verified.json` for the authoritative list.
4. **Most slot types** (0, 2, 4-22 of PerPlayerSubsystemTick): never observed populated in our test sessions; likely for entity types that need specific game states.
5. **EZ Wheel Wrapper hot-patch**: the bundled `app/DSOUND.dll` modifies vtable `0x00894cc8`'s vt[2] to `0xffffffff` at runtime, causing an engine crash post-race. This is the wrapper's bug, not ours.
6. **True input-binding lookup**: 0x56ecc0 is *not* it (see correction above). The actual DInput device-code → action-enum function is unmapped.
7. **HUD per-widget update functions**: widget-name strings have no callers in `.text` (only destructor cleanup funclets). Needs runtime breakpoint on widget-name string address.
8. **SpeedBreaker energy / cooldown globals**: time-scale found, recharge timer not yet located.
9. **Lua bytecode disassembly**: shipped `.luac` files in bundles not yet disassembled (would need a Lua 5.0 build patched to match this binary's flipped POS_A encoding).
10. **GameSpy revival**: all online code is reachable but the GameSpy service is shut down (2014). OpenSpy-style reimpl is community-feasible but out of scope here.

---

## Memory entries (for future-me)

40 markdown files in `~/.claude/projects/.../memory/` together form the working knowledge base. Listed below grouped by topic with the wave that produced them.

### Reference
| Entry | Topic |
|---|---|
| `reference_ghidra_mcp_docs.md` | Ghidra MCP plugin reference (193 endpoints @ v5.7.1) |
| `reference_nfsplugin_sdk.md` | berkayylmao's SDK: 181 hardcoded addresses, 65 enums, 245 structs |

### Engine / runtime
| Entry | Topic | Wave |
|---|---|---|
| `project_bchunk_hash.md` | Jenkins mix3 algorithm (seed 0xABCDEF00) | early |
| `project_jdlz_format.md` | NFSMW JDLZ v0x02 decompressor RE'd from 0x64db40 | early |
| `project_attribute_schema.md` | attributes.bin row format (16-byte rows from 0x18000) | early |
| `project_perframe_call_chain.md` | Per-frame execution graph | early |
| `project_runtime_trace.md` | 6+ live debugger sessions consolidated | early |
| `project_pvehicle_inventory.md` | pvehicle subclass inventory (RTTI list at 0x008add1c) | early |
| `project_allocator_architecture.md` | Heap → arena → pool layers | wave-1 |
| `project_streamer_anchors.md` | BUN/LZC streamer central API | early |
| `project_world_streamer.md` | Region-grid + AI path graph | wave-1 |
| `project_eagl_physics.md` | Worker-thread integrator behind runtime-bound vtable | wave-3 |

### Rendering / D3D9
| Entry | Topic | Wave |
|---|---|---|
| `project_render_pipeline.md` | D3D9 boot path + vtable slot table | early |
| `project_render_pass_pipeline.md` | Per-frame pass order (Clear→Shadow→World→Post→Present) | wave-3 |
| `project_animation_runtime.md` | EAGL4Anim + TickableBus dispatcher | wave-4 |
| `project_particle_system.md` | Particle/Emitter/EmitterGroup pools | wave-1 |
| `project_hud_rendering.md` | 28 HUD widgets; 13 update fns mapped (wave-8); tick-driven (not event-bus) | wave-5 + wave-8 |

### Audio
| Entry | Topic | Wave |
|---|---|---|
| `project_audio_subsystem.md` | Four audio entity classes + arena | wave-1 |
| `project_eatrax_music.md` | EA Trax (interactive + licensed); volume duck queue | **wave-5** |

### AI
| Entry | Topic | Wave |
|---|---|---|
| `project_ai_architecture.md` | AIGoal / AIAction hierarchy | early |
| `project_cop_ai_pursuit.md` | Goal-stack cop AI; SetAICopPursuitGoal | wave-3 |
| `project_ai_racer.md` | Racer AI (no drafting, no AI nitrous, rubber-band only) | **wave-5** |

### Gameplay systems
| Entry | Topic | Wave |
|---|---|---|
| `project_career_milestones.md` | Race-end → notify → event-broadcast model | wave-4 |
| `project_race_rules.md` | 11-value mode enum; Drift confirmed absent | **wave-5** |
| `project_speedbreaker.md` | GameBreaker (NOT PursuitBreaker); time-scale @ world_root+0x24 | **wave-5** |
| `project_damage_subsystem.md` | Mission-flag-driven damage state | wave-1 |
| `project_customization_system.md` | Vinyl + part-category dispatcher | wave-1 |

### Scripting / scripting natives
| Entry | Topic | Wave |
|---|---|---|
| `project_script_vm.md` | **Vanilla Lua 5.0.2**; 35-opcode dispatch table | **wave-5** |
| `project_script_natives.md` | ~150 C++ natives registered via lua_register | wave-1 |

### I/O / persistence
| Entry | Topic | Wave |
|---|---|---|
| `project_save_load.md` | MD5 trailer (not CRC); Documents\NFS Most Wanted\<player> | **wave-5** |
| `project_cutscene_system.md` | On2 VP6 + MAD audio (NOT Bink); EA SCHl/MVhd container | **wave-5** |
| `project_replay_subsystem.md` | Joylog + CarReplay deterministic capture | wave-1 |

### Input / UI
| Entry | Topic | Wave |
|---|---|---|
| `project_input_subsystem.md` | DInput8 + FF + CDAction layer | early |
| `project_input_action_layer.md` | DInput8 → action enum (0x56ecc0 false claim corrected wave-5) | wave-1 |
| `project_fe_engine.md` | FNG screen-stack engine | wave-1 |

### Network
| Entry | Topic | Wave |
|---|---|---|
| `project_network_subsystem.md` | GameSpy + LAN replay-sync model (service is dead since 2014) | wave-1 |

### Feedback / process
| Entry | Topic |
|---|---|
| `feedback_subagents_for_ghidra.md` | Subagent gotcha (program-switch must be first call) |
| `feedback_v571_features.md` | v5.7.1 function-tag/set_global conventions |
| `feedback_objdump_when_ghidra_offline.md` | objdump fallback when MCP bridge is broken |

---

*Compiled 2026-05-09 — 2026-05-14 over a multi-day reverse-engineering session using bethington/ghidra-mcp v5.7.1, gdb 17.1, NFSPluginSDK by berkayylmao (BSD-3), and live debugger attaches to speed.exe under Wine 11.7. 8 parallel subagents (wave-5) cumulatively contributed ~120 renames + 8 fresh memory entries in 25 wall-clock minutes.*
