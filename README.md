# NFSMW Reverse-Engineering Project

A community reverse-engineering, documentation, and modding-tools project for **Need For Speed Most Wanted (2005)** (PC retail, `speed.exe`, PE32 i386, MSVC 7.10, image base `0x00400000`, 26,316 functions).

> **Status (2026-05-15)**: 53 memory entries covering every major subsystem, **294 / 345 (85.2%) attribute names cracked**, 6,664 functions named in Ghidra (25.32 %), validated by a working ASI mod (`mods/infinite_trainer/`). All 5 of the original "mystery" attribute hashes solved. **HUD subsystem fully reverse-engineered end-to-end** (waves 8–17): walker, 24-widget slot map, per-widget internals, FNG event-bus full dispatch chain.

## What this repo contains

```
.
├── README.md                    ← you are here
├── LICENSE                      ← BSD-3
├── docs/                        ← Documentation, schemas, indices (the core deliverable)
│   ├── ARCHITECTURE.md          ← 817-line canonical reference
│   ├── ANTI_RE_AND_PATTERNS.md  ← 18 anti-RE techniques + how we beat each
│   ├── PROGRESS.md              ← Wave-by-wave session log
│   ├── attribute_hashes.md      ← attributes.bin schema + per-type crack tables
│   ├── attribute_cracks_verified.json  ← 294 hash→name pairs (re-hash verified)
│   ├── sdk_addrs.json           ← 181 hardcoded addresses from NFSPluginSDK
│   ├── sdk_enums.json           ← 65 enum definitions
│   ├── sdk_structs.json         ← 245 struct definitions (1,712 fields)
│   ├── renames.csv              ← 6,513 Ghidra-named functions
│   ├── nfsplugin_sdk_mw05/      ← Mirrored BSD-3 SDK headers (berkayylmao)
│   ├── GHIDRA_MCP_ENDPOINTS.md  ← Tooling reference (Ghidra HTTP plugin)
│   ├── DEBUGGER_PLAN.md         ← Wine + gdbserver attach walkthrough
│   └── plan.txt                 ← Project plan / status board
├── tools/                       ← Linux-native CLI + scripts
│   └── nfsmw-tool/              ← Pure-Python multi-command CLI
│       ├── nfsmw_tool.py        ← Hash, JDLZ decompress, save verify, SDK lookup, etc.
│       ├── Makefile
│       └── README.md
└── mods/                        ← Proof-of-concept mods
    └── infinite_trainer/        ← Working .asi (Tweak_InfiniteNOS + Tweak_InfiniteRaceBreaker)
        ├── nfsmw_trainer.c
        ├── Makefile             ← Cross-compiles via i686-w64-mingw32-gcc
        └── README.md
```

## Headline findings

| Finding | Reference |
|---|---|
| **bChunk hash = Bob Jenkins mix3 (1996), seed `0xABCDEF00`** — not DJB2/FNV | [`docs/ANTI_RE_AND_PATTERNS.md`](docs/ANTI_RE_AND_PATTERNS.md) §1 |
| **Script VM is vanilla Lua 5.0.2** — confirmed by error-string match | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) wave-5 section |
| **JDLZ v0x02** algorithm fully RE'd from `speed.exe @ 0x64db40` | [`tools/nfsmw-tool/nfsmw_tool.py`](tools/nfsmw-tool/nfsmw_tool.py) `jdlz_decompress()` |
| **Save files use MD5 trailer** (not CRC) — IV constants verified | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) §wave-5 save/load |
| **Cutscenes use On2 VP6 + MAD audio**, not Bink | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) §wave-5 cutscenes |
| **AI doesn't draft and doesn't use nitrous** — "slipstream" is just rubber-banding | [`docs/ANTI_RE_AND_PATTERNS.md`](docs/ANTI_RE_AND_PATTERNS.md) §14 |
| **Drift mode is NOT in MW** — leftover Underground-era string | [`docs/ANTI_RE_AND_PATTERNS.md`](docs/ANTI_RE_AND_PATTERNS.md) §14 |
| **NO physics worker thread** — integrator runs inline on main thread | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) wave-9 correction |
| All 5 original mystery hashes cracked: AUTO_SIMPLIFY, BEHAVIORS, SimplePhysics, ExplosionEffect, DROPOUT | [`docs/attribute_cracks_verified.json`](docs/attribute_cracks_verified.json) |
| **HUD per-frame walker** = `CHudWidgetArray_Tick @ 0x58ca30` (vt[1] of vtable @ 0x8a2538); inline iteration of 11 fixed slots; mode-filter via widget[6..9] masks | [`docs/wave13_hud_walker.md`](docs/wave13_hud_walker.md) |
| **24 HUD widgets** mapped to exact CHudWidgetArray storage offsets (+0x2c0..+0x32c). Only 10 walker-ticked; 14 are FNG-bus / passive | [`docs/wave14_hud_slot_map.md`](docs/wave14_hud_slot_map.md) |
| **BustedMeter is a passive widget** — Update is no-op; external writer pokes the data into the FNG | [`docs/hud_widget_decomps/BustedMeter_Update.txt`](docs/hud_widget_decomps/BustedMeter_Update.txt) |

## Quick start

### Install the CLI

```bash
cd tools/nfsmw-tool
make install                    # symlinks ~/.local/bin/nfsmw-tool
nfsmw-tool stats                # show project coverage
```

### Compute / look up a bChunk hash

```bash
$ nfsmw-tool hash MASS
bChunk("MASS") = 0x4A56503D

$ nfsmw-tool lookup 0xC2094707
0xC2094707 = YAW_SPEED  (Float-typed attribute)
```

### Decompress a JDLZ bundle

```bash
$ nfsmw-tool jdlz /path/to/GLOBAL/GLOBALB.LZC
Decompressed 2803648 bytes → /path/to/GLOBAL/GLOBALB.LZC.bin
```

### Build the infinite-NOS trainer

```bash
sudo pacman -S mingw-w64-gcc              # or apt install gcc-mingw-w64-i686
cd mods/infinite_trainer
make                                       # produces nfsmw_trainer.asi
cp nfsmw_trainer.asi /path/to/NFSMW/scripts/
```

Run NFSMW, race, use NOS — never depletes. Validates the entire docs-to-runtime chain.

## How to use this repo for your own modding

1. **Find what you want to change.** Use [`docs/attribute_hashes.md`](docs/attribute_hashes.md) to find an attribute name (e.g. `MASS`, `TopSpeed`, `RubberBandGain`), or [`docs/sdk_addrs.json`](docs/sdk_addrs.json) to find a global (e.g. `Tweak_InfiniteNOS`, `DrawCars`).
2. **Compute the hash if needed.** `nfsmw-tool hash <name>` gives you the 32-bit key.
3. **Find the read/write site in Ghidra.** Open `speed.exe`, search for the constant. With our 460 disassembly annotations applied, the hashes are pre-labeled with their cracked names.
4. **Write a `.asi` mod.** Copy `mods/infinite_trainer/` as a template. Replace the address constants. `make install`.

## How this work was done

Eight reverse-engineering "waves" (parallel agent + direct work) over ~6 days:

| Wave | Date | Achievement |
|---|---|---|
| Baseline | pre-2026-05-09 | ~6,338 fns named, JDLZ algorithm, attributes.bin schema |
| Wave-1 | 2026-05-09 | 10 subsystems mapped (allocator, world streamer, particles, audio, customization, FNG, network, damage, input, replay) |
| Wave-2/3/4 | mid-May | EAGL physics anchor, Cop AI, Render passes, Animation, Career, Script VM |
| Wave-5 | 2026-05-14 | NFSPluginSDK integration (178 headers), Lua 5.0 confirmed, 8 more subsystems mapped |
| Wave-6 | 2026-05-14 | +50 attribute cracks (manual + compound wordlists) → 121 / 345 (35 %) |
| Wave-7 | 2026-05-14 | Community NFS hash DB integration (Attribulator + OpenNFSTools + nfsu2-re) → 294 / 345 (85.2 %); all 5 mystery hashes cracked |
| Wave-8 | 2026-05-14 | Input-binding system fully mapped, 13 HUD widgets mapped, prior misreadings corrected |
| Wave-9 | 2026-05-14 | Infinite-NOS trainer built + validated, EAGL physics correction (no worker thread), event-bus API mapped, semantic roles for 15 hashes |

See [`docs/PROGRESS.md`](docs/PROGRESS.md) for the full log.

## What this repo does NOT contain

- **No copyrighted game assets.** No `speed.exe`, no bundles, no music, no models. You need a legally-acquired copy of the game to use these tools.
- **No game installer.** Bring your own copy.
- **No PDB / source leak.** Everything here is community-derived from a clean-room reverse-engineering effort.

## Acknowledgments

- **berkayylmao** for the [NFSPluginSDK](https://github.com/berkayylmao/NFSPluginSDK) — BSD-3 plugin SDK with 178 type headers. Saved months of work.
- **NFSTools/Attribulator** for [the community attribute hash database](https://github.com/NFSTools/Attribulator) (43,102 names) — single-pass match took attribute crack rate from 35 % to 85 %.
- **MWisBest/OpenNFSTools** for [`res/hashes.txt`](https://github.com/MWisBest/OpenNFSTools) — curated MW-specific names.
- **yugecin/nfsu2-re** for the [runtime-trace hash dumps](https://github.com/yugecin/nfsu2-re).
- The broader NFS modding community for a decade of accumulated knowledge.

## License

BSD-3-Clause. See [`LICENSE`](LICENSE).

## Contributing

PRs welcome. Particularly valuable:

- The remaining 51 uncracked attribute hashes (likely need a PDB/source leak)
- Live-debugger capture of the physics integrator function pointer (`(*DAT_009885c8)[+0x44]`)
- HUD per-widget Update function verification (14 candidates from wave-9)
- Additional mod templates beyond the trainer

See [`docs/PROGRESS.md`](docs/PROGRESS.md) §"Open threads" for a prioritized list.
