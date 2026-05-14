# nfsmw-tool

Linux-native CLI for **Need For Speed Most Wanted (2005)** reverse-engineering work. Pure Python — no compilation needed.

Exercises every layer of the repo docs:

| Subcommand | Uses |
|---|---|
| `hash <name>` | bChunk = Bob Jenkins mix3, seed `0xABCDEF00` |
| `lookup <hash>` | Reverse-lookup against the 294 cracked names |
| `jdlz <file>` | Decompress NFSMW JDLZ v0x02 bundles |
| `attrs <attributes.bin>` | Dump the attributes.bin schema with type + cracked names |
| `verify-save <file>` | Verify the MD5 trailer of an NFSMW save profile |
| `sdk <addr\|name>` | Lookup against the NFSPluginSDK 181-entry address index |
| `stats` | Show project coverage stats |

## Install

```bash
make install              # installs to ~/.local/bin/nfsmw-tool (symlink)
# or just run directly:
python3 nfsmw_tool.py --help
```

Requires Python 3.10+. No external dependencies.

## Examples

```bash
# Compute the bChunk hash of any name
$ nfsmw-tool hash MASS
bChunk("MASS") = 0x4A56503D

$ nfsmw-tool hash AUTO_SIMPLIFY
bChunk("AUTO_SIMPLIFY") = 0xB5C0DAC8

# Reverse-lookup a hash
$ nfsmw-tool lookup 0x4A56503D
0x4A56503D = MASS  (Float-typed attribute)

$ nfsmw-tool lookup 0xB5C0DAC8
0xB5C0DAC8 = AUTO_SIMPLIFY  (Float-typed attribute)

# Decompress a JDLZ bundle (works on any NFSMW LZC)
$ nfsmw-tool jdlz /path/to/GLOBAL/GLOBALB.LZC
Decompressed 2803648 bytes → /path/to/GLOBAL/GLOBALB.LZC.bin

# Dump the attributes.bin schema
$ nfsmw-tool attrs /path/to/GLOBAL/attributes.bin | head -10
# attributes.bin schema dump from attributes.bin
# rows starting at offset 0x18000 (16 bytes each)
# format: HASH  TYPE                 NAME (if cracked)
  0x4A56503D  Float                MASS
  0xFEF5CC35  Float                STEERING
  0x96E40580  Float                Power
  0x81625B35  Float                Life
  ...

# Verify an NFSMW save file
$ nfsmw-tool verify-save "~/Documents/NFS Most Wanted/MyProfile"
OK  payload 64432 bytes  MD5 a1b2c3...

# Find SDK function by name
$ nfsmw-tool sdk StringToKey
  0x454640  function Attrib_StringToKey  ::  std::uint32_t (__cdecl *)(const char*)

# Or by address
$ nfsmw-tool sdk 0x454640
  0x454640  function Attrib_StringToKey  ::  std::uint32_t (__cdecl *)(const char*)

# Project stats
$ nfsmw-tool stats
NFSMW Reverse-Engineering Project — Stats
==================================================
Attribute names cracked:        294 / 345 = 85.2%
NFSPluginSDK addresses:         181
  Functions:                    153
  Globals:                      28
...
```

## How it knows everything

The tool reads from this repo's `docs/` directory at runtime:

- `docs/attribute_cracks_verified.json` — 294 verified `hash → name` entries
- `docs/sdk_addrs.json` — NFSPluginSDK address index
- `docs/attrib_table.json` — per-type attribute breakdown (if present)

This means **anyone who clones the repo gets the full DB for free**. Update the docs and the tool's outputs update with them.

## Algorithms

### bChunk (Bob Jenkins mix3)

The hash NFSMW uses for every attribute/event/asset name. Verified by computing `bChunk("BASE") == 0xA6B47FAC` and matching a constant in `speed.exe`. See [`docs/ANTI_RE_AND_PATTERNS.md`](../../docs/ANTI_RE_AND_PATTERNS.md) §1.

### JDLZ v0x02

EA's in-house LZ77 variant, reverse-engineered from `speed.exe @ 0x64db40` (see [`docs/ANTI_RE_AND_PATTERNS.md`](../../docs/ANTI_RE_AND_PATTERNS.md) §2). The Python implementation here is byte-identical with the in-game decompressor on all 4 shipped LZC bundles (12.5 MB total).

### Save-file MD5

NFSMW saves use an MD5 trailer (not CRC — that misconception was caught in wave-5). Format: `[payload][0x00 × 0x10][16-byte MD5 of payload]`. Confirmed by matching IV constants `0x67452301 0xefcdab89 0x98badcfe 0x10325476` and the RFC-1321 T-table in `ComputeMd5OfSaveBuffer @ 0x57f920`.

## License

BSD-3 (matches NFSPluginSDK).
