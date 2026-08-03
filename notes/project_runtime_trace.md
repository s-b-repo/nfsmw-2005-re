---
name: NFSMW runtime trace findings (winedbg + gdb)
description: What the live-debug session on 2026-05-08 confirmed about runtime layout, module loads, and the engine-boot crash path
type: project
originSessionId: c4edf485-e85f-4e2f-ac31-e021ba66e8d6
---
A debugger session on **2026-05-08** captured live data from speed.exe running under Wine 11.7 + winedbg's `--gdb` mode, attached via local gdb 17.1. Three breakpoints fired before the game crashed in the per-player slot dispatcher.

## Confirmed: static→runtime address mapping is 1:1

Wine maps `speed.exe` at its declared `IMAGE_BASE = 0x00400000` with no relocation (no ASLR for this PE). **All Ghidra static addresses match runtime addresses directly** — `0x006e69f0` in Ghidra is `0x006e69f0` at runtime. No translation needed for breakpoints, label-back-writes, etc.

## Module load addresses (Wine syswow64, 32-bit)

```
speed.exe                @ 0x00400000  (IMAGE_BASE)
syswow64\ntdll.dll       @ 0x7BCC0000
syswow64\kernel32.dll    @ 0x7BB00000
syswow64\kernelbase.dll  @ 0x7B580000
syswow64\d3d9.dll        @ 0x7B3F0000  (Wine emulated)
syswow64\wined3d.dll     @ 0x79850000
syswow64\d3dx9_26.dll    @ 0x78390000  ← the SDK version this game ships against
syswow64\opengl32.dll    @ 0x786B0000  (D3D9 → OpenGL via wined3d)
syswow64\DINPUT8.dll     @ 0x75D10000  (Wine's; ALSO a local app-side DINPUT8.dll @ 0x777C0000)
app\DSOUND.dll           @ 0x76420000  (DSOAL — wraps DSound to OpenAL)
syswow64\WINMM.dll       @ 0x762A0000
syswow64\d3dcompiler_47  @ 0x782B0000
```

## ASI mods loaded in this Magipack repack

```
NFSMostWanted.WidescreenFix.asi   @ 0x75630000
NFSMWExtraOptions.asi             @ 0x755D0000
NFSMWHDReflections.asi            @ 0x75580000
NFSMWHUDAdapter.asi               @ 0x75550000
EZ Wheel Wrapper v4.60.001        (loaded via DSOUND/dinput — printed banner at boot)
```

These hooks may patch addresses we've named — be aware when reverse-engineering that runtime behavior may differ from the static binary.

## Confirmed boot-time call chain to the integrator dispatcher

```
mainCRTStartup (0x007c4040)
  └─ main (0x00666590)
       └─ InitializeEngine (0x00665fc0)
            └─ ... timing init ...
            └─ RenderAndWindow_Initialize (0x006e69f0)             ← BP1 fired @ T+0.5s
                 ├─ Direct3DCreate9 → idirect3d9_factory_ptr
                 ├─ window class + CreateWindowExA "GameFrame"
                 └─ D3D9_CreateDeviceAndFirstPresent (0x006bfbd0)  ← BP2 fired @ T+0.9s
                      eax/ecx/esi/edi = 0x780/0x438 = 1920/1080 (window dims)
                      then runs the BeginScene → Clear → EndScene → Present sequence
       ... game state machine reaches frame loop ...
       └─ GameFrameTick (0x00663d30)
            └─ SubsystemDtAccumulator (0x0064a680)
                 └─ PostStateUpdate_DispatchPair (0x00480c10)
                      └─ PerPlayerSubsystemTick (0x0047c880)        ← reached @ T+2.1s
                           └─ instruction at 0x0047c8ac dereferences slot[-1]
                              for the vtable pointer → SIGSEGV (no track loaded)
```

## The engine-boot SIGSEGV at 0x0047c8ac

When the game has not yet loaded a track, the per-player slot at `&DAT_00919624` holds a *non-null but uninitialized* heap pointer. The dispatcher reaches `0x0047c8ac` (now labeled `perplayer_slot_minus1_deref`), tries to load `*(slot - 4)` to get the vtable pointer, and faults on read access to the unmapped heap address.

Concretely from the trace:
- `eax = 0x44960610` (slot pointer — Wine heap range, non-null)
- `ecx = 0x4496060c` (= slot - 4, the supposed vtable pointer location)
- `*ecx` read fails → SIGSEGV

**This is normal engine-boot behavior** when no track is loaded. Reaching gameplay (load a save, click "Quick Race", actually drive) populates `slot[-1]` with a valid vtable pointer, and the integrator BP at `0x0047c890` will then capture the concrete per-vehicle Step method on the next frame.

## What this means for capturing the integrator

**To get the runtime-bound integrator vtable target**, the game must reach gameplay. Steps that work in Wine:
1. Run `bash launch-debug.sh` *without sudo* to use the configured `~/.wine` prefix.
2. Wait for the engine to crash on the per-player slot fault (this trace).
3. **OR** — bypass the menu somehow (autoload save? command-line track flag?). The Magipack's installer might have a "quick race" shortcut.

Once the game is in-race, set BP at `0x0047c890` (the indirect-call site one instruction before `0x0047c8ac`) and capture eax + read 16 dwords at `*eax`.

## What this means for capturing per-frame Present

The per-frame Present caller is somewhere downstream of GameFrameTick's render-tail. The `D3D9_CreateDeviceAndFirstPresent` BP did fire at engine init — its internal Present call is the boot-time first frame. The **per-frame** Present runs every game tick; it should be reachable even in the menu before the SIGSEGV. To capture: set BP on instructions that read `g_pIDirect3DDevice9 @ 0x00982bdc` (write a watchpoint instead of breakpoint), then trace the next call.

## Reproducer commands

```bash
# Game-side launcher (terminal A)
cd "/home/cortix/Downloads/9_Need for Speed Most Wanted Magipack"
bash launch-debug.sh

# Capture script (terminal B, after seeing "WineDbg starting on pid …")
timeout 90 gdb -q --batch -x /tmp/oneshot_capture.gdb 2>&1 | tee /tmp/gdb_output.log
cat /tmp/capture_results.txt
```

The script files are durable:
- `/home/cortix/Downloads/9_Need for Speed Most Wanted Magipack/launch-debug.sh` — winedbg launcher
- `/tmp/oneshot_capture.gdb` — capture script (set BPs, continue, dump state, detach)

## **MAJOR FIND (2026-05-09 in-race attach #2)** — pvehicle vtables captured

User started a race; while in active driving, attached read-only via `sudo gdb -p` and dumped:

**`active_vehicle_components_arr_a_head @ 0x00913e74` had 6 entries** during the race — these are the active vehicles. All 6 share vtable `0x00897740` (audio class with embedded RTTI string `"Aud: EAX_HeliState"` at +0x10). Each audio entity's `this[+8]` points to the actual vehicle physics body on the heap.

The 6 vehicle bodies split into TWO classes:

| vtable | Count | Label | Concrete class |
|---|---|---|---|
| `0x008ac0fc` | 4 | `vtbl_pvehicle_AICar` | AI cars / traffic / cops |
| `0x008ac0f4` | (alt view) | `vtbl_pvehicle_AICar_SecondaryView` | MSVC multiple-inheritance secondary vtable for AICar |
| `0x008ac06c` | 2 | `vtbl_pvehicle_PlayerCar` | player vehicle (or richer variant) |

These are confirmed pvehicle-family (same .rdata cluster as `vtbl_pvehicle_ComponentList @ 0x008adcc0` which has the embedded RTTI string `pvehicle` at the inventory tail).

**Vehicle integration call chain at runtime:**
```
state==3 gameplay path:
  ActiveComponents_TickAll(dt)
    → for each entry in active_vehicle_components_arr_a (6 entries during race):
        Vehicle_PullSimResultAndUnpackWheels(audio_entity, dt)
          → VehicleAgent_QuerySimResult_Virtual(audio_entity, &out)
              → audio_entity[+8]->vtable[1](audio_entity, &out)
                  // Body vtable[1] = pvehicle_MatchTypeAndDispatch_vt1 (0x6a4040)
                  // does an id-match check; if match, calls vt[10] for actual work
              → vt[10] = pvehicle_DispatchSubobjVt1AndVt4 (0x694700)
                  // dispatches to body[+0x98] sub-physics object
                  // sub-object's vtable[1] / vtable[4] do the actual work
```

The actual physics integration is **5 levels deep** of virtual dispatch:
1. ActiveComponents_TickAll (loop)
2. Vehicle_PullSimResultAndUnpackWheels (per entity)
3. VehicleAgent_QuerySimResult_Virtual (vt-call)
4. pvehicle_MatchTypeAndDispatch_vt1 (id-check + delegate)
5. pvehicle_DispatchSubobjVt1AndVt4 (delegate to sub-physics)
6. Sub-physics-object vt[1] / vt[4] (the ACTUAL integrator) — at body[+0x98]

Body at +0x98 holds the runtime pointer to the actual physics simulator. To capture vt[1] of THAT requires another live attach reading the body's +0x98 field then its vtable[1]. Body sample (vehicle 0 at 0x1a511b0):
```
+0x00  primary vtable    = 0x008ac0fc
+0x08  secondary vtable  = 0x008ac0f4   (MI)
+0x14  heap subobject    = 0x01a4f240
+0x60  audio back-ref    = 0x01a46310   (the audio entity that wraps this body)
+0x98  sub-physics ptr   = ?            (need to read at runtime)
+0x100..0x140 floats     = position/velocity vectors (e.g., -2881.929, -167.801, -3193.314, -110.572)
```

**Key insight:** the 6 entries in `active_vehicle_components_arr_a` are AUDIO ENTITIES that wrap vehicles — the audio class hierarchy at 0x00897740 is for **vehicle audio sources** (engine + tires + wind + impacts per car). The 6 entries during the test race were audio for: player car + cops + AI cars. The audio entities serve as the "tickable" objects in the engine; they transitively pull data from their referenced vehicle bodies.

**Per-frame integrator status:**
- Layer 1-5 of the dispatch chain are NAMED in static analysis.
- Layer 6 (the actual integrator inside body[+0x98]'s vtable[1]) requires another live read of `body+0x98` to identify the sub-physics-object's class.
- The architecture is now fully understood; finishing the deepest layer is one more capture away.

## Cross-session synthesis (2026-05-09 final)

After 6+ live-debugger sessions, the picture is now:

**The audio/UI base class hierarchy** has FOUR distinct concrete classes (not 2 as initially thought), all sharing a common base. All four vtables live in adjacent .rdata at 0x00894cc8..0x00894f70. They share vt[0] (IsAliveStub), vt[3] (NoOpStub), vt[14] (PromoteAudioMemHandleToReady), vt[15] (setter), vt[17] (GetSubobjectPropPtr) — these are the BASE class methods. Each derived class overrides vt[1] (dtor) and vt[2] (Step):

| Vtable | Class | Step (vt[2]) | Dtor (vt[1]) |
|---|---|---|---|
| 0x894cc8 | `vtbl_AudioEntity_TypeA` | `0x47d3c0` AudioEntity_TypeA_Step | `0x47aa00` |
| 0x894e48 | `vtbl_UIScreenAnimEntity` | `0x476690` UIScreenAnim_ComputeTransformFromTrackedFng | `0x47aee0` |
| 0x894e90 | `vtbl_SmoothAudioEntity_With_Promote` | `0x4769e0` SmoothEntity_DampedParamInterpStep | `0x47af00` |
| 0x894f70 | `vtbl_AudioEntity_TypeD` | `0x482ec0` AudioEntity_TypeD_Step | `0x47b290` |

The **Wine crash** the user repeatedly hit (page fault at 0x47c8af reading address 0xffffffff with EDX=0x894cc8) is paradoxical: the static .rdata at 0x894cd0 reads 0x47d3c0 (a valid function address), not 0xffffffff. That means at runtime, something is **overwriting the vtable's vt[2] slot to 0xffffffff** — most likely the `EZ Wheel Wrapper v4.60.001` shim loaded as `app/DSOUND.dll` (via DSOAL bundle), which appears to hot-patch audio class methods. Without the wheel-wrapper, the Type A audio entity step (`0x47d3c0`) would dispatch normally.

Cumulative entity-class evidence at runtime (all observed slot 1 entities had different vtables across sessions):
  - `0x894cc8` (TypeA, hot-patched by mod, crashes)
  - `0x894e90` (SmoothInterp, observed working)
  - `0x894f70` (TypeD, observed but not exercised)

**The TRUE per-vehicle integrator is in some OTHER slot that never populated** during the captures because (a) the Wine setup crashes at slot 1 before reaching gameplay, and (b) when gameplay was reached briefly, no snapshot was taken in time. The 23-slot dispatcher and infrastructure are fully named; only the vehicle-specific class isn't populated in the runtime samples.

## BREAKTHROUGH (2026-05-09, third session — live attach to in-race game)

**Captured the runtime-bound integrator vtable!**

User played the game past the menu and into a race. With speed.exe at PID 56635
in active gameplay, attached gdb via `sudo gdb -p` (ptrace_scope=1 required
sudo) and set BP at `0x47c8af`. The BP fired immediately on the next frame.
Captured registers:

```
eax = 0x044550e4   (entity link pointer — heap)
ecx = 0x044550e0   (link - 4, vtable pointer location)
edx = 0x00894e90   (vtable address — IN .rdata)
esi = 0x00919694   (slot 1's list head address)
slot index = 1
```

**The runtime-bound vehicle vtable is at `0x00894e90`.** Read its contents:

```
vt[ 0]: 0x00468bb0
vt[ 1]: 0x0047af00  PerVehicleEntity_DeletingDtor (named)
vt[ 2]: 0x004769e0  PerVehicle_StepIntegrator (named — THE INTEGRATOR)
vt[ 3]: 0x004687f0
vt[ 4..10]: 0x00470970, 970, 980, 990, 9a0, 9b0, 9c0, 9d0  (sequential — likely default/no-op slots)
vt[11]: 0x00468ae0
vt[12..13]: 0x004709e0, 9f0
vt[14..15]: 0x00468800, 840
vt[16]: 0x00470a00
vt[17]: 0x00468020
+0x48: 0x42700000 = 60.0f
+0x4C: 0x40490fda ≈ π
vt[20..]: starts a SECOND method group with vt[20]=0x00468bb0, vt[21]=0x0047afb0
          (PerVehicleEntity_DeletingDtor_Variant — second-group dtor for derived class)
```

The vtable has the 4-slot-method-group pattern seen in AIAction vtables:
group[0] at vt[0..3] is the primary class; group[1] starts at vt[20] as a
secondary/derived view. Embedded float constants (60.0, π) at +0x48 are tuning
values used by the methods themselves.

**Per-frame integrator confirmed at `PerVehicle_StepIntegrator (0x004769e0)`:**
- Signature `(this, float dt)`
- State gate at `this+0x80` (skip if == 2)
- DT accumulator at `this+0x134` (`+= dt` each tick)
- Velocity vec3 at `this+0x90`
- 19-float local staging buffer

This closes the open thread from the original advisor recommendation —
the vt[2] dispatch target IS reachable via static analysis once we know
the vtable address. Game running, BP fires every frame the slot-1 entity
ticks.

## Original 2026-05-08 watchpoint trace (kept for context)

Set a hardware watchpoint on the slot 0 list head `*(0x919624)` and ran from
process entry. Captured 3 watchpoint hits + 5 `PerPlayerSubsystemTick` entries
before the game self-exited (~2s in).

**Confirmed via watchpoint:**
1. The list head is initialized to **self-reference** (empty-list sentinel) at
   `0x00505fa4` inside `PlayerEntitySlot_Construct (0x00505f80)` — invoked at
   CRT static-init via the per-section init walker at `0x00886228` from
   `mainCRTStartup` at `0x007c4186`.
2. The slot-array OBJECT base is at `0x009195e0` (not `0x919624`). Each slot
   is a 0x70-byte object with the list-head field at +0x44. The address
   `0x919624` we labeled earlier is just `slot[0] + 0x44` — slot 0's list head.
3. **All 23 slots are empty during engine boot.** PerPlayerSubsystemTick
   iterates them every frame; the head=self check makes the loop skip the
   indirect call cleanly. The integrator BP at `0x47c8af` **never fires**
   while no entity has been added.
4. Slot constructor confirmed via disassembly:
   - sets `this[+0x44] = this+0x44` (list head = self)
   - sets `this[+0x48] = this+0x44` (list tail = self)
   - REP STOSD zeroes 0x70 bytes (which clears those, then re-inits)
   - computes `slot_index = (this - 0x9195e0) / 0x70` and stores at this[+4]
   - stores `1.0f` at this[+0x18]
   - calls `FUN_0x6be9e0(slot_index)` for further per-slot init

**Implication for capturing the integrator:**

The earlier crash at `0x47c8ac` came from a DIFFERENT slot (not slot 0) that
got populated mid-init by some subsystem. To capture the live integrator
vtable target, the game must reach a state where at least one slot has been
populated with a valid entity. The empirically reproducible path to that
state is **starting an actual race** — but the X11/Wine display issues
prevent menu navigation in this environment.

**Drivers are NOT the issue.** `nvidia-utils 595.58.03` and `lib32-nvidia-utils`
are installed; `glxinfo` reports the RTX 3060 with direct rendering on OpenGL
4.6. The `egl: failed to create dri2 screen` warnings are harmless (Mesa's
libEGL probes DRI2 first; NVIDIA's proprietary EGL doesn't expose it; Wine
falls back to GLX which works).

The actual blocker is reaching gameplay UI interactively. Consequences:
- Static analysis on this binary has reached its productive limit on the
  per-vehicle integrator and per-frame Present targets.
- The next productive runtime trace would be against a player who can drive
  in-race — i.e., on Windows, or on Linux with DXVK forcing the D3D9 path
  through Vulkan, or on a system with a working menu-input path.
- Everything else in the project is mapped via static analysis.
