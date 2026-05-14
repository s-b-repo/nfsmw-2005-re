#!/usr/bin/env python3
"""
lua-disasm — NFSMW (Lua 5.0.2, flipped-A encoding) bytecode tool.

NFSMW's gameplay scripting is vanilla Lua 5.0.2 with **one twist**:
the iABC field layout is reversed compared to stock Lua 5.0.

  Stock Lua 5.0 :  B[23:32] | C[14:23] | A[6:14]  | OP[0:6]
                   (POS_A = 6, POS_B = 23, POS_C = 14)

  NFSMW build   :  A[24:32] | B[15:24] | C[6:15]  | OP[0:6]
                   (POS_A = 24, POS_B = 15, POS_C = 6)

Bx / sBx are the same 18-bit wide field at bits [6:24], and the
constant/register split threshold for B/C (MAXSTACK 250) is unchanged.
Opcode numbers 0..0x22 and their semantics are identical to upstream
Lua 5.0.2.

Subcommands
-----------
  lua-disasm find <bundle>            Scan a file for embedded Lua 5.0 chunks,
                                      print (offset, size, source-name).
  lua-disasm dump <bundle> <offset>   Extract one chunk to a .luac file
                                      (size is parsed from the chunk header).
  lua-disasm decode <luac>            Disassemble a chunk (NFSMW encoding)
                                      to human-readable text.

The decode output mimics `luac -l`:

    function <source:line,line> (N instructions, N upvalues, N locals, ...)
      1   [line]  OPNAME           A B C   ; comment
      ...
"""

from __future__ import annotations

import argparse
import os
import struct
import sys
from pathlib import Path
from typing import Any, BinaryIO, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Opcode table (35 entries, indices 0x00..0x22). Mode lets us pretty-print.
# ---------------------------------------------------------------------------
# Mode legend:
#   ABC   — three operands, B/C may be RK (>=250 -> constant)
#   ABx   — A + 18-bit unsigned Bx
#   AsBx  — A + 18-bit signed Bx (sBx = Bx - 131071)

ABC, ABx, AsBx = "ABC", "ABx", "AsBx"

# Per-opcode B/C "is RK candidate" flags. Mirrors lopcodes.c in Lua 5.0.
# (True => operand is interpreted as RK when >=250.)
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
SBX_BIAS = 131071       # (1<<17) - 1, the canonical Lua 5.0 sBx bias.

# Canonical Lua 5.0 chunk signature: "\x1bLua" + version 0x50.
LUA_SIG = b"\x1bLua\x50"


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
    """Format a B/C operand as either a register or a constant ref."""
    if is_rk and val >= MAXSTACK:
        return f"K[{val - MAXSTACK}]"
    return f"R[{val}]"


# ---------------------------------------------------------------------------
# Chunk parser — reads a Lua 5.0 binary chunk and returns its size + Proto.
# We follow upstream lundump.c layout exactly; only the *instruction encoding*
# differs in NFSMW, so the header / constants / debug tables are byte-for-byte
# canonical Lua 5.0.
# ---------------------------------------------------------------------------
class LuaReader:
    """Cursor over a bytes blob; knows the chunk's endianness + int sizes."""

    def __init__(self, data: bytes, offset: int = 0) -> None:
        self.data = data
        self.pos = offset
        # Filled in by read_header():
        self.endian = "<"        # '<' little-endian, '>' big-endian.
        self.size_int = 4
        self.size_size_t = 4
        self.size_insn = 4
        self.size_number = 8
        self.int_number = False  # If true, Number is integer not double.

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
        if self.int_number:
            return struct.unpack(self.endian + "q", raw)[0]
        if self.size_number == 8:
            return struct.unpack(self.endian + "d", raw)[0]
        if self.size_number == 4:
            return struct.unpack(self.endian + "f", raw)[0]
        return int.from_bytes(raw, "little" if self.endian == "<" else "big")

    def string(self) -> bytes:
        n = self.size_t()
        if n == 0:
            return b""
        raw = self._take(n)
        # Lua stores trailing '\0' — strip it for display.
        return raw[:-1] if raw.endswith(b"\x00") else raw

    # --- chunk header ------------------------------------------------------
    def read_header(self) -> None:
        sig = self._take(4)
        if sig != b"\x1bLua":
            raise ValueError(f"bad signature {sig!r} at {self.pos - 4:#x}")
        version = self.byte()
        if version != 0x50:
            raise ValueError(f"not Lua 5.0 (version={version:#x})")
        endian = self.byte()
        self.endian = "<" if endian else ">"
        self.size_int = self.byte()
        self.size_size_t = self.byte()
        self.size_insn = self.byte()
        self.size_number = self.byte()
        self.int_number = bool(self.byte())
        # Sanity-test the number format: Lua writes a test value here (3.14159...)
        # We only need to *consume* it.
        self.number()

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
            elif t == 1:                     # LUA_TBOOLEAN
                p.constants.append(bool(self.byte()))
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
    """A loaded Lua 5.0 function prototype (post-parse)."""

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
        self.protos: List[Proto] = []
        self.code: List[int] = []


# ---------------------------------------------------------------------------
# Disassembly formatter.
# ---------------------------------------------------------------------------
def format_const(k: Any) -> str:
    """Compact, single-line repr for a constant — keeps disasm scannable."""
    if k is None:
        return "nil"
    if isinstance(k, bool):
        return "true" if k else "false"
    if isinstance(k, (int, float)):
        return repr(k)
    # bytes (string)
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

    # Operand display + a trailing "; ..." comment when it adds info
    # (constant name resolution, jump target, etc.).
    comment = ""
    if mode == ABC:
        operands = f"{a} {b} {c}"
        # Pretty constant-resolve for common cases
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
    header = (
        f"function {idx_path} <{src}:{proto.line_defined},{last_line}> "
        f"({len(proto.code)} insns, {proto.num_upvals} upvals, "
        f"{proto.num_params} params, {proto.max_stack} stack, "
        f"{len(proto.constants)} consts, {len(proto.locals)} locals, "
        f"{len(proto.protos)} subprotos, vararg={proto.is_vararg})"
    )
    out.append(header)
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
# Subcommands.
# ---------------------------------------------------------------------------
def find_chunks(data: bytes) -> List[Tuple[int, int, str]]:
    """
    Scan `data` for Lua 5.0 chunk signatures. For each hit, attempt to parse
    the full chunk to determine its on-disk length and main-function source
    name. Returns list of (offset, size_bytes, source_name).

    A chunk that fails to parse is reported with size=-1.
    """
    results: List[Tuple[int, int, str]] = []
    i = 0
    while True:
        i = data.find(LUA_SIG, i)
        if i < 0:
            break
        try:
            r = LuaReader(data, i)
            r.read_header()
            top = r.read_function()
            size = r.pos - i
            results.append((i, size, top.source))
            i = r.pos          # Skip past parsed chunk for next scan
        except Exception as e:
            results.append((i, -1, f"<parse-failed: {e}>"))
            i += 1            # Step forward and keep scanning
    return results


def cmd_find(args: argparse.Namespace) -> int:
    data = Path(args.bundle).read_bytes()
    hits = find_chunks(data)
    if not hits:
        print("(no Lua 5.0 chunks found)", file=sys.stderr)
        return 1
    print(f"# {args.bundle}: {len(hits)} Lua chunk(s)")
    print(f"# {'offset':>10s}  {'size':>8s}  source")
    for off, size, src in hits:
        size_s = f"{size}" if size >= 0 else "?"
        print(f"  {off:#010x}  {size_s:>8s}  {src}")
    return 0


def cmd_dump(args: argparse.Namespace) -> int:
    data = Path(args.bundle).read_bytes()
    off = int(args.offset, 0)
    r = LuaReader(data, off)
    r.read_header()
    r.read_function()
    size = r.pos - off
    chunk = data[off:off + size]
    out = Path(args.output) if args.output else Path(args.bundle).with_suffix(
        f".{off:08x}.luac"
    )
    out.write_bytes(chunk)
    print(f"dumped {size} bytes from {args.bundle}@{off:#x} -> {out}")
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
        description="NFSMW Lua 5.0 bytecode tool (handles flipped-A encoding).",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_find = sub.add_parser("find", help="locate Lua 5.0 chunks in a bundle")
    p_find.add_argument("bundle")
    p_find.set_defaults(func=cmd_find)

    p_dump = sub.add_parser("dump", help="extract one chunk to a .luac file")
    p_dump.add_argument("bundle")
    p_dump.add_argument("offset", help="byte offset of chunk (decimal or 0x...)")
    p_dump.add_argument("-o", "--output", help="output file (default: <bundle>.<off>.luac)")
    p_dump.set_defaults(func=cmd_dump)

    p_dec = sub.add_parser("decode", help="disassemble a Lua 5.0 chunk file")
    p_dec.add_argument("luac_file")
    p_dec.set_defaults(func=cmd_decode)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
