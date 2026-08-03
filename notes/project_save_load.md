---
name: profile save/load subsystem
description: NFSMW persists profiles to %USERPROFILE%\Documents\NFS Most Wanted\<PlayerName> (no extension). PS2 MemoryCard-style entry layout; MD5 (NOT CRC) integrity hash at file tail.
type: project
originSessionId: c4edf485-e85f-4e2f-ac31-e021ba66e8d6
---

## Save path resolution
- `EnsureProfileDirectoryExists @ 0x6cbf00` calls **SHGetFolderPathA(CSIDL=0x8005 = CSIDL_FLAG_CREATE|CSIDL_PERSONAL)** then **CreateDirectoryA(<Documents>\\NFS Most Wanted)**.
- Final dir cached at `DAT_0091cb20[+0xc8]`.
- File path = `<Documents>\NFS Most Wanted\<PlayerName>` literally — **NO `.bin`/`.pcf` extension** (PS2 MemoryCard entry-name semantics preserved on PC port; `RegisterProfileMemoryCardRecords @ 0x5435d0` registers logical entries Profile/Thumbnail/Image/NFSMWSD).
- NFSMWSD = save-data identifier; NFSMW/NFSMWNA = product code (locale).
- Optional NFSU2 import scan: `ScanNFSU2ProfileImportDir @ 0x518b40` looks at `<Documents>\NFS Underground 2` to flag prior-game presence.

## Save buffer layout (BuildProfileSaveBuffer @ 0x58fd10)
| offset | size | content |
|--------|------|---------|
| +0x00  | 0x10 | zero-padded header pad |
| +0x10  | 4    | DAT_0091cf90[+8] (build/version uint32) |
| +0x14  | 0x20 | g_GameMaster[+0..+0x20] (8 dwords) |
| +0x34  | 0xF0 | g_GameMaster[+0x324..+0x414] (60 dwords) |
| +0xC4  | 0x84 | g_GameMaster[+0x24..+0xA8] (33 dwords) |
| +0x148 | 0x8CC8 | career data block at g_GameMaster[+0x414..+0x90DC] |
| +0x8E10| 1    | g_GameMaster[+0x90DC] |
| +0x8E11| 0xBD8| g_GameMaster[+0x90E0..+0x91B8] |
| loop   | 0x108| 18 × 0x18 records from DAT_0091cf90[+0x2c] |
| tail   | ~0x36 | settings (audio fades, controller config, vol) via FUN_0057ffb0 |
| END-0x10 | 0x10 | **MD5(payload, len=size-0x20)** |

Total size = `GetProfileSaveBufferSize(0) = (0x30 + 0x825) * 0x13 + 0x59F9` ≈ 0xF8FC ≈ 63740 bytes. `0x30` from `FUN_00628cc0` (garage slot count).

## Integrity hash — MD5 not CRC
`ComputeMd5OfSaveBuffer @ 0x57f920` is the digest writer.
- **Proof:** IV constants `A=0x67452301, B=0xefcdab89, C=0x98badcfe, D=0x10325476` (MD5 init); T-table in `Md5CompressBlock @ 0x650410` matches RFC 1321 (`0xd76aa478, 0xe8c7b756, 0x242070db, 0xc1bdceee, 0xf57c0faf, …`). Padding: 0x80 + zeros to 56 mod 64 + 64-bit bit-count.
- 16 bytes raw digest at `ctx+0x59`; lowercase hex at `ctx+0x69`.
- MSG_R_BI_DATACRC @ 0x8b6b7c is **NOT this hash** — it sits in the netcode message-name table next to MSG_R_SC_RESTARTLOAD / SERVERSTATE_LOADING and has zero code xrefs (orphan/diagnostic).

## Save trigger paths
1. **Manual save** (FE save menu): `DispatchProfileSaveStateAction @ 0x544370` case 8 → `WriteProfileToFile @ 0x5188f0`.
2. **Autosave**: `TryTriggerAutosaveOverlay @ 0x562ab0` → `ShowAutosaveOverlayUi @ 0x518c50` → `CommitAutosaveToProfile @ 0x526800` → `WriteProfileToFile @ 0x5188f0`.
3. **Per-tick poll**: `PerTickAutosaveCheck @ 0x620930` runs `CheckShouldAutosaveNow @ 0x5184d0`; on true, sets `DAT_0091cb20[+0x1f]=1` (autosave-pending flag).
4. **Post-race trigger**: `FUN_005a7ae0 @ 0x5a7ae0` (post-race screen) calls `CheckShouldAutosaveNow` and dispatches if pending.
5. Async completion: `HandleProfileSaveResultDispatch @ 0x563380` decodes result codes (magic `0xB8A7C6CD` = success at result[+0x10]).

## Load path
`LoadProfileFromFile @ 0x5268b0` (was FUN_005268b0):
1. Copy player name (16 chars) into local + DAT_0091c2b8.
2. Build path = `<Documents>\NFS Most Wanted\<PlayerName>`.
3. State machine: this[+0x40] = 4 (LOAD).
4. `FUN_007f3c8a` queues async read; on completion, HandleProfileSaveResultDispatch receives result with magic check.
5. `CreateProfileMemorySnapshot @ 0x599500` rebuilds in-memory snapshot for dirty-comparison after load.

## Profile dirty detection
- `CreateProfileMemorySnapshot @ 0x599500` — snapshot at this[+0x128].
- `CompareProfileSnapshotForDirty @ 0x599570` — memcmp against current state; returns 1 if dirty.

## Profile manager command dispatcher
`DispatchProfileManagerCommand @ 0x560dc0` takes opcode 1..0x12:
- 1 = enter MainProfileManager.fng
- 3 = INIT (calls EnsureProfileDirectoryExists + scan)
- 7 = save, 8 = load, 9 = delete
- 0xC = format-card flow

## Why
The PC save-game format is a direct port of the PS2 MemoryCard layout: 4 named entries (Profile, Thumbnail, Image, NFSMWSD) become 4 files in `Documents\NFS Most Wanted\<PlayerName>\` — but on the PC, the implementation flattens them into a single binary stream per player. The MD5 trailer enables save-corruption detection without needing platform-provided checksumming.

## How to apply
- To modify save layout: edit `BuildProfileSaveBuffer @ 0x58fd10` — fields are copied via raw pointer arithmetic from g_GameMaster (DAT_0091cf90); offsets at +0x414/+0x90DC/+0x90E0 are the career/settings/options blocks.
- To bypass corruption check: patch `0x57f920` to early-return with all-zero digest (load verifier compares MD5; mismatch triggers MSG_R_BI_DATACRC-style rejection).
- To force autosave: write `*DAT_0091cb20[+0x1f] = 1` and `g_GameMaster[+0x38] = 1`; the per-tick check will fire on next frame.

## Open questions
- Exact filename: confirmed no extension is appended in this code path. Confirm by running the game and inspecting `Documents\NFS Most Wanted\` — there may be a wrapper layer (CFile open) that appends a suffix in the async-write thread (FUN_007f3bd0 → FUN_007f5d42 → FUN_007f6f42).
- Whether the 4 PS2-record names (Profile/Thumbnail/Image/NFSMWSD) become 4 separate files on PC or are concatenated into one.
- The `0xB8A7C6CD` magic at result[+0x10] — appears to be a save-file header magic OR a successful-I/O sentinel from the async layer.
- `0xff` byte at DAT_0091cae0[+0x14] — could be the save-slot index sentinel.
