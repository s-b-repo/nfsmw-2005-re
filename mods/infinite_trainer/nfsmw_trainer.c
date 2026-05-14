/*
 * NFSMW Infinite Trainer — proof-of-concept mod
 *
 * Demonstrates that the reverse-engineering documentation in docs/ is actionable:
 * applies 3 tweaks by writing to globals whose addresses come from the
 * NFSPluginSDK address index (docs/sdk_addrs.json).
 *
 * Drop the built .asi into app/scripts/ — the Magipack's bundled Ultimate-ASI-
 * Loader (dinput8.dll) will load it on game start.
 *
 * Effects:
 *   - Infinite NOS (Tweak_InfiniteNOS @ 0x937804)
 *   - Infinite Speedbreaker / Race-breaker (Tweak_InfiniteRaceBreaker @ 0x988E1C)
 *   - Disable cops at FE skip (SkipFEDisableCops @ 0x8F86C0) — already true by
 *     default; we leave it
 *
 * Build:
 *   make
 *
 * Install:
 *   cp nfsmw_trainer.asi /path/to/app/scripts/
 *
 * Author: NFSMW RE project, 2026-05-14
 */

#include <windows.h>
#include <stdio.h>
#include <stdint.h>

/* All addresses below are extracted from NFSPluginSDK by berkayylmao (BSD-3) —
 * see docs/sdk_addrs.json and docs/nfsplugin_sdk_mw05/MW05.h Variables namespace.
 * The game image-base is 0x00400000 and Wine maps speed.exe 1:1 at that address
 * (verified in docs/ARCHITECTURE.md module map), so the absolute addresses
 * below are directly usable.
 */
#define TWEAK_INFINITE_NOS          0x00937804u  /* bool — false by default */
#define TWEAK_INFINITE_RACEBREAKER  0x00988E1Cu  /* bool — false by default */
#define TWEAK_GAME_SPEED            0x00901B1Cu  /* float — 1.0 default */
#define DRAW_HUD                    0x0057CAA8u  /* bool — true default */
#define WINDOW_HAS_LOST_FOCUS       0x00982C50u  /* bool */
#define IS_IN_NIS                   0x0091606Cu  /* bool — cutscene flag */

/* Write helpers — temporarily relax page protection to write. */
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

static BYTE read_byte(uintptr_t addr) { return *(BYTE*)addr; }

/* Verify we're actually inside speed.exe before patching. The PE image-base in
 * the loaded module's DOS+NT headers must say 0x00400000. */
static int validate_speed_exe(void) {
    HMODULE main_module = GetModuleHandleA(NULL);
    if (!main_module) return 0;
    /* Read e_lfanew at offset 0x3C of the DOS header */
    DWORD nt_offset = *(DWORD*)((BYTE*)main_module + 0x3C);
    /* PE header signature at +0, OptionalHeader at +0x18, ImageBase at +0x18+0x1C = +0x34 */
    DWORD image_base = *(DWORD*)((BYTE*)main_module + nt_offset + 0x34);
    return image_base == 0x00400000;
}

static DWORD WINAPI trainer_thread(LPVOID lpv) {
    (void)lpv;
    /* Wait 2 seconds for the game to finish its own init pass. We don't want to
     * touch globals before the engine has had a chance to initialize them. */
    Sleep(2000);

    if (!validate_speed_exe()) {
        OutputDebugStringA("[NFSMW Trainer] ERROR: not inside speed.exe — refusing to patch\n");
        return 1;
    }

    /* Read-before-write so we can log what we're changing. */
    BYTE old_nos    = read_byte(TWEAK_INFINITE_NOS);
    BYTE old_brkr   = read_byte(TWEAK_INFINITE_RACEBREAKER);

    write_byte(TWEAK_INFINITE_NOS, 1);
    write_byte(TWEAK_INFINITE_RACEBREAKER, 1);

    char msg[256];
    snprintf(msg, sizeof(msg),
        "[NFSMW Trainer] Patched: TweakInfiniteNOS %d -> 1, TweakInfiniteRaceBreaker %d -> 1\n",
        old_nos, old_brkr);
    OutputDebugStringA(msg);
    return 0;
}

BOOL WINAPI DllMain(HINSTANCE hinst, DWORD reason, LPVOID reserved) {
    (void)reserved;
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(hinst);
        /* Spawn a worker so we don't block DllMain. Most ASIs work this way. */
        HANDLE h = CreateThread(NULL, 0, trainer_thread, NULL, 0, NULL);
        if (h) CloseHandle(h);
    }
    return TRUE;
}
