---
name: JDLZ decompression algorithm
description: NFSMW JDLZ v0x02 algorithm reverse-engineered from speed.exe @ 0x64db40; clean Python implementation in /home/cortix/tools/nfsmw_bun_reader/jdlz_nfsmw.py.
type: project
originSessionId: c4edf485-e85f-4e2f-ac31-e021ba66e8d6
---
NFSMW uses a JDLZ variant version 0x02 (different from Underground/Carbon and from public-internet "JDLZ" implementations). All the previous community decompressors I tried produced 0 bytes or garbage. Solved by directly disassembling speed.exe.

**Decompressor entry: 0x64db40** (also a magic-dispatcher at 0x650360 jumping to it).

## Format

16-byte header:
```
[0..3]   "JDLZ"
[4]      version (must == 0x02)
[5..7]   reserved
[8..11]  decompressed_size (u32 LE)
[12..15] compressed_size (u32 LE — total INCLUDING the 16-byte header)
```

Compressed stream starts at offset 0x10:
```
[0x10]   flag1 byte
[0x11]   flag2 byte
[0x12+]  payload
```

## Algorithm

```
flag1 = src[0x10] | 0x100   # sentinel at bit 8
flag2 = src[0x11] | 0x100
src_pos = 0x12
remaining = comp_size - 0x12

loop:
    if flag1 LSB == 0: literal
        out << src[src_pos++]
        remaining -= 1
    else: back-ref
        b0 = src[pos], b1 = src[pos+1]; pos += 2; remaining -= 2
        if flag2 LSB == 1:  # form A — small offset, very long length (RLE)
            length = (((b0 & 0xF0) << 4) | b1) + 3      # 12-bit, range 3..4098
            offset = (b0 & 0x0F) + 1                      # 4-bit, range 1..16
        else:               # form B — medium offset, short length
            length = (b0 & 0x1F) + 3                      # 5-bit, range 3..34
            offset = (((b0 & 0xE0) << 3) | b1) + 17       # 11-bit + 17, range 17..2064
        copy `length` bytes from out[len(out)-offset]   # self-overlapping is valid
        flag2 = SAR(flag2, 1)
    flag1 = SAR(flag1, 1)
    if flag1 == 1: flag1 = src[src_pos++] | 0x100; remaining -= 1
    if flag2 == 1: flag2 = src[src_pos++] | 0x100; remaining -= 1   # always checked
```

Key gotcha: **flag1 LSB 0 = literal, 1 = back-ref** (OPPOSITE of public Underground/Carbon JDLZ).

The two back-ref forms are also unusual — small-offset/long-length and medium-offset/short-length, *no* large-offset form. This means JDLZ is tuned for repeating patterns within a 2KB window, not generic dictionary compression.

## Verified results
- gameplay.lzc (779,956 bytes) → 2,105,216 bytes (matches expected)
- GlobalB.lzc (1,520,744 bytes) → 2,803,648 bytes ✓
- InGameB.lzc (522,637 bytes) → 946,264 bytes ✓
- FrontB.lzc (2,921,499 bytes) → 6,677,024 bytes ✓
- All four byte-for-byte match the corresponding *.BUN files where they exist.

**Why:** Without this, ~12 MB of NFSMW assets were unreachable. Now all bundle contents (gameplay attributes, FE strings, in-game scripts) are decodable.

**How to apply:** Use `jdlz_nfsmw.py decompress in.lzc out.bun` for any NFSMW LZC. Decompressed output goes to `extracted/app/GLOBAL/decompressed_lzc/*.bun`. For string extraction inside JDLZ, use `jdlz_nfsmw.py extract-strings`.
