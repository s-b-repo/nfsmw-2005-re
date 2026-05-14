#!/usr/bin/env python3
"""
lua-disasm — NFSMW (Lua 5.0.2, flipped-A encoding, JDLZ-wrapped) bytecode tool.

NFSMW's gameplay scripting is vanilla Lua 5.0.2 with **two local quirks**:

  1. The iABC field layout is reversed vs stock Lua 5.0:
     stock:  B[23:32] | C[14:23] | A[6:14] | OP[0:6]   (POS_A=6)
     NFSMW:  A[24:32] | B[15:24] | C[6:15] | OP[0:6]   (POS_A=24)
     Bx/sBx are the same 18-bit field at bits [6:24].
     MAXSTACK (RK threshold) = 250, unchanged.

  2. Compiled .luac chunks are wrapped in JDLZ v0x02 blocks before being
     packed into the asset bundles. Scanning a decompressed_lzc/*.bun file
     for `\x1bLua\x50` literally only finds chunks whose first 16 bytes
     happen to be JDLZ-literal (no back-refs in the first byte). The
     reliable approach is to scan for JDLZ magic, decompress, then check
     for `\x1bLua\x50` at offset 0 of the decompressed buffer.

Subcommands
-----------
  lua-disasm find <bundle>            Scan a file for JDLZ-wrapped Lua chunks,
                                      print (jdlz-offset, decomp-size, source-name).
  lua-disasm dump <bundle> <offset>   Decompress one JDLZ block at <offset>
                                      and write the .luac to disk.
  lua-disasm decode <luac>            Disassemble a Lua 5.0 chunk file.

The decode output mimics `luac -l`:

    function <source:line,line> (N instructions, N upvalues, N locals, ...)
      1   [line]  OPNAME           A B C   ; comment
      ...
"""

from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path
from typing import Any, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Opcode table (35 entries, 0x00..0x22). Mode lets us pretty-print operands.
# ---------------------------------------------------------------------------
# Mode legend:
#   ABC   — three operands, B/C may be RK (>=250 -> constant)
#   ABx   — A + 18-bit unsigned Bx
#   AsBx  — A + 18-bit signed Bx (sBx = Bx - 131071)

ABC, ABx, AsBx = "ABC", "ABx", "AsBx"

# Per-opcode B/C "is RK candidate" flags. Mirrors lopcodes.c in Lua 5.0.
OPCODES: List[Tuple[str, str, bool, bool]] = [
    # name,        mode,  B_is_RK, C_is_RK
    ("MOVE",       ABC,   False, False),  # 0x00
    ("LOADK",      ABx,   False, False),  # 0x01
    ("LOADBOOL",   ABC,   False, False),  # 0x02
    ("LOADNIL",    ABC,   False, False),  # 0x03
    ("GETUPVAL",   ABC,   False, False),  # 0x04
    ("GETGLOBAL",  ABx,   False, False),  # 0x05
    ("GETTABLE",   ABC,   False, True ),  # 0x06
    ("SETGLOBAL",  ABx,   False, False),  # 0x07
    ("SETUPVAL",   ABC,   False, False),  # 0x08
    ("SETTABLE",   ABC,   True,  True ),  # 0x09
    ("NEWTABLE",   ABC,   False, False),  # 0x0a
    ("SELF",       ABC,   False, True ),  # 0x0b
    ("ADD",        ABC,   True,  True ),  # 0x0c
    ("SUB",        ABC,   True,  True ),  # 0x0d
    ("MUL",        ABC,   True,  True ),  # 0x0e
    ("DIV",        ABC,   True,  True ),  # 0x0f
    ("POW",        ABC,   True,  True ),  # 0x10
    ("UNM",        ABC,   False, False),  # 0x11
    ("NOT",        ABC,   False, False),  # 0x12
    ("CONCAT",     ABC,   False, False),  # 0x13
    ("JMP",        AsBx,  False, False),  # 0x14
    ("EQ",         ABC,   True,  True ),  # 0x15
    ("LT",         ABC,   True,  True ),  # 0x16
    ("LE",         ABC,   True,  True ),  # 0x17
    ("TEST",       ABC,   False, False),  # 0x18
    ("CALL",       ABC,   False, False),  # 0x19
    ("TAILCALL",   ABC,   False, False),  # 0x1a
    ("RETURN",     ABC,   False, False),  # 0x1b
    ("FORLOOP",    AsBx,  False, False),  # 0x1c
    ("TFORLOOP",   ABC,   False, False),  # 0x1d
    ("TFORPREP",   AsBx,  False, False),  # 0x1e
    ("SETLIST",    ABx,   False, False),  # 0x1f
    ("SETLISTO",   ABx,   False, False),  # 0x20
    ("CLOSE",      ABC,   False, False),  # 0x21
    ("CLOSURE",    ABx,   False, False),  # 0x22
]

MAXSTACK = 250          # B/C threshold for "is constant K" in this build.
SBX_BIAS = 131071       # (1<<17) - 1, canonical Lua 5.0 sBx bias.

LUA_SIG = b"\x1bLua\x50"   # Lua 5.0 chunk magic (sig+version).
JDLZ_MAGIC = b"JDLZ"


# ---------------------------------------------------------------------------
# JDLZ v0x02 decompressor (NFSMW variant).
# Ported verbatim from tools/nfsmw-tool/nfsmw_tool.py — algorithm RE'd from
# speed.exe @ 0x64db40. Kept as a local copy so this tool has zero deps on
# the rest of the repo's tools/.
# ---------------------------------------------------------------------------
def jdlz_decompress(buf: bytes) -> bytes:
    if len(buf) < 0x12:
        raise ValueError("buffer too small for JDLZ header")
    if buf[:4] != JDLZ_MAGIC:
        raise ValueError(f"not a JDLZ block (magic={buf[:4]!r})")
    if buf[4] != 0x02:
        raise ValueError(f"unsupported JDLZ version 0x{buf[4]:02x}")
    decomp_size = struct.unpack_from("<I", buf, 8)[0]
    comp_size = struct.unpack_from("<I", buf, 12)[0]
    out = bytearray()
    src_pos = 0x12
    flag1 = buf[0x10] | 0x100
    flag2 = buf[0x11] | 0x100
    remaining = comp_size - 0x12
    while remaining > 0 and len(out) < decomp_size:
        if (flag1 & 1) == 0:
            out.append(buf[src_pos]); src_pos += 1; remaining -= 1
        else:
            if remaining < 2:
                break
            b0, b1 = buf[src_pos], buf[src_pos + 1]
            if (flag2 & 1) == 1:
                length = (((b0 & 0xF0) << 4) | b1) + 3
                offset = (b0 & 0x0F) + 1
            else:
                length = (b0 & 0x1F) + 3
                offset = (((b0 & 0xE0) << 3) | b1) + 17
            src_pos += 2; remaining -= 2
            start = len(out) - offset
            if start < 0:
                raise ValueError(
                    f"back-ref OOB at out-offset {len(out)}, back {offset}"
                )
            for j in range(length):
                if len(out) >= decomp_size:
                    break
                out.append(out[start + j])
            flag2 >>= 1
        flag1 >>= 1
        if flag1 == 1:
            if remaining < 1:
                break
            flag1 = buf[src_pos] | 0x100; src_pos += 1; remaining -= 1
        if flag2 == 1:
            if remaining < 1:
                break
            flag2 = buf[src_pos] | 0x100; src_pos += 1; remaining -= 1
    return bytes(out)


def jdlz_block_size(buf: bytes, off: int) -> int:
    """Total on-disk length of the JDLZ block starting at `off` (comp_size)."""
    return struct.unpack_from("<I", buf, off + 12)[0]


# ---------------------------------------------------------------------------
# Instruction decoder — NFSMW shifts (A in the *high* bits).
# ---------------------------------------------------------------------------
def decode_insn(word: int) -> Tuple[int, int, int, int, int, int]:
    op  =  word        & 0x3F
    c   = (word >> 6)  & 0x1FF
    b   = (word >> 15) & 0x1FF
    a   = (word >> 24) & 0xFF
    bx  = (word >> 6)  & 0x3FFFF
    sbx = bx - SBX_BIAS
    return op, a, b, c, bx, sbx


def rk_str(val: int, is_rk: bool) -> str:
    if is_rk and val >= MAXSTACK:
        return f"K[{val - MAXSTACK}]"
    return f"R[{val}]"


# ---------------------------------------------------------------------------
# Chunk parser.
#
# The NFSMW chunk header has a 10-byte detail block (no canonical Lua 5.0.2
# "test number" — that's been removed). Layout (post sig + version):
#
#   +0  endian          (1 = LE)
#   +1  sizeof(int)
#   +2  sizeof(size_t)
#   +3  format          (always 0 in observed chunks)
#   +4  sizeof(Instr)   (= 4)
#   +5  SIZE_OP         (= 6)
#   +6  SIZE_A          (= 8)
#   +7  SIZE_B          (= 9)
#   +8  SIZE_C          (= 9)
#   +9  sizeof(Number)  (= 4, single-precision float)
#
# Everything that follows (the function tree) uses the canonical Lua 5.0.2
# lundump.c order; only the *instruction word* layout differs (see
# decode_insn above).
# ---------------------------------------------------------------------------
class LuaReader:
    def __init__(self, data: bytes, offset: int = 0) -> None:
        self.data = data
        self.pos = offset
        self.endian = "<"
        self.size_int = 4
        self.size_size_t = 4
        self.size_insn = 4
        self.size_number = 4         # NFSMW uses single-precision float.
        self.size_op = 6
        self.size_a = 8
        self.size_b = 9
        self.size_c = 9

    # --- low-level ---------------------------------------------------------
    def _take(self, n: int) -> bytes:
        if self.pos + n > len(self.data):
            raise ValueError(
                f"truncated chunk: need {n} at {self.pos:#x}, "
                f"have {len(self.data) - self.pos}"
            )
        out = self.data[self.pos:self.pos + n]
        self.pos += n
        return out

    def byte(self) -> int:
        return self._take(1)[0]

    def u32(self) -> int:
        return struct.unpack(self.endian + "I", self._take(4))[0]

    def integer(self) -> int:
        return struct.unpack(
            self.endian + ("i" if self.size_int == 4 else "q"),
            self._take(self.size_int),
        )[0]

    def size_t(self) -> int:
        return struct.unpack(
            self.endian + ("I" if self.size_size_t == 4 else "Q"),
            self._take(self.size_size_t),
        )[0]

    def number(self) -> float:
        raw = self._take(self.size_number)
        if self.size_number == 4:
            return struct.unpack(self.endian + "f", raw)[0]
        if self.size_number == 8:
            return struct.unpack(self.endian + "d", raw)[0]
        return int.from_bytes(raw, "little" if self.endian == "<" else "big")

    def string(self) -> bytes:
        n = self.size_t()
        if n == 0:
            return b""
        raw = self._take(n)
        # Strip Lua's trailing '\0' for display.
        return raw[:-1] if raw.endswith(b"\x00") else raw

    # --- chunk header (NFSMW layout) --------------------------------------
    def read_header(self) -> None:
        sig = self._take(4)
        if sig != b"\x1bLua":
            raise ValueError(f"bad signature {sig!r} at {self.pos - 4:#x}")
        version = self.byte()
        if version != 0x50:
            raise ValueError(f"not Lua 5.0 (version={version:#x})")
        endian = self.byte()
        self.endian = "<" if endian else ">"
        self.size_int    = self.byte()
        self.size_size_t = self.byte()
        _fmt             = self.byte()   # "format" byte, always 0 in observed
        self.size_insn   = self.byte()
        self.size_op     = self.byte()
        self.size_a      = self.byte()
        self.size_b      = self.byte()
        self.size_c      = self.byte()
        self.size_number = self.byte()
        # No canonical "test number" follows in this build.

    # --- function prototype ------------------------------------------------
    def read_function(self) -> "Proto":
        p = Proto()
        p.source = self.string().decode("latin-1", errors="replace")
        p.line_defined = self.integer()
        p.num_upvals = self.byte()
        p.num_params = self.byte()
        p.is_vararg = self.byte()
        p.max_stack = self.byte()
        # locals
        n = self.integer()
        for _ in range(n):
            name = self.string().decode("latin-1", errors="replace")
            startpc = self.integer()
            endpc = self.integer()
            p.locals.append((name, startpc, endpc))
        # line info
        n = self.integer()
        p.lineinfo = [self.integer() for _ in range(n)]
        # constants
        n = self.integer()
        for _ in range(n):
            t = self.byte()
            if t == 0:                       # LUA_TNIL
                p.constants.append(None)
            elif t == 1:                     # LUA_TBOOLEAN (defensive — stock 5.0
                p.constants.append(bool(self.byte()))   # writes only nil/number/string)
            elif t == 3:                     # LUA_TNUMBER
                p.constants.append(self.number())
            elif t == 4:                     # LUA_TSTRING
                p.constants.append(self.string())
            else:
                raise ValueError(f"unknown constant type {t} at {self.pos:#x}")
        # nested protos
        n = self.integer()
        for _ in range(n):
            p.protos.append(self.read_function())
        # code (read LAST in Lua 5.0)
        n = self.integer()
        for _ in range(n):
            p.code.append(self.u32())
        return p


class Proto:
    def __init__(self) -> None:
        self.source: str = ""
        self.line_defined: int = 0
        self.num_upvals: int = 0
        self.num_params: int = 0
        self.is_vararg: int = 0
        self.max_stack: int = 0
        self.locals: List[Tuple[str, int, int]] = []
        self.lineinfo: List[int] = []
        self.constants: List[Any] = []
        self.protos: List["Proto"] = []
        self.code: List[int] = []


# ---------------------------------------------------------------------------
# Disassembly formatter.
# ---------------------------------------------------------------------------
def format_const(k: Any) -> str:
    if k is None:
        return "nil"
    if isinstance(k, bool):
        return "true" if k else "false"
    if isinstance(k, (int, float)):
        return repr(k)
    try:
        s = k.decode("utf-8")
    except (UnicodeDecodeError, AttributeError):
        s = k.decode("latin-1", errors="replace") if isinstance(k, bytes) else str(k)
    if len(s) > 60:
        s = s[:57] + "..."
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def fmt_insn(pc: int, word: int, proto: Proto) -> str:
    op, a, b, c, bx, sbx = decode_insn(word)
    if op >= len(OPCODES):
        return f"  {pc + 1:>4d}  ?op={op:#04x}  raw={word:#010x}"
    name, mode, b_rk, c_rk = OPCODES[op]
    line = proto.lineinfo[pc] if pc < len(proto.lineinfo) else 0
    line_str = f"[{line}]" if line else "[?]"

    comment = ""
    if mode == ABC:
        operands = f"{a} {b} {c}"
        if name in ("GETTABLE", "SELF") and c_rk and c >= MAXSTACK:
            ki = c - MAXSTACK
            if 0 <= ki < len(proto.constants):
                comment = f"; {format_const(proto.constants[ki])}"
        elif name == "SETTABLE" and b_rk and b >= MAXSTACK:
            ki = b - MAXSTACK
            if 0 <= ki < len(proto.constants):
                comment = f"; key={format_const(proto.constants[ki])}"
    elif mode == ABx:
        operands = f"{a} {bx}"
        if name in ("LOADK", "GETGLOBAL", "SETGLOBAL"):
            if 0 <= bx < len(proto.constants):
                comment = f"; {format_const(proto.constants[bx])}"
        elif name == "CLOSURE":
            comment = f"; proto #{bx}"
    else:  # AsBx
        operands = f"{a} {sbx}"
        if name in ("JMP", "FORLOOP", "TFORPREP"):
            comment = f"; to {pc + 1 + sbx + 1}"

    return f"  {pc + 1:>4d}  {line_str:>6s}  {name:<10s} {operands:<12s} {comment}"


def disasm_proto(proto: Proto, depth: int = 0, idx_path: str = "main") -> List[str]:
    out: List[str] = []
    src = proto.source or "<?>"
    last_line = max(proto.lineinfo) if proto.lineinfo else proto.line_defined
    out.append(
        f"function {idx_path} <{src}:{proto.line_defined},{last_line}> "
        f"({len(proto.code)} insns, {proto.num_upvals} upvals, "
        f"{proto.num_params} params, {proto.max_stack} stack, "
        f"{len(proto.constants)} consts, {len(proto.locals)} locals, "
        f"{len(proto.protos)} subprotos, vararg={proto.is_vararg})"
    )
    for i, w in enumerate(proto.code):
        out.append(fmt_insn(i, w, proto))
    if proto.constants:
        out.append("  -- constants:")
        for i, k in enumerate(proto.constants):
            out.append(f"      K[{i}] = {format_const(k)}")
    if proto.locals:
        out.append("  -- locals:")
        for i, (n, a, b) in enumerate(proto.locals):
            out.append(f"      L[{i}] = {n!r} pc=[{a},{b}]")
    for i, sub in enumerate(proto.protos):
        out.append("")
        out.extend(disasm_proto(sub, depth + 1, f"{idx_path}.{i}"))
    return out


# ---------------------------------------------------------------------------
# Bundle scanning.
#
# Approach: walk the file looking for JDLZ magic. For each block, try to
# decompress it; if the result starts with the Lua 5.0 signature, parse the
# whole chunk and report (bundle-offset, decomp-size, source-name).
#
# Note that JDLZ blocks can also wrap non-Lua payloads — those decompress
# fine but fail the LUA_SIG check; they're silently skipped.
# ---------------------------------------------------------------------------
def find_chunks(data: bytes) -> List[Tuple[int, int, int, str]]:
    """
    Returns list of (jdlz_offset, decomp_size, comp_size, source_name).
    """
    results: List[Tuple[int, int, int, str]] = []
    i = 0
    while True:
        i = data.find(JDLZ_MAGIC, i)
        if i < 0:
            break
        # Validate header before attempting decompress.
        if i + 16 > len(data) or data[i + 4] != 0x02:
            i += 1
            continue
        try:
            comp_size = jdlz_block_size(data, i)
            if comp_size <= 0 or i + comp_size > len(data):
                i += 1
                continue
            decomp = jdlz_decompress(data[i:i + comp_size])
        except Exception:
            i += 1
            continue
        if not decomp.startswith(LUA_SIG):
            i += max(comp_size, 1)
            continue
        # Parse the decompressed chunk to extract its source name.
        try:
            r = LuaReader(decomp)
            r.read_header()
            top = r.read_function()
            source = top.source
        except Exception as e:
            source = f"<parse-failed: {e}>"
        results.append((i, len(decomp), comp_size, source))
        i += comp_size
    return results


def cmd_find(args: argparse.Namespace) -> int:
    data = Path(args.bundle).read_bytes()
    hits = find_chunks(data)
    if not hits:
        print("(no JDLZ-wrapped Lua 5.0 chunks found)", file=sys.stderr)
        return 1
    print(f"# {args.bundle}: {len(hits)} Lua chunk(s)")
    print(f"# {'jdlz-off':>10s}  {'decomp':>8s}  {'comp':>8s}  source")
    for off, dsize, csize, src in hits:
        print(f"  {off:#010x}  {dsize:>8d}  {csize:>8d}  {src}")
    return 0


def cmd_dump(args: argparse.Namespace) -> int:
    data = Path(args.bundle).read_bytes()
    off = int(args.offset, 0)
    if data[off:off + 4] != JDLZ_MAGIC:
        raise SystemExit(
            f"no JDLZ magic at {off:#x} (got {data[off:off + 4]!r})"
        )
    comp_size = jdlz_block_size(data, off)
    decomp = jdlz_decompress(data[off:off + comp_size])
    if not decomp.startswith(LUA_SIG):
        raise SystemExit(
            f"JDLZ block at {off:#x} does not decompress to a Lua chunk "
            f"(starts with {decomp[:5]!r})"
        )
    out = Path(args.output) if args.output else Path(args.bundle).with_suffix(
        f".{off:08x}.luac"
    )
    out.write_bytes(decomp)
    print(f"decompressed {comp_size} bytes -> {len(decomp)} bytes  ->  {out}")
    return 0


def cmd_decode(args: argparse.Namespace) -> int:
    data = Path(args.luac_file).read_bytes()
    r = LuaReader(data)
    r.read_header()
    top = r.read_function()
    for ln in disasm_proto(top):
        print(ln)
    return 0


# ---------------------------------------------------------------------------
# CLI plumbing.
# ---------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="lua-disasm",
        description="NFSMW Lua 5.0 bytecode tool (flipped-A, JDLZ-wrapped).",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_find = sub.add_parser("find", help="locate JDLZ-wrapped Lua 5.0 chunks")
    p_find.add_argument("bundle")
    p_find.set_defaults(func=cmd_find)

    p_dump = sub.add_parser("dump", help="decompress one chunk to a .luac")
    p_dump.add_argument("bundle")
    p_dump.add_argument("offset", help="byte offset of the JDLZ block")
    p_dump.add_argument("-o", "--output", help="output file path")
    p_dump.set_defaults(func=cmd_dump)

    p_dec = sub.add_parser("decode", help="disassemble a Lua 5.0 chunk file")
    p_dec.add_argument("luac_file")
    p_dec.set_defaults(func=cmd_decode)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
