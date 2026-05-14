#!/usr/bin/env python3
"""
nfsmw-tool — Linux-native CLI for Need For Speed Most Wanted (2005) reverse-engineering.

Exercises every layer of the RE work in this project:
  * bChunk (Bob Jenkins mix3, seed 0xABCDEF00) hash compute + reverse-lookup
  * JDLZ v0x02 decompression (proprietary EA codec)
  * attributes.bin schema dump
  * Save-file MD5 integrity verify
  * NFSPluginSDK address lookup

Usage:
    nfsmw-tool hash <NAME>              Compute bChunk hash of a string
    nfsmw-tool lookup <HASH>            Reverse-lookup a hash to its name (if cracked)
    nfsmw-tool jdlz <FILE>              Decompress a JDLZ-compressed file (writes .bin)
    nfsmw-tool attrs <attributes.bin>   Dump attributes.bin schema with cracked names
    nfsmw-tool verify-save <FILE>       Verify the MD5 trailer of an NFSMW save
    nfsmw-tool sdk <ADDRESS|NAME>       Look up an address or name in the SDK address index
    nfsmw-tool stats                    Show project stats (crack %, coverage, etc.)

Example:
    $ nfsmw-tool hash MASS
    bChunk("MASS") = 0x4A56503D

    $ nfsmw-tool lookup 0x4A56503D
    0x4A56503D = MASS  (Float-typed attribute)

    $ nfsmw-tool jdlz GLOBAL/GLOBALB.LZC
    Decompressed 2803648 bytes → GLOBAL/GLOBALB.LZC.bin

License: BSD-3 (project), Apache-2.0 (this file is original)
"""

from __future__ import annotations
import argparse
import hashlib
import json
import os
import struct
import sys
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# Paths (relative to this script — repo layout assumed)
# ─────────────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent  # tools/nfsmw-tool/ → repo/
DOCS = REPO_ROOT / "docs"


# ─────────────────────────────────────────────────────────────────────────────
# bChunk = Bob Jenkins 1996 "mix3" hash, seed 0xABCDEF00
# ─────────────────────────────────────────────────────────────────────────────
MASK = 0xFFFFFFFF
GOLDEN = 0x9E3779B9
SEED = 0xABCDEF00


def _mix(a, b, c):
    a = (a - b) & MASK; a = (a - c) & MASK; a ^= (c >> 13); a &= MASK
    b = (b - c) & MASK; b = (b - a) & MASK; b ^= ((a << 8) & MASK)
    c = (c - a) & MASK; c = (c - b) & MASK; c ^= (b >> 13); c &= MASK
    a = (a - b) & MASK; a = (a - c) & MASK; a ^= (c >> 12); a &= MASK
    b = (b - c) & MASK; b = (b - a) & MASK; b ^= ((a << 16) & MASK)
    c = (c - a) & MASK; c = (c - b) & MASK; c ^= (b >> 5); c &= MASK
    a = (a - b) & MASK; a = (a - c) & MASK; a ^= (c >> 3); a &= MASK
    b = (b - c) & MASK; b = (b - a) & MASK; b ^= ((a << 10) & MASK)
    c = (c - a) & MASK; c = (c - b) & MASK; c ^= (b >> 15); c &= MASK
    return a & MASK, b & MASK, c & MASK


def bchunk(s: str | bytes, seed: int = SEED) -> int:
    if isinstance(s, str):
        s = s.encode('latin-1')
    length = len(s)
    a = GOLDEN
    b = GOLDEN
    c = seed
    p = 0
    rem = length
    while rem >= 12:
        a = (a + struct.unpack_from('<I', s, p)[0]) & MASK
        b = (b + struct.unpack_from('<I', s, p + 4)[0]) & MASK
        c = (c + struct.unpack_from('<I', s, p + 8)[0]) & MASK
        a, b, c = _mix(a, b, c)
        p += 12
        rem -= 12
    c = (c + length) & MASK
    if rem >= 11: c = (c + (s[p + 10] << 24)) & MASK
    if rem >= 10: c = (c + (s[p + 9] << 16)) & MASK
    if rem >= 9:  c = (c + (s[p + 8] << 8)) & MASK
    if rem >= 8:  b = (b + (s[p + 7] << 24)) & MASK
    if rem >= 7:  b = (b + (s[p + 6] << 16)) & MASK
    if rem >= 6:  b = (b + (s[p + 5] << 8)) & MASK
    if rem >= 5:  b = (b + s[p + 4]) & MASK
    if rem >= 4:  a = (a + (s[p + 3] << 24)) & MASK
    if rem >= 3:  a = (a + (s[p + 2] << 16)) & MASK
    if rem >= 2:  a = (a + (s[p + 1] << 8)) & MASK
    if rem >= 1:  a = (a + s[p]) & MASK
    a, b, c = _mix(a, b, c)
    return c


# ─────────────────────────────────────────────────────────────────────────────
# JDLZ v0x02 decompressor (NFSMW variant)
# Algorithm reverse-engineered from speed.exe @ 0x64db40
# ─────────────────────────────────────────────────────────────────────────────
def jdlz_decompress(buf: bytes) -> bytes:
    if len(buf) < 0x12:
        raise ValueError("buffer too small for JDLZ header")
    if buf[:4] != b'JDLZ':
        raise ValueError(f"not a JDLZ file (magic was {buf[:4]!r})")
    if buf[4] != 0x02:
        raise ValueError(f"unsupported JDLZ version 0x{buf[4]:02x} (only v0x02 supported)")
    decomp_size = struct.unpack_from('<I', buf, 8)[0]
    comp_size = struct.unpack_from('<I', buf, 12)[0]
    out = bytearray()
    src_pos = 0x12
    flag1 = buf[0x10] | 0x100
    flag2 = buf[0x11] | 0x100
    remaining = comp_size - 0x12
    while remaining > 0 and len(out) < decomp_size:
        if (flag1 & 1) == 0:
            # Literal byte
            out.append(buf[src_pos])
            src_pos += 1
            remaining -= 1
        else:
            # Back-reference (2 bytes)
            if remaining < 2:
                break
            b0, b1 = buf[src_pos], buf[src_pos + 1]
            if (flag2 & 1) == 1:
                # Form A: small offset (1..16), long length (3..4098)
                length = (((b0 & 0xF0) << 4) | b1) + 3
                offset = (b0 & 0x0F) + 1
            else:
                # Form B: bigger offset (17..2064), short length (3..34)
                length = (b0 & 0x1F) + 3
                offset = (((b0 & 0xE0) << 3) | b1) + 17
            src_pos += 2
            remaining -= 2
            start = len(out) - offset
            if start < 0:
                raise ValueError(f"back-reference out of bounds at out-offset {len(out)}, ref-back {offset}")
            for j in range(length):
                if len(out) >= decomp_size:
                    break
                out.append(out[start + j])
            flag2 >>= 1
        flag1 >>= 1
        # Refill flag bytes when sentinel bit reaches the bottom
        if flag1 == 1:
            if remaining < 1:
                break
            flag1 = buf[src_pos] | 0x100
            src_pos += 1
            remaining -= 1
        if flag2 == 1:
            if remaining < 1:
                break
            flag2 = buf[src_pos] | 0x100
            src_pos += 1
            remaining -= 1
    return bytes(out)


# ─────────────────────────────────────────────────────────────────────────────
# Hash database
# ─────────────────────────────────────────────────────────────────────────────
def load_hash_db() -> dict[int, str]:
    """Load the verified-cracks JSON into {hash_int: name}."""
    path = DOCS / "attribute_cracks_verified.json"
    if not path.exists():
        return {}
    with open(path) as f:
        raw = json.load(f)
    return {int(k, 16): name for k, name in raw.items()}


def load_attr_table() -> dict:
    """Load the attribute type-table (hash → type-name lookup)."""
    # Try in-package, then docs
    for candidate in [DOCS / "attrib_table.json", SCRIPT_DIR / "attrib_table.json"]:
        if candidate.exists():
            with open(candidate) as f:
                return json.load(f)
    return {}


def load_sdk_addrs() -> list:
    path = DOCS / "sdk_addrs.json"
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)


# ─────────────────────────────────────────────────────────────────────────────
# Save file format
# ─────────────────────────────────────────────────────────────────────────────
def verify_save(path: Path) -> tuple[bool, str]:
    """Verify the MD5 trailer of an NFSMW save file.
    Save format (from project_save_load.md):
      [payload ... ][0x00 × 0x10][16-byte MD5 of payload]
    The MD5 is computed over (size − 0x20) bytes (i.e. everything before the
    trailing zero-padding + digest).
    """
    data = path.read_bytes()
    if len(data) < 0x30:
        return False, f"file too small ({len(data)} bytes)"
    payload_len = len(data) - 0x20
    expected = data[-0x10:]
    actual = hashlib.md5(data[:payload_len]).digest()
    if actual == expected:
        return True, f"OK  payload {payload_len} bytes  MD5 {actual.hex()}"
    return False, f"BAD MD5\n  expected (from file): {expected.hex()}\n  computed:             {actual.hex()}"


# ─────────────────────────────────────────────────────────────────────────────
# attributes.bin schema dump
# ─────────────────────────────────────────────────────────────────────────────
TYPE_HASHES = {
    0x3C16EC5E: "Float",
    0xA3F0C234: "Text",
    0x939992BB: "UInt32",
    0x064BEC37: "Bool",
    0x2B936EB7: "RefSpec",
    0xA502A824: "StringKey",
    0xDB9D3A16: "eDRIVE_BY_TYPE",
}


def dump_attributes_bin(path: Path, names: dict[int, str]) -> None:
    data = path.read_bytes()
    if len(data) < 0x18000:
        print(f"{path}: too small ({len(data)} bytes) — needs at least 0x18000", file=sys.stderr)
        sys.exit(1)
    print(f"# attributes.bin schema dump from {path}")
    print(f"# rows starting at offset 0x18000 (16 bytes each)")
    print(f"# format: HASH  TYPE                 NAME (if cracked)")
    counts = {}
    pos = 0x18000
    rows = 0
    while pos + 16 <= len(data):
        name_hash, type_hash = struct.unpack_from('<II', data, pos)
        if name_hash == 0 and type_hash == 0:
            break  # end of table sentinel
        type_name = TYPE_HASHES.get(type_hash, f"unknown({type_hash:08X})")
        crack = names.get(name_hash, '?')
        print(f"  0x{name_hash:08X}  {type_name:<20s} {crack}")
        counts[type_name] = counts.get(type_name, 0) + 1
        pos += 16
        rows += 1
    print(f"\n# Total: {rows} rows")
    for tp, c in sorted(counts.items()):
        print(f"#   {tp:<20s} {c}")


# ─────────────────────────────────────────────────────────────────────────────
# Stats
# ─────────────────────────────────────────────────────────────────────────────
def show_stats() -> None:
    names = load_hash_db()
    sdk = load_sdk_addrs()
    print(f"NFSMW Reverse-Engineering Project — Stats")
    print(f"=" * 50)
    print(f"Attribute names cracked:        {len(names)} / 345 = {len(names)*100/345:.1f}%")
    print(f"NFSPluginSDK addresses:         {len(sdk)}")
    print(f"  Functions:                    {sum(1 for e in sdk if e.get('kind')=='function')}")
    print(f"  Globals:                      {sum(1 for e in sdk if e.get('kind')=='global')}")
    # Sample of cracked names
    print(f"\nSample cracked attribute names:")
    for i, (h, n) in enumerate(sorted(names.items())[:10]):
        print(f"  0x{h:08X}  {n}")
    if len(names) > 10:
        print(f"  ... and {len(names)-10} more")


# ─────────────────────────────────────────────────────────────────────────────
# SDK address lookup
# ─────────────────────────────────────────────────────────────────────────────
def sdk_lookup(query: str) -> None:
    sdk = load_sdk_addrs()
    if not sdk:
        print("docs/sdk_addrs.json not found", file=sys.stderr); sys.exit(1)
    query_lower = query.lower()
    matches = []
    if query.startswith("0x"):
        target_addr = query.lower()
        for e in sdk:
            if e['addr'].lower() == target_addr:
                matches.append(e)
    else:
        for e in sdk:
            name = (e.get('fullname') or e.get('name') or e.get('method') or '').lower()
            if query_lower in name:
                matches.append(e)
    if not matches:
        print(f"No matches for {query!r}", file=sys.stderr)
        sys.exit(1)
    for e in matches[:50]:
        kind = e.get('kind', '?')
        name = e.get('fullname') or e.get('name') or e.get('method') or '?'
        if kind == 'function':
            sig = f"{e.get('ret','?')} ({e.get('cc','?')} *)({e.get('args','?')})"
            print(f"  {e['addr']}  {kind:<8s} {name}  ::  {sig}")
        else:
            print(f"  {e['addr']}  {kind:<8s} {name}  ::  {e.get('type','?')}")
    if len(matches) > 50:
        print(f"  ... +{len(matches)-50} more")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────
def cmd_hash(args):
    h = bchunk(args.name)
    print(f'bChunk("{args.name}") = 0x{h:08X}')


def cmd_lookup(args):
    db = load_hash_db()
    table = load_attr_table()
    hash_val = int(args.hash, 16) if args.hash.startswith("0x") else int(args.hash, 16)
    name = db.get(hash_val)
    if not name:
        print(f"0x{hash_val:08X} : NOT CRACKED")
        # Type info?
        for tp, items in (dict(table).get('uncracked', {}) or {}).items():
            for hx in items:
                if int(hx, 16) == hash_val:
                    print(f"  Type: {tp}")
                    return
        sys.exit(1)
    # Find type
    type_name = "?"
    for tp, items in (dict(table).get('cracked', {}) or {}).items():
        for hx, n in items:
            if int(hx, 16) == hash_val:
                type_name = tp
                break
    print(f"0x{hash_val:08X} = {name}  ({type_name}-typed attribute)")


def cmd_jdlz(args):
    src = Path(args.file)
    data = src.read_bytes()
    out = jdlz_decompress(data)
    dst = src.with_suffix(src.suffix + ".bin") if not args.output else Path(args.output)
    dst.write_bytes(out)
    print(f"Decompressed {len(out)} bytes → {dst}")


def cmd_attrs(args):
    db = load_hash_db()
    dump_attributes_bin(Path(args.file), db)


def cmd_verify_save(args):
    ok, msg = verify_save(Path(args.file))
    print(msg)
    sys.exit(0 if ok else 1)


def cmd_sdk(args):
    sdk_lookup(args.query)


def cmd_stats(args):
    show_stats()


def main():
    ap = argparse.ArgumentParser(
        prog='nfsmw-tool',
        description='Linux CLI for NFSMW (2005) reverse engineering — exercises every layer of the repo docs.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split('Example:')[1] if 'Example:' in (__doc__ or '') else None
    )
    sub = ap.add_subparsers(dest='cmd', required=True)

    p = sub.add_parser('hash', help='compute bChunk hash of a name')
    p.add_argument('name')
    p.set_defaults(func=cmd_hash)

    p = sub.add_parser('lookup', help='reverse-lookup a hash to its cracked name')
    p.add_argument('hash')
    p.set_defaults(func=cmd_lookup)

    p = sub.add_parser('jdlz', help='decompress a JDLZ-compressed file')
    p.add_argument('file')
    p.add_argument('-o', '--output', help='output path (default: <file>.bin)')
    p.set_defaults(func=cmd_jdlz)

    p = sub.add_parser('attrs', help='dump attributes.bin schema')
    p.add_argument('file', help='path to attributes.bin')
    p.set_defaults(func=cmd_attrs)

    p = sub.add_parser('verify-save', help='verify the MD5 trailer of an NFSMW save')
    p.add_argument('file')
    p.set_defaults(func=cmd_verify_save)

    p = sub.add_parser('sdk', help='look up an address or name in the SDK address index')
    p.add_argument('query', help='0x-prefixed address OR substring of function/global name')
    p.set_defaults(func=cmd_sdk)

    p = sub.add_parser('stats', help='show project stats (crack percentage, coverage)')
    p.set_defaults(func=cmd_stats)

    args = ap.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
