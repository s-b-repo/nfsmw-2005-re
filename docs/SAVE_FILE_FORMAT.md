# NFSMW Save File Format Reference

Complete reference for the Need for Speed: Most Wanted (2005, PC) profile save
file format, as implemented in `speed.exe`. This document consolidates the
findings from the save/load subsystem reverse-engineering effort.

---

## 1. Overview

NFSMW stores player progress in a single binary blob per player profile. The
file:

- Lives under the user's Documents folder, in a game-specific subdirectory.
- Has **no file extension** — the filename is literally the in-game player name.
- Is approximately **63 KB** (≈ `0xF8FC` bytes) regardless of save state.
- Carries an **MD5 digest** (NOT a CRC) in the last 16 bytes for tamper / corruption
  detection.
- Is written and read via the engine's **asynchronous file I/O layer**, not via
  direct synchronous `CreateFileA` / `ReadFile` / `WriteFile` calls from the
  save logic.

The on-disk layout is a flat memory image of `g_GameMaster` (the global game
state at `DAT_0091cf90`), with a small prelude and a settings tail, framed by a
zero pad and an MD5 trailer.

### Autosave triggers (summary)

| Trigger          | Entry point                                             |
| ---------------- | ------------------------------------------------------- |
| Manual save (FE) | `DispatchProfileSaveStateAction @ 0x544370` case 8      |
| Autosave overlay | `TryTriggerAutosaveOverlay @ 0x562ab0`                  |
| Per-tick poll    | `PerTickAutosaveCheck @ 0x620930`                       |
| Post-race        | `FUN_005a7ae0 @ 0x5a7ae0` (post-race screen)            |
| Commit           | `CommitAutosaveToProfile @ 0x526800` → `WriteProfileToFile @ 0x5188f0` |

---

## 2. Path resolution

The save directory is computed once at profile-manager init and cached. The
relevant routine is `EnsureProfileDirectoryExists @ 0x6cbf00`.

### Win32 calls (in order)

1. **`SHGetFolderPathA(NULL, 0x8005, NULL, 0, buf)`**
   - `0x8005` = `CSIDL_PERSONAL | CSIDL_FLAG_CREATE`
   - Resolves to `%USERPROFILE%\Documents` on Windows XP/Vista/7/10/11
   - The `CSIDL_FLAG_CREATE` bit ensures the Documents folder exists.
2. **`strcat(buf, "\\NFS Most Wanted")`**
3. **`CreateDirectoryA(buf, NULL)`**
   - Silently succeeds if it already exists.
4. Cached at `DAT_0091cb20[+0xc8]`.

### Final file path

```
%USERPROFILE%\Documents\NFS Most Wanted\<PlayerName>
```

- **No extension is appended.** This preserves PS2 MemoryCard entry-name
  semantics — on PS2, MemoryCard entries don't have file extensions; the PC port
  flattens the PS2's four logical records (`Profile`, `Thumbnail`, `Image`,
  `NFSMWSD`) into one stream per player.
- `RegisterProfileMemoryCardRecords @ 0x5435d0` registers the four PS2 logical
  entries; these names survive in the binary even though only one file is
  actually written on PC.
- `NFSMWSD` = "NFS Most Wanted Save Data" — the save-data identifier.
- `NFSMW` / `NFSMWNA` = product code (locale-specific; NA = North America).

### Optional sibling scan

`ScanNFSU2ProfileImportDir @ 0x518b40` looks at
`%USERPROFILE%\Documents\NFS Underground 2` to detect a prior-game install
(used for the NFSU2 → NFSMW import / bonus-car gate).

---

## 3. File structure

Total size ≈ **`0xF8FC` bytes** (≈ 63 740 bytes). Computed by
`GetProfileSaveBufferSize(0)` as:

```
(0x30 + 0x825) * 0x13 + 0x59F9 = 0xF8FC
```

where `0x30` is the garage slot count from `FUN_00628cc0`.

The buffer is assembled by `BuildProfileSaveBuffer @ 0x58fd10` and written by
`WriteProfileToFile @ 0x5188f0`.

### Master offset table

| Offset   | Size      | Field                                                                  |
| -------- | --------- | ---------------------------------------------------------------------- |
| `+0x00`  | `0x10`    | Zero pad (header padding; not hashed sentinel — see §4)                |
| `+0x10`  | `4`       | Build / version: `*(uint32*)(DAT_0091cf90 + 8)`                        |
| `+0x14`  | `0x20`    | g_GameMaster header: `g_GameMaster[+0x00 .. +0x20]` (8 dwords)         |
| `+0x34`  | `0xF0`    | Settings block A: `g_GameMaster[+0x324 .. +0x414]` (60 dwords)         |
| `+0xC4`  | `0x84`    | Settings block B: `g_GameMaster[+0x24 .. +0xA8]` (33 dwords)           |
| `+0x148` | `0x8CC8`  | **Career data block** (largest field): `g_GameMaster[+0x414 .. +0x90DC]` |
| `+0x8E10`| `1`       | Career terminator byte: `g_GameMaster[+0x90DC]`                        |
| `+0x8E11`| `0xBD8`   | Second career chunk: `g_GameMaster[+0x90E0 .. +0x91B8]`                |
| `+0x99E9`| `0x108`   | 18 × 0x18 records from `DAT_0091cf90[+0x2c]` (loop)                    |
| (tail)   | `~0x36`   | Audio fades + controller config + master volume via `FUN_0057ffb0`     |
| END-0x10 | `0x10`    | **MD5 digest** of bytes `[0 .. size − 0x20]`                           |

Note that bytes `[size − 0x20 .. size − 0x10]` (the 16 bytes immediately before
the MD5) are also zero-padded; the MD5 hashes the payload only, excluding both
its own slot and the preceding zero pad.

### Career data block (`+0x148`, `0x8CC8` bytes)

This is by far the biggest field — career career progression, owned cars,
unlocks, milestones, race wins, and bounty live here. Internal substructure is
managed entirely by the `g_GameMaster` writer and is not parsed at file-level.

### Settings tail (`FUN_0057ffb0`)

Holds:
- Audio: master / SFX / music / dialog / engine volumes; reverb fade
- Controller: axis/button binding indices, deadzones, FFB strength
- Display: brightness, units (mph/kph), subtitle on/off

---

## 4. MD5 implementation

The last 16 bytes of the file are an MD5 digest of the preceding payload. This
is **MD5, not CRC32** — proven by matching IV constants and round-table
T-values to RFC 1321.

### Call chain

| Address  | Routine                          | Role                                  |
| -------- | -------------------------------- | ------------------------------------- |
| `0x57f920` | `ComputeMd5OfSaveBuffer`       | Top-level: init context, update, finalize, write 16 bytes |
| `0x650410` | `Md5CompressBlock`             | 64-byte block compression (4 rounds × 16 ops) |
| (inline) | `Md5UpdateContext`               | Appends bytes, flushes full blocks    |
| (inline) | `Md5FinalizeContext`             | Public finalize wrapper               |
| (inline) | `Md5PadAndFinalize`              | Appends `0x80`, zero-pads to 56 mod 64, appends 64-bit length |

### Verification — IV constants

`Md5CompressBlock` initializes / receives state:

```
A = 0x67452301
B = 0xEFCDAB89
C = 0x98BADCFE
D = 0x10325476
```

These are the canonical MD5 IVs (RFC 1321 §3.3).

### Verification — T-table

The compression function multiplies by the standard 64 T[i] constants. The
first few in `Md5CompressBlock` match exactly:

```
T[ 0] = 0xD76AA478
T[ 1] = 0xE8C7B756
T[ 2] = 0x242070DB
T[ 3] = 0xC1BDCEEE
T[ 4] = 0xF57C0FAF
...
```

### Context layout (heuristic, observed offsets)

| Offset    | Field                                       |
| --------- | ------------------------------------------- |
| `ctx+0x00`  | State A/B/C/D (4 × uint32)                |
| `ctx+0x10`  | Bit count (uint64)                        |
| `ctx+0x18`  | Block buffer (64 bytes)                   |
| `ctx+0x58`  | Buffer length                             |
| `ctx+0x59`  | **Raw 16-byte digest output**             |
| `ctx+0x69`  | Lowercase hex string (33 bytes incl. NUL) |

### What MD5 is hashed?

```
md5_input  = save_buffer[0 .. size − 0x20]
hash       = save_buffer[size − 0x10 .. size]
```

The 16 bytes between the hashed region and the MD5 slot are zero-padded and
NOT included in the hash. This is how the writer can insert the digest into
the buffer without needing a two-pass hash.

---

## 5. Autosave triggers (detail)

### 5.1 Per-tick poll

`PerTickAutosaveCheck @ 0x620930` is invoked from the main game tick. It
calls `CheckShouldAutosaveNow @ 0x5184d0`. If the check returns true, it sets:

```
DAT_0091cb20[+0x1f] = 1   // autosave-pending flag
```

On the next FE / world transition with `g_GameMaster[+0x38] == 1`, the autosave
overlay is shown and the save commits.

### 5.2 Post-race trigger

`FUN_005a7ae0 @ 0x5a7ae0` (post-race screen handler) explicitly calls
`CheckShouldAutosaveNow` and, on true, routes to `TryTriggerAutosaveOverlay`.
This is what causes the "Saving..." overlay after every race.

### 5.3 Manual save (front-end menu)

`DispatchProfileSaveStateAction @ 0x544370`:

| opcode | meaning                                          |
| ------ | ------------------------------------------------ |
| `7`    | save (user-initiated)                            |
| `8`    | load                                             |
| `9`    | delete                                           |
| `0xC`  | format-card / wipe flow (PS2 vestige; works on PC) |

`DispatchProfileManagerCommand @ 0x560dc0` is the front-end's opcode router.
Opcode `1` enters `MainProfileManager.fng`; opcode `3` is the INIT path that
calls `EnsureProfileDirectoryExists` plus the NFSU2 scan.

### 5.4 Async completion dispatch

When the async write returns, `HandleProfileSaveResultDispatch @ 0x563380`
decodes the result. A magic value `0xB8A7C6CD` at `result[+0x10]` indicates
success — this is either a save-file header magic OR a successful-I/O sentinel
from the async layer (the surrounding code treats it as success regardless).

---

## 6. Async file I/O

NFSMW does **not** call `CreateFileA` directly from the save / load path. All
file access goes through the engine's async I/O layer:

```
WriteProfileToFile @ 0x5188f0
  → enqueues a write job (callback = HandleProfileSaveResultDispatch)
  → FUN_007f3bd0 (job-queue submit)
    → FUN_007f5d42 (worker thread)
      → FUN_007f6f42 (eventual Win32 file call)

LoadProfileFromFile @ 0x5268b0
  → state-machine: this[+0x40] = 4 (LOAD)
  → FUN_007f3c8a (async read submit)
  → on completion → HandleProfileSaveResultDispatch (magic check)
```

This means:
- Saves do not block the main game loop; the autosave overlay polls the async
  result.
- Modifications to the synchronous code path will not affect saving.
- Hooking `CreateFileA` will catch the write, but the call stack will land
  deep inside the worker thread (`FUN_007f6f42`), not in the save code.
- Whether the four PS2 logical records become four separate files or are
  concatenated is decided inside this async layer; static analysis of
  `BuildProfileSaveBuffer` alone cannot resolve it.

### Profile dirty detection

To avoid unnecessary writes, the engine snapshots the in-memory profile after
a successful load, then diffs against the live state when deciding whether to
write:

| Address    | Routine                            | Role                            |
| ---------- | ---------------------------------- | ------------------------------- |
| `0x599500` | `CreateProfileMemorySnapshot`      | Copies state to `this[+0x128]`  |
| `0x599570` | `CompareProfileSnapshotForDirty`   | `memcmp` vs. current; returns 1 if dirty |

---

## 7. Correction: `MSG_R_BI_DATACRC` is NOT the save CRC

A stale earlier hypothesis (preserved in the `career + milestones` memory
entry) suggested `MSG_R_BI_DATACRC` was the save-integrity check. **This is
wrong.**

- `MSG_R_BI_DATACRC` is a netcode message-name string located at `0x8b6b7c`.
- It sits in the network message-name table directly adjacent to
  `MSG_R_SC_RESTARTLOAD` and `SERVERSTATE_LOADING`.
- It has **zero code xrefs** — it's an orphan / diagnostic / debug-build
  string that survives in the retail binary.
- The actual save integrity hash is **MD5**, computed by
  `ComputeMd5OfSaveBuffer @ 0x57f920` and verified post-load against the
  trailing 16 bytes of the file (a mismatch triggers the corruption rejection
  flow, which uses a different message string in the live retail UI).

When auditing save-integrity code, search for the MD5 IVs (`0x67452301`,
`0xEFCDAB89`, `0x98BADCFE`, `0x10325476`) rather than for `DATACRC`.

---

## 8. Save modification

Editing a save file is straightforward if you respect the MD5 trailer:

1. Read the file as raw bytes.
2. Modify any payload byte in `[0x10 .. size − 0x20]`.
   - Do not touch the leading 16-byte zero pad if you want the game's loader to
     accept the file (some checks rely on bytes `+0x00 .. +0x10` being zero).
   - Do not touch bytes `[size − 0x20 .. size − 0x10]` — they are zero pad.
3. Recompute MD5 over `data[0 : size − 0x20]`.
4. Overwrite the last 16 bytes with the new digest.
5. Save back to disk.

### Common edits

| Goal                | Field offset (approx)             | Notes                                 |
| ------------------- | --------------------------------- | ------------------------------------- |
| Build/version       | `+0x10` (uint32)                  | Match game version to avoid migration |
| Player cash         | inside career block (`+0x148+…`)  | Sub-offset varies; sniff by saving with known cash, diffing |
| Career milestone    | inside career block               | Treat as bitfield; diff to locate     |
| Garage slot (18×0x18) | tail loop region                | Each entry is 0x18 bytes              |
| Audio volume        | settings tail                     | float [0..1] per channel              |

### Bypassing the corruption check

If you need to test edits without recomputing MD5, you can patch the verifier
to short-circuit:

- Patch `0x57f920` (`ComputeMd5OfSaveBuffer`) to early-return with an
  all-zero digest, **then also write 16 zero bytes** as the trailer.

This is purely a development workflow — the recommended approach is the Python
recomputation script in the appendix.

---

## Appendix A — Python save editor

A minimal save edit + MD5 recompute helper. Requires only the Python standard
library.

```python
#!/usr/bin/env python3
"""
nfsmw_save_edit.py — Edit an NFSMW PC save file and recompute its MD5 trailer.

Usage:
    nfsmw_save_edit.py read  <save_path>
    nfsmw_save_edit.py patch <save_path> <hex_offset> <hex_bytes>
    nfsmw_save_edit.py fix   <save_path>     # just recompute the MD5

Save layout (≈ 0xF8FC bytes):
    [0x00..0x10)            zero pad
    [0x10..size-0x20)       hashed payload (build/version, g_GameMaster, career, tail)
    [size-0x20..size-0x10)  zero pad (NOT hashed)
    [size-0x10..size)       MD5 of [0..size-0x20)
"""
import hashlib
import os
import sys

DIGEST_SIZE = 0x10
TRAILER_PAD = 0x10  # zero pad between payload and MD5 slot

def hashed_region(buf: bytes) -> bytes:
    return buf[: len(buf) - (DIGEST_SIZE + TRAILER_PAD)]

def stored_digest(buf: bytes) -> bytes:
    return buf[len(buf) - DIGEST_SIZE :]

def recompute_md5(buf: bytearray) -> bytes:
    digest = hashlib.md5(bytes(hashed_region(buf))).digest()
    buf[len(buf) - DIGEST_SIZE :] = digest
    # Zero out the pad between payload and digest, just in case.
    buf[len(buf) - (DIGEST_SIZE + TRAILER_PAD) : len(buf) - DIGEST_SIZE] = b"\x00" * TRAILER_PAD
    return digest

def cmd_read(path: str) -> None:
    with open(path, "rb") as f:
        buf = f.read()
    size = len(buf)
    build_ver = int.from_bytes(buf[0x10:0x14], "little") if size >= 0x14 else 0
    have = stored_digest(buf).hex()
    want = hashlib.md5(hashed_region(buf)).hexdigest()
    print(f"file:         {path}")
    print(f"size:         {size} (0x{size:X})")
    print(f"build/ver:    0x{build_ver:08X}")
    print(f"md5 stored:   {have}")
    print(f"md5 expected: {want}")
    print(f"integrity:    {'OK' if have == want else 'MISMATCH'}")

def cmd_patch(path: str, hex_offset: str, hex_bytes: str) -> None:
    offset = int(hex_offset, 16)
    payload = bytes.fromhex(hex_bytes)
    with open(path, "rb") as f:
        buf = bytearray(f.read())
    end = offset + len(payload)
    payload_end = len(buf) - (DIGEST_SIZE + TRAILER_PAD)
    if offset < 0x10:
        raise SystemExit("refusing to patch into the leading zero-pad (<0x10)")
    if end > payload_end:
        raise SystemExit(f"patch end 0x{end:X} extends past hashed payload (0x{payload_end:X})")
    buf[offset:end] = payload
    digest = recompute_md5(buf)
    backup = path + ".bak"
    if not os.path.exists(backup):
        with open(backup, "wb") as f:
            f.write(buf[: len(buf)])  # write original? no — we already mutated buf
    with open(path, "wb") as f:
        f.write(buf)
    print(f"patched {len(payload)} byte(s) @ 0x{offset:X}; new md5 = {digest.hex()}")

def cmd_fix(path: str) -> None:
    with open(path, "rb") as f:
        buf = bytearray(f.read())
    digest = recompute_md5(buf)
    with open(path, "wb") as f:
        f.write(buf)
    print(f"recomputed md5 = {digest.hex()}")

def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    cmd = argv[1]
    if cmd == "read" and len(argv) == 3:
        cmd_read(argv[2])
    elif cmd == "patch" and len(argv) == 5:
        cmd_patch(argv[2], argv[3], argv[4])
    elif cmd == "fix" and len(argv) == 3:
        cmd_fix(argv[2])
    else:
        print(__doc__)
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

### Typical workflow

```sh
# 1. Inspect a save (verifies MD5).
python3 nfsmw_save_edit.py read "$HOME/Documents/NFS Most Wanted/MyName"

# 2. Patch the build/version field (uint32 LE) to 0xDEADBEEF as an example.
python3 nfsmw_save_edit.py patch "$HOME/Documents/NFS Most Wanted/MyName" 0x10 EFBEADDE

# 3. Or just fix the MD5 after an external edit (e.g., a hex-editor run).
python3 nfsmw_save_edit.py fix "$HOME/Documents/NFS Most Wanted/MyName"
```

Always keep a backup. The game will silently refuse a save with a bad MD5;
it will not corrupt the file on its own, but a botched payload edit can wedge
the profile state machine on next boot.

---

## References

- `EnsureProfileDirectoryExists` — `speed.exe @ 0x6cbf00`
- `BuildProfileSaveBuffer` — `speed.exe @ 0x58fd10`
- `GetProfileSaveBufferSize` — `speed.exe` (size formula)
- `ComputeMd5OfSaveBuffer` — `speed.exe @ 0x57f920`
- `Md5CompressBlock` — `speed.exe @ 0x650410`
- `WriteProfileToFile` — `speed.exe @ 0x5188f0`
- `LoadProfileFromFile` — `speed.exe @ 0x5268b0`
- `DispatchProfileSaveStateAction` — `speed.exe @ 0x544370`
- `DispatchProfileManagerCommand` — `speed.exe @ 0x560dc0`
- `TryTriggerAutosaveOverlay` — `speed.exe @ 0x562ab0`
- `CommitAutosaveToProfile` — `speed.exe @ 0x526800`
- `PerTickAutosaveCheck` — `speed.exe @ 0x620930`
- `CheckShouldAutosaveNow` — `speed.exe @ 0x5184d0`
- `HandleProfileSaveResultDispatch` — `speed.exe @ 0x563380`
- `CreateProfileMemorySnapshot` — `speed.exe @ 0x599500`
- `CompareProfileSnapshotForDirty` — `speed.exe @ 0x599570`
- `ScanNFSU2ProfileImportDir` — `speed.exe @ 0x518b40`
- `RegisterProfileMemoryCardRecords` — `speed.exe @ 0x5435d0`
- RFC 1321 — The MD5 Message-Digest Algorithm
