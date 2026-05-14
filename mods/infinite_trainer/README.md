# NFSMW Infinite Trainer (proof-of-concept)

A minimal .asi mod that demonstrates the NFSMW reverse-engineering documentation in `docs/` is **actionable** — i.e. you can write a working mod using only the names and addresses we've recovered.

## What it does

Patches 2 globals on game-load so they stay true throughout the session:

| Global | Address | Effect |
|---|---|---|
| `Tweak_InfiniteNOS` | `0x937804` | NOS never depletes |
| `Tweak_InfiniteRaceBreaker` | `0x988E1C` | GameBreaker (SpeedBreaker) never depletes |

Both addresses come from `docs/sdk_addrs.json`, extracted from the NFSPluginSDK by berkayylmao (BSD-3 licensed).

## Build

The mod is a 32-bit PE DLL renamed to `.asi`. Two build paths:

### Option A — MinGW-w64 (preferred)

```bash
pacman -S mingw-w64-gcc       # Arch
# or:  apt install gcc-mingw-w64-i686     (Debian/Ubuntu)
make mingw
```

### Option B — winegcc

```bash
make                          # uses winegcc, already installed in the dev env
```

Either produces `nfsmw_trainer.asi`.

## Install

```bash
make install
# or manually:
cp nfsmw_trainer.asi /path/to/Magipack/extracted/app/scripts/
```

The Magipack bundles **Ultimate-ASI-Loader** as `app/dinput8.dll` — it loads any `.asi` file in `app/scripts/` on game start.

## Verify

1. Run speed.exe (Wine: `wine speed.exe`)
2. Start a race
3. Use NOS — the bar should never deplete
4. Use SpeedBreaker (default key: RCtrl or G) — the meter should never deplete
5. Optional: capture `OutputDebugString` output via DebugView++ or Wine's `WINEDEBUG=+tid` to see the patch-applied message

## Why this mod is interesting (not just for the gameplay)

It's the **validation step** for ~30 days of reverse-engineering work. Every layer of the docs is exercised:

| Layer | What's tested |
|---|---|
| `docs/ARCHITECTURE.md` module map | Image base verification (`0x00400000`) |
| `docs/sdk_addrs.json` | The 3 hardcoded addresses |
| `docs/nfsplugin_sdk_mw05/MW05.h` Variables namespace | Type info (bool for NOS, etc.) |
| `docs/ANTI_RE_AND_PATTERNS.md` §12 | "multiplex.cfg-style runtime gates" pattern |

If this mod works on the user's machine, every claim in the RE docs about these specific addresses is **proven correct empirically**. If it crashes / has no effect, that tells us exactly which doc claim is wrong.

## Extending

Other globals available immediately from `docs/sdk_addrs.json`:

- `0x903320 DrawCars` (bool)
- `0x903324 DrawCarsReflections` (bool)
- `0x903328 DrawCarShadow` (bool)
- `0x57CAA8 DrawHUD` (bool)
- `0x91CAE4 IsFadeScreenOn` (bool)
- `0x901AEC Tweak_GameBreakerCollisionMass` (float, default 2.0)
- `0x901B1C Tweak_GameSpeed` (float, default 1.0 — set to 2.0 for fast-forward, 0.5 for slow-mo!)
- `0x91112C NOSFOVWidening` (uint16, default 0x666)
- `0x926064 SkipFE` (bool — skip front-end menus, jump straight to race)

To add features, just call `write_byte()` / `write_float()` with the appropriate address. The `validate_speed_exe()` guard ensures the mod won't apply if loaded into a non-NFSMW process.

## License

This trainer source is BSD-3 (matches NFSPluginSDK).
