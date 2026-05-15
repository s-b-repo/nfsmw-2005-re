# NFSMW Mod Recipes

Copy-paste-ready C snippets that target globals and functions in `speed.exe`
via the NFSPluginSDK address index (`docs/sdk_addrs.json`).

Each recipe is a single patch you drop into a copy of
`mods/infinite_trainer/nfsmw_trainer.c`. The reference trainer already supplies
`write_byte`, `write_float`, `validate_speed_exe`, and the threading shell —
recipes below only show the **patch lines** (or a small extra helper) that go
inside `trainer_thread()` (or, for hook-style recipes, in a polling loop).

> All absolute addresses below assume the standard NFSMW PE image-base
> `0x00400000` and the Magipack distribution's bundled `speed.exe`. Verify
> with `validate_speed_exe()` before writing (the reference trainer does
> this for you). Image-base verification is the difference between "infinite
> NOS" and "instant crash".

---

## Shared boilerplate (used by every recipe)

```c
#include <windows.h>
#include <stdio.h>
#include <stdint.h>

static void write_byte(uintptr_t addr, BYTE v) {
    DWORD old; if (VirtualProtect((LPVOID)addr, 1, PAGE_EXECUTE_READWRITE, &old)) {
        *(BYTE*)addr = v; VirtualProtect((LPVOID)addr, 1, old, &old);
    }
}
static void write_word(uintptr_t addr, WORD v) {
    DWORD old; if (VirtualProtect((LPVOID)addr, 2, PAGE_EXECUTE_READWRITE, &old)) {
        *(WORD*)addr = v; VirtualProtect((LPVOID)addr, 2, old, &old);
    }
}
static void write_int(uintptr_t addr, DWORD v) {
    DWORD old; if (VirtualProtect((LPVOID)addr, 4, PAGE_EXECUTE_READWRITE, &old)) {
        *(DWORD*)addr = v; VirtualProtect((LPVOID)addr, 4, old, &old);
    }
}
static void write_float(uintptr_t addr, float v) {
    DWORD old; if (VirtualProtect((LPVOID)addr, 4, PAGE_EXECUTE_READWRITE, &old)) {
        *(float*)addr = v; VirtualProtect((LPVOID)addr, 4, old, &old);
    }
}
static BYTE  read_byte (uintptr_t a) { return *(BYTE *)a; }
static WORD  read_word (uintptr_t a) { return *(WORD *)a; }
static DWORD read_int  (uintptr_t a) { return *(DWORD*)a; }
static float read_float(uintptr_t a) { return *(float*)a; }
```

The recipes below assume these helpers are in scope.

---

## Recipe 1 — Infinite NOS

**Description.** Holds the NOS bottle full so the player never depletes nitrous.
This is the canonical recipe shown in `mods/infinite_trainer/nfsmw_trainer.c`.

**Address / type.**
`Tweak_InfiniteNOS @ 0x00937804` — `bool` (1 byte). Default `0`.

**Snippet.**
```c
#define TWEAK_INFINITE_NOS  0x00937804u

write_byte(TWEAK_INFINITE_NOS, 1);
```

**Side effects.** None — engine treats the flag as a master override at the
gauge sampling layer, so HUD, FOV widening, and physics boost all stay in sync.

**Verify in-game.** Start any race, hit NOS, watch the meter stay full.

---

## Recipe 2 — Infinite SpeedBreaker / GameBreaker

**Description.** Player can hold the bullet-time SpeedBreaker indefinitely.

**Address / type.**
`Tweak_InfiniteRaceBreaker @ 0x00988E1C` — `bool` (1 byte). Default `0`.

**Snippet.**
```c
#define TWEAK_INFINITE_RACEBREAKER  0x00988E1Cu

write_byte(TWEAK_INFINITE_RACEBREAKER, 1);
```

**Side effects.** The meter still ticks visually, but the gate that disables
input is bypassed. Pair with `Tweak_GameBreakerCollisionMass @ 0x901AEC`
(`float`) to also make rams feel heavier while SpeedBreaker is active.

**Verify in-game.** Press the SpeedBreaker key; release; press again
immediately — should reactivate without a cooldown.

---

## Recipe 3 — Game speed 2x

**Description.** Globally accelerates simulation by 2x. Affects physics tick,
animation rate, AI thinking, and audio pitch shift inside the engine layer.

**Address / type.**
`Tweak_GameSpeed @ 0x00901B1C` — `float`. Default `1.0`.

**Snippet.**
```c
#define TWEAK_GAME_SPEED  0x00901B1Cu

write_float(TWEAK_GAME_SPEED, 2.0f);
```

**Side effects.**
- AI gets the same speedup, so opponents are *not* easier.
- Replay (joylog) capture diverges if you toggle this mid-race — replays
  recorded at 2x will desync at 1x.
- Physics determinism degrades at >2x (collision LOD assumes default `dt`).

**Verify in-game.** Time-trial a known route; halve your wall-clock time.

---

## Recipe 4 — Game speed 0.5x (cinematic)

**Description.** Slow the world to half speed — useful for capture footage,
trick shots, or inspecting crashes frame-by-frame.

**Address / type.** Same as recipe 3 — `Tweak_GameSpeed @ 0x00901B1C`.

**Snippet.**
```c
write_float(0x00901B1Cu, 0.5f);
```

**Side effects.** Audio pitch shifts down a perfect fifth; subtitle/cutscene
timing breaks since NIS scripts assume `dt=1.0`. Don't enable during NIS
(`IsInNIS @ 0x9106C` is your guard).

**Verify in-game.** Engine note drops about an octave; tachometer needle
visibly lags real RPM.

---

## Recipe 5 — Skip front-end menus

**Description.** Boots directly into the open world with the SkipFE player car,
bypassing the main menu / save-select / "press start" stack.

**Address / type.**
`SkipFE @ 0x00926064` — `bool`. Default `0`.

**Snippet.**
```c
#define SKIP_FE        0x00926064u
#define SKIP_FE_CAR    0x008F86A8u   /* const char* — name string of car */

write_byte(SKIP_FE, 1);
/* Optional: lock the player car. The pointer is a `const char*` — the
 * engine reads it once at boot, so we can just overwrite the pointer with
 * a hand-built string literal we ship inside our .asi: */
static const char k_default_skip_car[] = "PORSCHE911GT2";
write_int(SKIP_FE_CAR, (DWORD)(uintptr_t)k_default_skip_car);
```

**Side effects.** No save is loaded — career data is fresh-default. Use with
recipes 6/7 to also disable cops/traffic if you just want a sandbox.

**Verify in-game.** Game window appears, splash plays, you spawn directly in
the world map (no UI). Check `OutputDebugStringA` for the patch log.

---

## Recipe 6 — No cops

**Description.** Disables cop AI on the SkipFE path. **Only effective when
`SkipFE @ 0x926064` is also `1`** — without SkipFE the front-end loader
re-initializes the cop manager from save data and clobbers this flag.

**Address / type.**
`SkipFEDisableCops @ 0x008F86C0` — `bool`. Default `0`.

**Snippet.**
```c
#define SKIP_FE              0x00926064u
#define SKIP_FE_NO_COPS      0x008F86C0u

write_byte(SKIP_FE, 1);              /* prerequisite */
write_byte(SKIP_FE_NO_COPS, 1);
```

For a *runtime* cop kill (after the game has already loaded a save), call
`SetCopsEnabled @ 0x604F40` instead:

```c
typedef void (__cdecl *SetCopsEnabled_t)(bool);
((SetCopsEnabled_t)0x00604F40)(false);
```

**Side effects.** Cop chases never trigger; pursuit-related career events that
gate progression on `BUSTED`/`EVADED` cannot complete.

**Verify in-game.** Run reds at 200 km/h in the open world for 60 s — no
sirens, no `TheOneCopManager @ 0x90D5F4` activity.

---

## Recipe 7 — No traffic

**Description.** Disables AI traffic on the SkipFE path. Open world stays
populated with props and racers but no civilian cars.

**Address / type.**
`SkipFEDisableTraffic @ 0x00926094` — `bool` (the SDK calls it
`g_bSkipFEDisableTraffic` in some headers; same global). Default `0`.

For density without disabling outright, use the companion float:
`SkipFETrafficDensity @ 0x00926090` — `float`, 0.0..1.0.

**Snippet.**
```c
#define SKIP_FE                  0x00926064u
#define SKIP_FE_NO_TRAFFIC       0x00926094u
#define SKIP_FE_TRAFFIC_DENSITY  0x00926090u

write_byte(SKIP_FE, 1);
write_byte(SKIP_FE_NO_TRAFFIC, 1);
/* Or, instead of the hard kill, reduce density to 10%: */
/* write_float(SKIP_FE_TRAFFIC_DENSITY, 0.1f); */
```

**Side effects.** "Near-miss" cash bonuses can't be earned. Career-bound
challenges that require traffic interactions stall.

**Verify in-game.** Drive five blocks of downtown Rockport — empty road.

---

## Recipe 8 — Hide HUD

**Description.** Toggles the HUD draw pass off — clean screenshots, video
capture, photo mode poor man's edition.

**Address / type.**
`DrawHUD @ 0x0057CAA8` — `bool`. Default `1`.

**Snippet.**
```c
#define DRAW_HUD  0x0057CAA8u

write_byte(DRAW_HUD, 0);
```

To bind it to a key (toggle on F10), wrap in a polling thread:

```c
static DWORD WINAPI hud_toggle_loop(LPVOID p) {
    BYTE wanted = 0;
    SHORT was_down = 0;
    for (;;) {
        SHORT now = GetAsyncKeyState(VK_F10) & 0x8000;
        if (now && !was_down) {
            wanted ^= 1;
            write_byte(DRAW_HUD, wanted ? 0 : 1);
        }
        was_down = now;
        Sleep(30);
    }
}
```

**Side effects.** Minimap, lap counter, tachometer all vanish — you fly blind.
NIS overlays (mission briefs) still draw because they ride a different layer.

**Verify in-game.** Speedometer and minimap disappear.

---

## Recipe 9 — No reflections (FPS boost)

**Description.** Skips the per-car cube-map reflection pass — measurable FPS
gain on weak GPUs, and looks acceptable on matte paint jobs.

**Address / type.**
`DrawCarsReflections @ 0x00903324` — `bool`. Default `1`.

**Snippet.**
```c
#define DRAW_CARS_REFLECTIONS  0x00903324u

write_byte(DRAW_CARS_REFLECTIONS, 0);
```

**Side effects.** Chrome and gloss paints look flat. Cinematics that rely on
reflections for storytelling (e.g. windshield-reflected NPC dialogue cars) lose
their visual reference but don't break.

**Verify in-game.** Park near a glass building — your roof doesn't show the
skyline anymore.

---

## Recipe 10 — Disable car shadows

**Description.** Skips the dynamic car shadow pass. Bigger FPS win than
reflections on integrated GPUs.

**Address / type.**
`DrawCarShadow @ 0x00903328` — `bool`. Default `1`.

**Snippet.**
```c
#define DRAW_CAR_SHADOW  0x00903328u

write_byte(DRAW_CAR_SHADOW, 0);
```

Pair with recipe 9 for maximum savings:

```c
write_byte(0x00903324u, 0);   /* DrawCarsReflections */
write_byte(0x00903328u, 0);   /* DrawCarShadow */
```

**Side effects.** Cars look like they're floating; cone of doubt about whether
the car is grounded during big jumps. Static world shadows (lightmap baked)
remain.

**Verify in-game.** No oval shadow under any car in bright daylight.

---

## Recipe 11 — NOS FOV widening (aggressive)

**Description.** Increases the FOV-pump applied while NOS is active —
"speed-feel" enhancement.

**Address / type.**
`NOSFOVWidening @ 0x0091112C` — `std::uint16_t`. Default `0x0666` (~1638
fixed-point units). Aggressive value: `0x1500`.

**Snippet.**
```c
#define NOS_FOV_WIDENING  0x0091112Cu

write_word(NOS_FOV_WIDENING, 0x1500);
```

**Side effects.** Very-wide FOV during NOS can intermittently expose
out-of-LOD geometry at the screen edge (you'll see low-poly building swaps
mid-boost) and amplifies motion sickness on some users. The HUD anchor still
sits at its 1.0× position so the speedo "drifts" toward center.

**Verify in-game.** Spam NOS in a straight; the world should noticeably
"breathe" outward.

---

## Recipe 12 — Force first-person POV on FE skip

**Description.** When SkipFE is enabled, force the spawn camera to the bumper
(first-person) view rather than the user's last-saved POV preference.

**Address / type.**
`SkipFEPOVType @ 0x008F86C4` — `ePlayerSettingsCameras` enum, `int32` width.
Enum values (from `sdk_enums.json` / `MW05.h`):

| Value | Name |
|------:|------|
| 0 | Bumper |
| 1 | Hood |
| 2 | ChasePerformance |
| 3 | ChaseHeavy |
| 4 | ChaseTrailing |
| 5 | DriverCockpit |

**Snippet.**
```c
#define SKIP_FE_POV_TYPE  0x008F86C4u
#define SKIP_FE           0x00926064u

write_byte(SKIP_FE, 1);
write_int(SKIP_FE_POV_TYPE, 0);   /* 0 = Bumper */
```

**Side effects.** First-person mode disables some HUD elements automatically
(certain rear-view-mirror widgets aren't drawn). If you select an out-of-range
enum value the game falls back to ChasePerformance silently.

**Verify in-game.** Game spawns with the bumper camera; mouse-wheel toggling
through POVs cycles starting from Bumper.

---

## Recipe 13 — Skip a specific blacklist event (career flag patch)

**Description.** Mark a specific career milestone (e.g. a blacklist boss race)
as completed without actually running it. The career system is event-driven
(see `project_career_milestones`); MilestoneProgressEventConstructor reads from
the `CAREER_DATA` root that lives behind `cFrontEndDatabase::GetPlayerSettings
@ 0x91CF90`. We don't have a direct numeric global for "boss N done" in the
181-entry SDK index, so the recipe is *deferred-runtime*: we call the engine's
own AwardBonusCars / AwardRivalCar functions after a boss would normally drop
the unlock, then call the milestone broadcast to mark it complete.

**Approach.** Sequence the engine's own helpers — they update the CRC at
`MSG_R_BI_DATACRC` so the save remains valid.

**Snippet.**
```c
typedef void (__thiscall *AwardBonusCars_t)(void* fePlayerCarDB);
typedef void (__thiscall *AwardRivalCar_t)(void* fePlayerCarDB, uint32_t carStringKey);
typedef void* (__cdecl *GetPlayerSettings_t)(void);
typedef uint32_t (__cdecl *StringToKey_t)(const char*);

#define ADDR_GetPlayerSettings  0x0091CF90u
#define ADDR_AwardBonusCars     0x0056F0C0u
#define ADDR_AwardRivalCar      0x005A41E0u
#define ADDR_StringToKey        0x00454640u

/* Place inside trainer_thread() after Sleep(8000) — long enough for the
 * front-end DB to finish loading the save.  */
static void unlock_blacklist_n(int boss_index, const char *rival_car_name) {
    GetPlayerSettings_t GetSettings = (GetPlayerSettings_t)ADDR_GetPlayerSettings;
    StringToKey_t       Hash        = (StringToKey_t)ADDR_StringToKey;
    AwardBonusCars_t    AwardBonus  = (AwardBonusCars_t)ADDR_AwardBonusCars;
    AwardRivalCar_t     AwardRival  = (AwardRivalCar_t)ADDR_AwardRivalCar;

    void *db = GetSettings();
    if (!db) return;

    /* Hand the boss's pink-slip car directly to the player. */
    uint32_t car_hash = Hash(rival_car_name);
    AwardRival(db, car_hash);

    /* Then trigger the post-boss bonus drops (markers / blueprints / etc). */
    AwardBonus(db);

    (void)boss_index;   /* Hook for future milestone-broadcast extension */
}

/* Example: skip BL15 (the very first boss), grab his Corvette. */
unlock_blacklist_n(15, "CORVETTEC6");
```

**Side effects.** This *adds* a car to the player garage and triggers the
bonus drop chain, but does **not** mark every race in that boss's roster as
completed. To do that cleanly you also need to broadcast
`MSG_R_BI_DATACRC` — out of scope for this short recipe. Use this for "give me
the rival's car NOW" workflows, not for fully bypassing the career graph.

**Verify in-game.** Open the garage after applying — the rival's car is in
the inventory. Career screen still shows boss as not-yet-defeated.

---

## Recipe 14 — Camera-shake on hotkey

**Description.** Triggers the engine's built-in `ShakeCamera` impulse function
on a key press — usable for screenshot dramatics, debugging IK rigs, or just
as a meme button.

**Address / type.**
`ShakeCamera @ 0x0062B110` — `void __cdecl ShakeCamera(void)`. No arguments
(amplitude is read from a tuning global the function references internally).

**Snippet.**
```c
typedef void (__cdecl *ShakeCamera_t)(void);
#define ADDR_ShakeCamera  0x0062B110u

/* Spawn this thread from DllMain (or call it from trainer_thread after
 * the patches are applied). It taps the F11 key. */
static DWORD WINAPI shake_loop(LPVOID p) {
    ShakeCamera_t Shake = (ShakeCamera_t)ADDR_ShakeCamera;
    SHORT prev = 0;
    for (;;) {
        SHORT now = GetAsyncKeyState(VK_F11) & 0x8000;
        if (now && !prev) {
            Shake();
        }
        prev = now;
        Sleep(20);
    }
}

/* In DllMain DLL_PROCESS_ATTACH, after the trainer thread, also do:
 *   HANDLE h2 = CreateThread(NULL, 0, shake_loop, NULL, 0, NULL);
 *   if (h2) CloseHandle(h2);
 */
```

**Side effects.** Calling `ShakeCamera` outside an active gameplay camera
(e.g. mid-NIS, mid-pause, in front-end) is a NOP but cheap; verify the
gameplay camera is live (`StopUpdatingCamera @ 0x911020 == 0`,
`IsInNIS @ 0x91606C == 0`) before pressing if you want a guaranteed visible
effect.

**Verify in-game.** Press F11 while driving — sharp screen jolt as if you'd
just clipped a guardrail.

---

## Appendix A — Recipe index by address

| Recipe | Symbol | Addr | Type | Default | Patched |
|-------:|--------|------|------|--------:|--------:|
| 1 | `Tweak_InfiniteNOS`           | `0x937804` | `bool`     | 0       | 1       |
| 2 | `Tweak_InfiniteRaceBreaker`   | `0x988E1C` | `bool`     | 0       | 1       |
| 3 | `Tweak_GameSpeed`             | `0x901B1C` | `float`    | 1.0     | 2.0     |
| 4 | `Tweak_GameSpeed`             | `0x901B1C` | `float`    | 1.0     | 0.5     |
| 5 | `SkipFE`                      | `0x926064` | `bool`     | 0       | 1       |
| 6 | `SkipFEDisableCops`           | `0x8F86C0` | `bool`     | 0       | 1       |
| 7 | `SkipFEDisableTraffic`        | `0x926094` | `bool`     | 0       | 1       |
| 8 | `DrawHUD`                     | `0x57CAA8` | `bool`     | 1       | 0       |
| 9 | `DrawCarsReflections`         | `0x903324` | `bool`     | 1       | 0       |
| 10 | `DrawCarShadow`              | `0x903328` | `bool`     | 1       | 0       |
| 11 | `NOSFOVWidening`             | `0x91112C` | `uint16_t` | 0x0666  | 0x1500  |
| 12 | `SkipFEPOVType`              | `0x8F86C4` | enum int   | varies  | 0       |
| 13 | `(career flag)`              | runtime    | engine fn  | n/a     | n/a     |
| 14 | `ShakeCamera`                | `0x62B110` | `void()`   | n/a     | hotkey  |

---

## Appendix B — Compile + install

```bash
# from the repo root
cd mods/infinite_trainer
# edit nfsmw_trainer.c — paste one or more recipes into trainer_thread()
make                    # produces nfsmw_trainer.asi
cp nfsmw_trainer.asi /path/to/app/scripts/
```

Ultimate-ASI-Loader (the Magipack bundles it as `dinput8.dll`) sideloads any
`.asi` in `app/scripts/` on game start, runs your `DllMain`, and your patches
land before the player presses any key.

---

## Appendix C — Auto-generated trainers

For machine-driven mod generation, `tools/nfsmw-tool/generate_trainer.py`
emits a complete `nfsmw_trainer.c` source from a `[(addr, value, kind)]`
patch list. Use it like:

```bash
python3 tools/nfsmw-tool/generate_trainer.py \
    --out mods/infinite_trainer/nfsmw_trainer.c \
    --patch 0x937804:byte:1 \
    --patch 0x988E1C:byte:1 \
    --patch 0x901B1C:float:2.0
```

The generated source includes the standard ASI threading shell and the same
`validate_speed_exe` PE-base sanity check used by the reference trainer.

---

## Safety + style notes

- **Always** verify the image-base before patching (`validate_speed_exe`),
  otherwise a future loader change or a non-Magipack `speed.exe` will corrupt
  random heap pages.
- **Don't** patch a global from inside `DllMain` — Windows holds the loader
  lock; long writes deadlock under some ASI loaders. Spawn a worker thread.
- **Do** sleep ~2 s before applying — the engine zeroes some of these
  globals during its own boot. Patching too early gets overwritten.
- **Read-before-write** when logging, so you have a record of the original
  value for restoring if you ever ship an "undo".
- Recipe 13 (career flag) is the only one that *modifies player data on disk*
  (the save file CRC). Test with a backup save, not your real one.

That's the menu. Mix and match — the reference trainer is short specifically
so you can paste any of the above into `trainer_thread()` and rebuild in
under a minute.
