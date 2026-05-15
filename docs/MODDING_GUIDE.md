# NFSMW Modding Guide

A comprehensive guide to building NFSMW (2005) mods using the reverse-engineering
work captured in this project. Every address cited here traces back to either
`docs/sdk_addrs.json` or one of the wave memory entries — no fabricated symbols.

The reference implementation is `mods/infinite_trainer/nfsmw_trainer.c`. This
document walks through it line-by-line, then expands into the broader patterns
the project's RE work makes available: HUD modification, attribute writing, AI
behavior overrides, FNG event posting, and game-state-machine injection.

---

## Table of contents

1. [Setup — toolchain, Wine, ASI loader](#1-setup)
2. [The `infinite_trainer` template explained](#2-the-infinite_trainer-template)
3. [Single-byte tweak mods — every Tweak\_\* and Draw\* global](#3-single-byte-tweak-mods)
4. [Hook patterns — vtable replacement, detours, event-bus interception](#4-hook-patterns)
5. [HUD widget modification](#5-hud-widget-modification)
6. [Attribute writing](#6-attribute-writing)
7. [AI behavior mods](#7-ai-behavior-mods)
8. [Game state machine injection](#8-game-state-machine-injection)
9. [FNG event posting from mods](#9-fng-event-posting-from-mods)
10. [Common pitfalls](#10-common-pitfalls)

---

## 1. Setup

NFSMW (2005) is a 32-bit PE executable with image base `0x00400000`. The
Magipack distribution ships an Ultimate-ASI-Loader proxy at `app/dinput8.dll`,
which scans `app/scripts/*.asi` on game startup and `LoadLibrary`s each one.
A "mod" in this guide is a 32-bit Windows DLL renamed to `.asi`.

### 1.1. Install MinGW-w64 (cross-compiler for Linux/macOS)

You can target the PE32 ABI from any host using MinGW-w64:

```bash
# Arch / Manjaro
sudo pacman -S mingw-w64-gcc

# Debian / Ubuntu
sudo apt install gcc-mingw-w64-i686

# macOS
brew install mingw-w64
```

The trainer's `Makefile` uses `i686-w64-mingw32-gcc -m32` — the `-m32` is the
critical flag, because NFSMW is a 32-bit process and a 64-bit DLL won't load.

### 1.2. Install Wine (only for Linux/macOS playtest)

```bash
sudo pacman -S wine                 # Arch
sudo apt install wine32 wine64      # Debian/Ubuntu
```

The Magipack already runs under Wine — no special prefix is required for the
ASI loader to work; the loader is a standard `dinput8.dll` proxy.

### 1.3. Ultimate-ASI-Loader

The Magipack bundles Ultimate-ASI-Loader as `app/dinput8.dll`. When `speed.exe`
launches and imports `dinput8.dll`, the loader takes over the import, then:

1. Forwards every real DirectInput export to the system DLL.
2. Enumerates `app/scripts/*.asi` and `LoadLibrary`s each one.
3. Each `.asi`'s `DllMain` runs with `DLL_PROCESS_ATTACH`.

That's where your mod code begins. Drop `nfsmw_trainer.asi` into
`extracted/app/scripts/` and it will load on the next launch.

### 1.4. Build & install loop

```bash
cd mods/infinite_trainer
make
make install   # copies the .asi to extracted/app/scripts/
wine ../../extracted/app/speed.exe
```

`OutputDebugStringA` calls inside the mod can be captured under Wine with
`WINEDEBUG=+tid wine speed.exe 2>&1 | grep '\[NFSMW Trainer\]'`, or on a
Windows debug build with DbgView / DebugView++.

---

## 2. The `infinite_trainer` template

The trainer is roughly 110 lines and is the simplest possible working mod.
Below is a guided tour with the full source structure annotated.

### 2.1. Headers and address constants

```c
#include <windows.h>
#include <stdio.h>
#include <stdint.h>

/* Addresses from docs/sdk_addrs.json (NFSPluginSDK by berkayylmao, BSD-3). */
#define TWEAK_INFINITE_NOS          0x00937804u  /* bool */
#define TWEAK_INFINITE_RACEBREAKER  0x00988E1Cu  /* bool */
#define TWEAK_GAME_SPEED            0x00901B1Cu  /* float, default 1.0 */
#define DRAW_HUD                    0x0057CAA8u  /* bool */
#define WINDOW_HAS_LOST_FOCUS       0x00982C50u  /* bool */
#define IS_IN_NIS                   0x0091606Cu  /* bool */
```

Every address is a literal absolute virtual address in the loaded image of
`speed.exe`. NFSMW does not use ASLR — `speed.exe` always maps to its declared
ImageBase of `0x00400000`, so hard-coded addresses work without rebasing.

### 2.2. Write helpers — page protection

```c
static void write_byte(uintptr_t addr, BYTE value) {
    DWORD old_prot;
    if (VirtualProtect((LPVOID)addr, 1, PAGE_EXECUTE_READWRITE, &old_prot)) {
        *(BYTE*)addr = value;
        VirtualProtect((LPVOID)addr, 1, old_prot, &old_prot);
    }
}

static void write_float(uintptr_t addr, float value) {
    DWORD old_prot;
    if (VirtualProtect((LPVOID)addr, 4, PAGE_EXECUTE_READWRITE, &old_prot)) {
        *(float*)addr = value;
        VirtualProtect((LPVOID)addr, 4, old_prot, &old_prot);
    }
}
```

Most of the `Tweak_*` and `Draw*` globals live in `.data` (writable already),
but some — and especially anything in `.text` like a hooked instruction byte —
will fault unless you flip the page protection first. Always wrap your write
with `VirtualProtect` for safety; the cost is one syscall per patch and a
roundtrip back to the original protection.

### 2.3. Image-base validation

```c
static int validate_speed_exe(void) {
    HMODULE main_module = GetModuleHandleA(NULL);
    if (!main_module) return 0;
    DWORD nt_offset    = *(DWORD*)((BYTE*)main_module + 0x3C);
    DWORD image_base   = *(DWORD*)((BYTE*)main_module + nt_offset + 0x34);
    return image_base == 0x00400000;
}
```

This is a defensive measure: the same `.asi` could in theory be `LoadLibrary`d
by some other process that happens to have a `dinput8.dll` import. By checking
the PE header's `ImageBase` we ensure we are inside an executable whose layout
matches our hardcoded addresses. Always include a check like this — patching
arbitrary bytes inside an unknown process is a recipe for a crash log on the
user's desktop.

### 2.4. Worker thread

```c
static DWORD WINAPI trainer_thread(LPVOID lpv) {
    (void)lpv;
    Sleep(2000);  /* let the engine finish its own init */

    if (!validate_speed_exe()) {
        OutputDebugStringA("[NFSMW Trainer] ERROR: not inside speed.exe\n");
        return 1;
    }

    BYTE old_nos    = *(BYTE*)TWEAK_INFINITE_NOS;
    BYTE old_brkr   = *(BYTE*)TWEAK_INFINITE_RACEBREAKER;
    write_byte(TWEAK_INFINITE_NOS, 1);
    write_byte(TWEAK_INFINITE_RACEBREAKER, 1);

    char msg[256];
    snprintf(msg, sizeof(msg),
        "[NFSMW Trainer] Patched: NOS %d->1, RaceBreaker %d->1\n",
        old_nos, old_brkr);
    OutputDebugStringA(msg);
    return 0;
}
```

The 2-second sleep is a pragmatic delay so that the engine's static initializers
have run and the `.data` region holds the engine's defaults — patching too
early could be overwritten by the game itself. For tweak globals this rarely
matters, but for hook installations it's essential.

### 2.5. `DllMain`

```c
BOOL WINAPI DllMain(HINSTANCE hinst, DWORD reason, LPVOID reserved) {
    (void)reserved;
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(hinst);
        HANDLE h = CreateThread(NULL, 0, trainer_thread, NULL, 0, NULL);
        if (h) CloseHandle(h);
    }
    return TRUE;
}
```

Do **not** do work directly inside `DllMain`. The Windows loader holds the
loader lock while `DllMain` runs and calling most APIs from inside it is
unsupported. Always spin out a worker thread — every serious ASI mod does
this.

---

## 3. Single-byte tweak mods

The simplest mods are one-byte or one-float pokes against the engine's
SDK-exposed globals. From `docs/sdk_addrs.json`:

| Address     | Name                              | Type   | Default | Effect when changed |
|-------------|-----------------------------------|--------|---------|---------------------|
| `0x57caa8`  | `DrawHUD`                         | bool   | true    | Set false to hide the entire HUD |
| `0x8f2918`  | `DrawLightFlares`                 | bool   | true    | Set false to disable headlight/streetlight flares |
| `0x901aec`  | `Tweak_GameBreakerCollisionMass`  | float  | 2.0     | Mass multiplier applied to vehicles during SpeedBreaker collisions |
| `0x901b1c`  | `Tweak_GameSpeed`                 | float  | 1.0     | Global time-scale (set 2.0 for fast-forward, 0.5 for slow-mo) |
| `0x903320`  | `DrawCars`                        | bool   | true    | Set false to hide every car except the player |
| `0x903324`  | `DrawCarsReflections`             | bool   | true    | Skip car reflection passes |
| `0x903328`  | `DrawCarShadow`                   | bool   | true    | Skip car shadow render pass |
| `0x92584c`  | `Tweak_PauseCameraLock`           | bool   | false   | Lock the camera when the pause menu is open |
| `0x937804`  | `Tweak_InfiniteNOS`               | bool   | false   | NOS never depletes |
| `0x988e1c`  | `Tweak_InfiniteRaceBreaker`       | bool   | false   | SpeedBreaker (Race-breaker) never depletes |

Additional related globals available from the same source:

| Address     | Name                  | Type   | Note |
|-------------|-----------------------|--------|------|
| `0x8f86c0`  | `SkipFEDisableCops`   | bool   | Suppresses cops when skipping the FE |
| `0x91606c`  | `IsInNIS`             | bool   | Set during cutscenes — read-only at runtime |
| `0x982c50`  | `WindowHasLostFocus`  | bool   | Engine sets this when alt-tabbing |

A minimal "no-HUD, 2x speed" mod is two writes:

```c
write_byte(0x57caa8u, 0);                      /* DrawHUD = false */
write_float(0x901b1cu, 2.0f);                  /* Tweak_GameSpeed = 2.0 */
```

For floats, the SDK only exposes two: `Tweak_GameBreakerCollisionMass` and
`Tweak_GameSpeed`. Everything else listed above is `bool` (one byte).

### 3.1. Why `Tweak_InfiniteRaceBreaker` works

The drain side of the SpeedBreaker controller — verified in
`project_speedbreaker_userkey_chain.md` — has a literal `if
(g_bTweak_InfiniteRaceBreaker == false)` guard around the per-frame energy
decrement (see `UpdateSpeedBreakerEnergyTick @ 0x006edd60`). Setting that one
byte to `1` skips the drain branch entirely — no patching of the function
itself required. This is why the tweak globals are so cheap to flip: the
engine builds them into its control flow.

---

## 4. Hook patterns

Tweak globals only get you so far. For richer behavior overrides you'll
intercept calls — three standard patterns.

### 4.1. Vtable replacement

NFSMW is heavily C++/virtual. Vtables are arrays of function pointers stored
in `.rdata` (read-only after load), so you `VirtualProtect` to RW, swap a
slot, then restore protection. From the HUD wave-13 work, the CHudWidgetArray
vtable lives at `0x008a2538` and its `Tick` is at `vt[1]` (= `0x0058ca30`):

```c
/* Pattern: replace CHudWidgetArray::Tick with our own implementation,
 * keeping the original so we can chain to it. */
typedef void (__thiscall *CHudWidgetArrayTickFn)(void *self, void *param);

static CHudWidgetArrayTickFn g_orig_hud_tick = NULL;

static void __fastcall MyHudTick(void *self, void *edx, void *param) {
    /* Pre-update hook — your code here */
    g_orig_hud_tick(self, param);   /* call the real Tick */
    /* Post-update hook — your code here */
}

static void install_hud_tick_hook(void) {
    void **vtable     = (void**)0x008a2538;       /* CHudWidgetArray vtable */
    DWORD old_prot;
    VirtualProtect(&vtable[1], sizeof(void*), PAGE_READWRITE, &old_prot);
    g_orig_hud_tick = (CHudWidgetArrayTickFn)vtable[1];   /* save = 0x58ca30 */
    vtable[1]       = (void*)MyHudTick;
    VirtualProtect(&vtable[1], sizeof(void*), old_prot,    &old_prot);
}
```

`__thiscall` is the calling convention for C++ non-static methods on
32-bit MSVC — `this` arrives in `ECX`. On GCC/MinGW the trick is to declare
the hook as `__fastcall` with a dummy `edx` parameter, which receives
nothing but matches the stack frame the compiler emits. (MSVC has
`__thiscall` natively.) Note that for plain C-level virtuals — like the
`CHudWidgetArray_Tick` referenced above — the engine's vtable slot reference
is `(**(code **)(*widget + 4))();` per the decompiled walker, so calling
convention matters only when you chain back to the original.

### 4.2. 5-byte JMP detour (function trampoline)

For non-virtual functions, the universal pattern is a 5-byte JMP at the
function entry, with a trampoline that runs the displaced prologue bytes plus
a JMP back. This is the "Detours" pattern. For a hook on
`SetSpeedBreakerActive @ 0x006e9aa0`:

```c
/* Reserve enough bytes for the relocated prologue (usually 5-7) + JMP back. */
static unsigned char g_set_sb_trampoline[32];
typedef void (__cdecl *SetSpeedBreakerActiveFn)(void *self, char state);
static SetSpeedBreakerActiveFn g_orig_set_speedbreaker = NULL;

static void __cdecl MySetSpeedBreakerActive(void *self, char state) {
    /* Force the breaker on regardless of the requested state. */
    g_orig_set_speedbreaker(self, 1);
}

static void install_set_speedbreaker_detour(void) {
    uintptr_t target = 0x006e9aa0u;          /* SetSpeedBreakerActive */
    DWORD old_prot;
    /* Copy 5 prologue bytes to trampoline */
    memcpy(g_set_sb_trampoline, (void*)target, 5);
    /* JMP back into target+5 */
    g_set_sb_trampoline[5] = 0xE9;
    *(int32_t*)&g_set_sb_trampoline[6] =
        (int32_t)(target + 5 - (uintptr_t)&g_set_sb_trampoline[10]);
    /* Make trampoline executable */
    VirtualProtect(g_set_sb_trampoline, sizeof(g_set_sb_trampoline),
                   PAGE_EXECUTE_READWRITE, &old_prot);
    g_orig_set_speedbreaker = (SetSpeedBreakerActiveFn)g_set_sb_trampoline;

    /* Patch the target prologue: E9 rel32 to MySetSpeedBreakerActive */
    VirtualProtect((void*)target, 5, PAGE_EXECUTE_READWRITE, &old_prot);
    *(uint8_t*)target          = 0xE9;
    *(int32_t*)(target + 1)    = (int32_t)((uintptr_t)MySetSpeedBreakerActive
                                           - (target + 5));
    VirtualProtect((void*)target, 5, old_prot, &old_prot);
}
```

This is the **standard detour pattern**, presented here as reference. In
production you'd use MinHook or Detours rather than rolling it by hand,
because of edge cases (relative jumps in the prologue, short prologues
under 5 bytes, etc.). The trainer project doesn't currently use detours —
its only writes are byte-level pokes — but every address cited above is a
real function from this project's RE.

### 4.3. Event-bus interception

The FNG event bus chain is described end-to-end in
`project_fng_dispatch_complete.md`. The single best interception point is
`PostUIEventToNamedNode @ 0x516c90`, because every UI event funnels through
it before being scheduled or dispatched. Hook it the same way as section 4.2:

```c
typedef void (__cdecl *PostUIEventFn)(void *ui_root, unsigned event_hash,
                                      const char *node_name, int payload);
static PostUIEventFn g_orig_post_ui_event = NULL;

static void __cdecl MyPostUIEvent(void *ui_root, unsigned event_hash,
                                  const char *node_name, int payload) {
    /* Filter / log / suppress events here. */
    if (event_hash == 0x014035fb) {
        /* HUD render-ready event from wave-13 — drop it as a test. */
        return;
    }
    g_orig_post_ui_event(ui_root, event_hash, node_name, payload);
}
```

You can also intercept later in the chain:

| Hook point | Address | Use case |
|---|---|---|
| `PostUIEventToNamedNode`            | `0x516c90` | All UI events |
| `DispatchUIEventToNamedNode`        | `0x516be0` | Per-target-node filtering |
| `ScheduleUIDeferredEvent`           | `0x5b7780` | Per-event-hash filtering, queue inspection |
| `DrainUIDeferredEventQueue_PerFrame`| `0x5c1460` | Drain interception (rarely needed) |
| `FE_PerFrameTick_DrainQueueAndUpdateChildren` | `0x5c53c0` | Per-frame FE tick |

---

## 5. HUD widget modification

The HUD is structured as one `CHudWidgetArray` object containing eleven
widget slots at fixed offsets (`+0x2dc`, `+0x2e0`, `+0x2e8`, `+0x2ec`,
`+0x2f0`, `+0x310`, `+0x314`, `+0x318`, `+0x31c`, `+0x328`, `+0x32c`).
Each frame, `CHudWidgetArray_Tick @ 0x58ca30` walks these slots and calls
`vt[1]` (the widget's `Update`) on each one, gated by a mode-filter mask.

### 5.1. Force-tick or skip a widget

Per the wave-13 capture, each widget has `widget[6..9]` (offsets `+0x18`
through `+0x24`) acting as mode-filter masks. A widget is ticked iff
`(widget[8] & widget[6]) != 0 || (widget[9] & widget[7]) != 0`. So:

```c
/* Force a widget at slot+0x2dc to always tick (set both mask pairs to -1). */
unsigned char *hud_array = /* obtain via game accessor or static ptr */;
unsigned **slot     = (unsigned**)(hud_array + 0x2dc);
unsigned  *widget   = (unsigned*)(*slot);
if (widget) {
    widget[6] = 0xFFFFFFFF;
    widget[7] = 0xFFFFFFFF;
    widget[8] = 0xFFFFFFFF;
    widget[9] = 0xFFFFFFFF;
}
```

Conversely, to suppress a widget without disturbing render state:

```c
widget[6] = widget[7] = widget[8] = widget[9] = 0;
```

### 5.2. Inject a custom widget

The slot is just a pointer to an object whose first member is a vtable
pointer. Allocate your own object, write a vtable with at least a `dtor`
(slot 0) and `Update` (slot 1), set `widget[6..9]` to a mode-filter that
matches your desired game mode, and write the pointer into one of the
free widget slot offsets. Nothing else is needed for the walker to start
calling your `Update` every frame.

### 5.3. Per-widget direct field writes

From `project_hud_widget_internals.md`, every walker-driven widget has a
known field layout. Examples of useful pokes against a live widget pointer:

```c
/* RaceOverMessage @ 0x0057a4b0 — force the race-end message to display */
*(unsigned char*)((char*)widget + 0x39) = 1;

/* HeatMeterInRace @ 0x005666a0 — fake max heat */
*(float*)((char*)widget + 0x40) = 4.0f;       /* raw heat */

/* Reputation @ 0x005669b0 — show rep for 60 frames */
*(void**)((char*)widget + 0x40)  = my_rep_data_ptr;
*(int*)((char*)widget + 0x3c)    = 60;

/* TimeExtension @ 0x0057b780 — force a +bonus seconds display */
*(float*)((char*)widget + 0x40)  = 5.0f;

/* RadarDetector @ 0x00566170 — force visible/hidden via the two flag bytes */
*(unsigned char*)((char*)widget + 0x64) = 1;
*(unsigned char*)((char*)widget + 0x65) = 1;

/* PursuitBoardInRace @ 0x0057aee0 — fake 4 active cops */
*(unsigned char*)((char*)widget + 0x38) = 1;
*(float*)((char*)widget + 0x40)         = 4.0f;
```

Two widgets do NOT update from the walker:

* `BustedMeter @ 0x00568eb0` — its `Update` is a no-op. The visible value is
  written by an external system (cop-AI tick). To mod it you must locate
  and hook that external writer.
* `Infractions @ 0x00569a50` — its `Update` only polls 4 slot entries that
  are populated by cop-AI infraction events. To inject custom infractions
  you must patch the infraction emitter, not the widget.

### 5.4. FNG node hashes commonly used

| Hash         | Likely state name      |
|--------------|------------------------|
| `0x5079c8f8` | HIDDEN / OFF           |
| `0x33113ac`  | VISIBLE / SHOW         |
| `0x1744b3`   | OFF (alternate)        |
| `0x16a259`   | IDLE / INACTIVE        |
| `0x41e1fedc` | HeatMeter low state    |
| `0x77031c70` | HeatMeter mid state    |
| `0xda600155` | HeatMeter high state   |
| `0x13f51124` | PursuitBoard state     |
| `0x8ab83edb` | "FADE_IN" / "APPEAR_BIG" anim |
| `0x4f79cba2` | "HOLD" anim            |
| `0x821e6378` | "FADE_OUT" anim        |

These are pre-computed FE hashes (DJB-family, not Jenkins bChunk) that
appear in the widget decompilations as state IDs passed to
`CheckActiveSceneChildIdEquals` and `RemoveSceneNodeByName`.

---

## 6. Attribute writing

NFSMW's attribute system is a hashed key/value table. The cracked hash list
in `docs/attribute_cracks_verified.json` covers the names we have so far.
Examples of stable, frequently-modded attribute hashes:

| Hash         | Name                |
|--------------|---------------------|
| `0x263E9452` | FOV                 |
| `0x4A56503D` | MASS                |
| `0x96E40580` | Power               |
| `0x81625B35` | Life                |
| `0x39BF8002` | Radius              |
| `0x07A7A3E5` | transmission        |
| `0x36350867` | brakes              |
| `0x83066633` | Tranny              |
| `0x665F4D74` | TILTING             |
| `0x4CB36381` | AxlePair            |
| `0x6CCD5819` | ResetsPlayer        |
| `0x5F84F834` | RESPAWN_TIME        |
| `0x811C6606` | TRAFFIC_SPEED       |
| `0x3F4A4CEC` | MAX_TRAFFIC_SPAWN_DISTANCE |
| `0x3918E889` | CopsInRace          |
| `0x0E47FE63` | ScriptedCopsInRace  |

The full list is in `docs/attribute_cracks_verified.json`. Attribute rows are
16 bytes each from `0x18000` in the attribute store (see the
`project_attribute_schema` memory entry for the row layout). Most floats sit
at `+0x0C` of the row. To mod a Float attribute by hash:

```c
/* Pseudocode — concrete row offset depends on per-table layout. */
extern float* find_attribute_float(unsigned hash);

float *fov = find_attribute_float(0x263E9452);    /* FOV */
if (fov) *fov = 90.0f;
```

In practice you locate the row by walking the attribute table from
`0x18000` looking for the matching hash in column 0, then write the float at
the row's data slot. The `attribute_cracks_verified.json` set was verified
against in-game values, so these hashes are safe to rely on.

For modding races and cop behavior, the most useful keys are:
`CopsInRace`, `ScriptedCopsInRace`, `TRAFFIC_SPEED`,
`MAX_TRAFFIC_SPAWN_DISTANCE`, `RESPAWN_TIME`, `RandomOpponent`, `TimeLimit`,
`AutoStart`, `GoalEasy`, `GoalHard`, `TargetBronze`, `TargetSilver`,
`TargetGold`.

---

## 7. AI behavior mods

The two AI vehicle vtables captured in `project_ai_vehicle_vtables.md`:

* `vtbl_AIVehicleTraffic @ 0x00891CF8` (24 slots)
* `vtbl_AIVehicleHelicopter @ 0x008920D8` (30 slots)

Both share a base-class `Update` at `vt[1] = 0x00406600`
(`AIVehicle_BaseUpdate_vt1`). The per-class `OnDriving` is at `vt[10]`:

* Traffic: `UpdateAIVehicleTraffic_OnDriving @ 0x0042ab40`
* Helicopter: `UpdateAIVehicleHelicopter_OnDriving @ 0x0042adb0`

The helicopter additionally exposes `FilterHeliAltitudeVector @ 0x00417a20`
at `vt[17]`, which clamps the seek-point Y to mHeight bounds.

### 7.1. Override per-frame heli driving

```c
typedef void (__thiscall *HeliOnDrivingFn)(void *self, float dt);
static HeliOnDrivingFn g_orig_heli_on_driving = NULL;

static void __fastcall MyHeliOnDriving(void *self, void *edx, float dt) {
    /* Pre-update: maybe force a desired velocity or altitude here. */
    g_orig_heli_on_driving(self, dt);
    /* Post-update: maybe re-read state and override. */
}

static void install_heli_hook(void) {
    void **vt = (void**)0x008920D8u;     /* vtbl_AIVehicleHelicopter */
    DWORD old_prot;
    VirtualProtect(&vt[10], sizeof(void*), PAGE_READWRITE, &old_prot);
    g_orig_heli_on_driving = (HeliOnDrivingFn)vt[10];
    vt[10] = (void*)MyHeliOnDriving;
    VirtualProtect(&vt[10], sizeof(void*), old_prot, &old_prot);
}
```

### 7.2. Strip helicopter altitude clamping

```c
/* Zero out the filter — heli will follow seek-point Y verbatim. */
static void __fastcall MyFilterHeliAltitude(void *self, void *edx, void *vec) {
    (void)self; (void)edx; (void)vec;
    /* no clamp */
}

static void install_no_alt_clamp(void) {
    void **vt = (void**)0x008920D8u;
    DWORD old_prot;
    VirtualProtect(&vt[17], sizeof(void*), PAGE_READWRITE, &old_prot);
    vt[17] = (void*)MyFilterHeliAltitude;
    VirtualProtect(&vt[17], sizeof(void*), old_prot, &old_prot);
}
```

### 7.3. Traffic behavior

`UpdateAIVehicleTraffic_OnDriving @ 0x0042ab40` is the per-frame entry for
every traffic vehicle. Hook it identically to the heli example, swap
`0x891CF8` for the traffic vtable and `vt[10]` for the slot.

Other useful traffic-class slots (un-named so far, but addresses verified):

| Slot   | Address     | Notes |
|--------|-------------|-------|
| vt[15] | `0x00415290` | Traffic-specific |
| vt[20] | `0x00432490` | Traffic-specific |
| vt[21] | `0x00423320` | Traffic-specific |
| vt[22] | `0x00423430` | Traffic-specific |
| vt[23] | `0x00423370` | `SetAITrafficGoal` |

For cop AI rather than traffic, the per-frame entry is in the
`SetAICopPursuitGoal @ 0x42ab80` family (see the `project_cop_ai_pursuit`
memory entry). The cop goal stack and `CreateAIAction{Race,Ram,Roadblock,
HeliExit}` constructors are the granular control points.

---

## 8. Game state machine injection

NFSMW's game-flow state is a **function-pointer trampoline**, not an enum
(see `project_game_state_machine.md`). The dispatch loop is
`ProcessGameStateMachine @ 0x6596a0`:

```c
void ProcessGameStateMachine(int *state_record) {
  code *fn = (code*)*state_record;
  do {
    if (fn == NULL) break;
    int arg = state_record[1];
    *state_record   = 0;
    state_record[1] = 0;
    state_record[2] = 0;
    (*fn)(arg);                          /* run state fn */
    bool transitioned = ((code*)*state_record != fn);
    fn = (code*)*state_record;
  } while (transitioned);
  if (state_record[3] != 0)
    ((code*)state_record[3])();          /* post-callback */
}
```

The state record at `DAT_00925e70` is a 16-byte (4-slot) struct of
`{fn_ptr, arg, ctx, post_cb}`. "Transitioning" means a state fn writes a
new fn pointer into `state_record[0]` before returning.

### 8.1. Read the current state from a mod

```c
typedef void (*GameStateFn)(int arg);
GameStateFn current_state(void) {
    int *state_record = (int*)0x00925e70u;
    return (GameStateFn)state_record[0];
}
```

### 8.2. Inject a custom state (trampoline replacement)

The cleanest injection is to set `state_record[3]` (the post-callback),
which the dispatch loop invokes after the state-transition loop unwinds.
That callback fires once per dispatch — perfect for "do something every
time the game flow advances":

```c
static void __cdecl my_post_state_cb(void) {
    /* This runs after every state transition. */
    OutputDebugStringA("[NFSMW Mod] state advanced\n");
}

static void install_state_post_cb(void) {
    int *state_record = (int*)0x00925e70u;
    DWORD old_prot;
    VirtualProtect(&state_record[3], 4, PAGE_READWRITE, &old_prot);
    state_record[3] = (int)my_post_state_cb;
    VirtualProtect(&state_record[3], 4, old_prot, &old_prot);
}
```

To force a state transition from a mod, write a known state-fn pointer into
`state_record[0]`:

| Address     | Name                              |
|-------------|-----------------------------------|
| `0x664c20`  | `StateLoadingFrontEnd`            |
| `0x659530`  | `StateBeginGameFlowLoadTrack`     |
| `0x666fa0`  | `StateBeginGameFlowLoadTrackImpl` |
| `0x667340`  | `BeginGameFlowUnloadTrack`        |
| `0x666aa0`  | `DispatchRegionLoaderHandler`     |

```c
/* Force the engine to reload the front-end next dispatch. */
int *state_record = (int*)0x00925e70u;
state_record[0] = 0x664c20;     /* StateLoadingFrontEnd */
```

Don't write to `state_record[0]` during a state-fn execution unless you're
trying to do a transition from that state — the dispatch loop will catch
the write and treat it as a normal transition.

---

## 9. FNG event posting from mods

Once you can call into `PostUIEventToNamedNode`, you can fake any UI event:

```c
typedef void (__cdecl *PostUIEventFn)(void *ui_root, unsigned event_hash,
                                      const char *node_name, int payload);

static void post_ui_event(unsigned hash, const char *node, int payload) {
    PostUIEventFn fn = (PostUIEventFn)0x00516c90u;     /* PostUIEventToNamedNode */
    void *ui_root = /* obtain from a hooked Tick that captures `this` */;
    fn(ui_root, hash, node, payload);
}
```

Event hashes worth knowing:

| Hash         | Meaning |
|--------------|---------|
| `0x014035fb` | HUD render-ready (broadcast by `CHudWidgetArray_Tick`) |

The event object format (0x20 bytes) is documented in
`project_fng_dispatch_complete.md`:

```
+0x00  vtable = 0x008a2c90 (PTR_FUN_008a2c90)
+0x04  prev   (fence 0xABADCAFE initially)
+0x08  next   (fence 0xABADCAFE initially)
+0x0c  param_2 (caller payload)
+0x10  event hash
+0x14  command/value
+0x18  target node ptr (or 0xfffffffc broadcast, 0xfffffffa alt-broadcast, NULL type-registry)
+0x1c  priority
```

If you really need to inject directly into the queue (bypassing
`PostUIEventToNamedNode`), allocate a 0x20-byte event, set the vtable and
fences, and link it into the doubly-linked list at `this+0x4118`
(`this+0x4114` is the count, `this+0x411c` is the tail).

For most mods the right call is just `PostUIEventToNamedNode`. Synchronous
dispatch happens if the UI-root's `+0x524e` byte is set; otherwise the
event drains on the next FE tick via `FE_PerFrameTick_DrainQueueAndUpdateChildren`.

---

## 10. Common pitfalls

### 10.1. Patching the wrong process

Always call `validate_speed_exe()` (or equivalent) before any write. An ASI
loader might inject your DLL into any process that imports `dinput8.dll`,
and writes to `0x00400000` in the wrong process will either crash the host
or silently no-op. The 6-line PE-header check in the trainer is the
cheapest possible guard:

```c
DWORD nt_offset  = *(DWORD*)((BYTE*)GetModuleHandleA(NULL) + 0x3C);
DWORD image_base = *(DWORD*)((BYTE*)GetModuleHandleA(NULL) + nt_offset + 0x34);
return image_base == 0x00400000;
```

### 10.2. Page protection

Globals in `.data` are usually writable; functions, vtables (`.rdata`), and
some const tables are not. **Always** wrap writes with `VirtualProtect` to
`PAGE_EXECUTE_READWRITE`, perform the write, and restore the old protection.
Skipping this works for `Tweak_InfiniteNOS` but will fault for vtable swaps
and for any `.text` patch.

### 10.3. Race conditions on init

If you patch a global from `DllMain`, the engine's own static constructors
may write over you. Always defer work to a worker thread, sleep for at
least 1-2 seconds, then validate and patch. For hooks that depend on the
target object existing (HUD widgets, vehicles), defer until after a
known-late state transition — the trainer uses a flat `Sleep(2000)`, but
hooking `ProcessGameStateMachine`'s post-callback is more robust.

### 10.4. Wine quirks

* `OutputDebugStringA` output appears under Wine with `WINEDEBUG=+tid` or
  by hooking the per-process debug stream. On Windows you'd use DbgView.
* Wine maps the image at the declared base just like Windows — addresses
  work identically.
* `VirtualProtect` is implemented by Wine; no special handling needed.
* If your mod uses `printf` to stdout, Wine sends it to its own console;
  the safer logging primitive is `OutputDebugStringA`.

### 10.5. `__thiscall` vs `__fastcall` on MinGW

GCC/MinGW doesn't natively support `__thiscall`. The standard workaround
for hooking a non-static method is `__fastcall` with a dummy `EDX` parameter:

```c
static void __fastcall MyHook(void *self, void *edx, ARG arg1) { ... }
```

`self` arrives in `ECX`, `edx` matches the convention's second register
(unused by `__thiscall`), and the remaining args arrive on the stack as
expected. Do not forget the `edx` parameter — without it, the call frame
will be misaligned and you'll see the first stack argument show up as the
"self" pointer.

### 10.6. Re-entrancy in vtable hooks

If you hook `CHudWidgetArray::Tick` and your hook calls back into anything
that recursively walks widgets, you can re-enter your own hook. Either keep
a per-thread re-entry flag or use a thread-local hop-counter. The same
applies to `PostUIEventToNamedNode` — your hook MUST be re-entrant or
guard against recursion.

### 10.7. Bytes-out-of-range arithmetic

The detour pattern in section 4.2 uses a `rel32` JMP, whose target must
fit in a signed 32-bit displacement. Within a single 32-bit process this
is trivially true. If you ever build a 64-bit mod the same trick can fail
and you'll need a longer 64-bit absolute jump — not a concern for NFSMW
since it's 32-bit only.

### 10.8. Static vs runtime object pointers

Many of the addresses in this guide are vtable pointers (`.rdata`) — those
are stable across runs and the simplest to hook. Object pointers (like the
"this" for a specific widget instance) are runtime allocations and have
different addresses every launch. The right move there is to hook
`CHudWidgetArray_Tick` (vtable slot, stable) and from inside that hook
capture the `this` pointer your code is interested in. Don't hard-code
runtime allocations.

### 10.9. The `DAT_009885c8` gotcha

Per the per-frame call chain memory entry, the physics integrator is bound
to a runtime vtable slot at `0x0047c890` and the integrator step entry
lives behind `DAT_009885c8[+0x44]`. Don't try to patch the integrator at
its function address — patch the vtable slot instead so the engine picks
up your hook when it binds. Similar dynamic-binding traps exist in the
`SubsystemDtAccumulator` chain.

### 10.10. Distribute as a single `.asi`

Ultimate-ASI-Loader scans `app/scripts/` and loads everything it finds.
If you ship multiple `.asi` files, they all load — but conflicting hooks
on the same vtable slot will silently overwrite each other in load order.
Either consolidate your mods or coordinate via a shared init slot.

---

## Appendix A — Address quick reference

These addresses appear throughout this guide and trace to either
`docs/sdk_addrs.json` or one of the wave memory entries. The image base is
always `0x00400000`.

| Address     | Symbol                                            | Source |
|-------------|---------------------------------------------------|--------|
| `0x00406600` | `AIVehicle_BaseUpdate_vt1`                       | wave-16 |
| `0x00417a20` | `FilterHeliAltitudeVector`                       | wave-16 |
| `0x0042ab40` | `UpdateAIVehicleTraffic_OnDriving`               | wave-16 |
| `0x0042adb0` | `UpdateAIVehicleHelicopter_OnDriving`            | wave-16 |
| `0x0042ab80` | `SetAICopPursuitGoal`                            | cop AI memory |
| `0x00516be0` | `DispatchUIEventToNamedNode`                     | wave-17 |
| `0x00516c90` | `PostUIEventToNamedNode`                         | wave-17 |
| `0x00569570` | `CHudWidgetArray_SetActive` (vt[4])              | wave-13 |
| `0x005696c0` | `CHudWidgetArray_FlipVisibilityOnGameMasterChange` | wave-13 |
| `0x00566170` | `RadarDetector` Update                           | wave-12 |
| `0x005666a0` | `HeatMeterInRace` Update                         | wave-12 |
| `0x005668f0` | `CostToState` Update                             | wave-12 |
| `0x005669b0` | `Reputation` Update                              | wave-12 |
| `0x00568eb0` | `BustedMeter` Update (no-op)                     | wave-12 |
| `0x00569a50` | `Infractions` Update                             | wave-12 |
| `0x0057a4b0` | `RaceOverMessage` Update                         | wave-12 |
| `0x0057aee0` | `PursuitBoardInRace` Update                      | wave-12 |
| `0x0057b780` | `TimeExtension` Update                           | wave-12 |
| `0x0057bbc0` | `MenuZoneTrigger` Update                         | wave-12 |
| `0x0058ca30` | `CHudWidgetArray_Tick`                           | wave-13 |
| `0x005b7780` | `ScheduleUIDeferredEvent`                        | wave-17 |
| `0x005bbc00` | `DispatchUIEvent_ToSubscriberHandler`            | wave-17 |
| `0x005beaa0` | `DispatchUIEvent_ToTypeRegistrySubscribers`      | wave-17 |
| `0x005c1460` | `DrainUIDeferredEventQueue_PerFrame`             | wave-17 |
| `0x005c53c0` | `FE_PerFrameTick_DrainQueueAndUpdateChildren`    | wave-17 |
| `0x006596a0` | `ProcessGameStateMachine`                        | game-state memory |
| `0x006e9aa0` | `SetSpeedBreakerActive`                          | wave-11 |
| `0x006edc90` | `CheckSpeedBreakerAvailable`                     | wave-11 |
| `0x006edd10` | `HandleSpeedBreakerToggleRequest`                | wave-11 |
| `0x006edd60` | `UpdateSpeedBreakerEnergyTick`                   | wave-11 |
| `0x00891CF8` | `vtbl_AIVehicleTraffic`                          | wave-16 |
| `0x008920D8` | `vtbl_AIVehicleHelicopter`                       | wave-16 |
| `0x008a2538` | `CHudWidgetArray` vtable                         | wave-13 |
| `0x00925e70` | game-flow state record                           | game-state memory |
| `0x00937804` | `Tweak_InfiniteNOS`                              | sdk_addrs |
| `0x00988e1c` | `Tweak_InfiniteRaceBreaker`                      | sdk_addrs |

---

## Appendix B — Build templates

A minimal Makefile for any mod following the trainer pattern:

```make
CC      = i686-w64-mingw32-gcc
CFLAGS  = -m32 -Os -Wall -Wextra
LDFLAGS = -shared -static -static-libgcc -Wl,--kill-at
LIBS    = -lkernel32

TARGET  = my_mod.asi
SRC     = my_mod.c

all: $(TARGET)

$(TARGET): $(SRC)
	$(CC) $(CFLAGS) $(LDFLAGS) $(SRC) -o $(TARGET) $(LIBS)

install: $(TARGET)
	cp $(TARGET) "../../extracted/app/scripts/"

clean:
	rm -f $(TARGET) *.o
```

The `-Wl,--kill-at` flag strips the `@N` decoration from stdcall exports —
required for ASI loader compatibility. `-static` and `-static-libgcc`
ensure the resulting DLL has no runtime dependencies beyond `kernel32.dll`.

---

## Appendix C — Where to look next

Every claim in this guide is sourced from a memory entry in
`~/.claude/projects/.../memory/`. If you need deeper detail on any
subsystem, the canonical references are:

| Topic | Memory entry |
|---|---|
| SpeedBreaker chain | `project_speedbreaker_userkey_chain.md` |
| HUD walker | `project_hud_walker_discovered.md` |
| HUD widget internals | `project_hud_widget_internals.md` |
| FNG dispatch | `project_fng_dispatch_complete.md` |
| AI vtables | `project_ai_vehicle_vtables.md` |
| Game state machine | `project_game_state_machine.md` |
| Attribute schema | `project_attribute_schema.md` |
| Cop AI / pursuit | `project_cop_ai_pursuit.md` |
| Physics integrator | `project_eagl_physics.md` |
| Per-frame call chain | `project_perframe_call_chain.md` |
| Render pipeline | `project_render_pipeline.md` |
| Streamer anchors | `project_streamer_anchors.md` |
| Input subsystem | `project_input_subsystem.md` |
| Allocator architecture | `project_allocator_architecture.md` |

For the address-only side, `docs/sdk_addrs.json` is the authoritative source
imported from NFSPluginSDK (BSD-3) — every Tweak/Draw global in this guide
ultimately comes from that file.
