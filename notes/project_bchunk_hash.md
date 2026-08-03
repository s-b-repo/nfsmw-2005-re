---
name: NFSMW bChunk hash is Jenkins mix3 (not DJB2)
description: The "bChunk" hash at speed.exe!0x5cc240 is Bob Jenkins's 1996 mix3 hash with seed 0xABCDEF00, not a DJB2 variant
type: project
originSessionId: c4edf485-e85f-4e2f-ac31-e021ba66e8d6
---
The string-hash function at `speed.exe!0x5cc240` (now `BChunkHash_JenkinsMix3`) and its inner routine at `0x5cc090` (`BChunkHash_JenkinsMix3_Inner`) implement **Bob Jenkins's 1996 "hash" function (mix3)** — the ancestor of `lookup3`.

- Block size: **12 bytes** (3×u32 per round)
- State: `a = b = 0x9E3779B9` (golden-ratio constant), `c = initval`
- Seed: **`0xABCDEF00`** (the EA bChunk constant)
- Shift sequence (Jenkins-canonical): `13, 8, 13, 12, 16, 5, 3, 10, 15`
- Inner uses a custom calling convention: pointer in EAX, len/seed/len in ECX/EDX/stack

**Why this matters:** Earlier notes called this "DJB2 ×33". They were wrong — DJB2 doesn't have a 12-byte block mix. Don't waste time on `(h * 33) ^ c` when reversing attribute names; you need a real Jenkins mix3 implementation.

**Verified by hash-cracking:**
- `0xA6B47FAC = bChunk("BASE")` — found by hashing all binary strings; matches the magic type-tag cookie passed to `RigidBody_AllocAndInitFromAttributes` (0x6895a0). "BASE" is the EAGL root type-class tag.

**Why:** Need a working hash to reverse attribute names like `0xEE0011E3` and the type-registry keys threaded through `LookupTypeRegistryEntry` / `LookupAttributeByHash`. Many keys won't crack against EXE strings — they live in external `Attributes/*.BIN` archives that ship separately.

**How to apply:**
- When you see a 32-bit constant compared against the result of `BChunkHash_JenkinsMix3`, run a Jenkins mix3 (seed `0xABCDEF00`, golden-ratio `a=b`, shifts 13/8/13/12/16/5/3/10/15) over candidate strings to crack it.
- For attribute lookups: extract `*.BIN`/`*.VLT` files from the game data first, then hash the contained names.
- The hash is case-sensitive and requires exact bytes (no null terminator).
