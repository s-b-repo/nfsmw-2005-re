# lua-disasm — NFSMW Lua 5.0 bytecode tool

`lua-disasm` disassembles Lua 5.0 bytecode chunks shipped inside NFSMW (2005)
asset bundles. NFSMW uses **vanilla Lua 5.0.2** with **one local modification**:
the instruction encoding rearranges the `iABC` operand fields so that `A` lives
in the high byte of the 32-bit word. Stock `luac -l` from a clean lua-5.0.2
build will load the chunk header successfully but produce garbage operand
columns, because it shifts `A` to bit 6.

## The encoding twist

Lua 5.0's canonical bit layout (lopcodes.h):

```
            31           23           14         6      0
            +------------+------------+----------+------+
  iABC      |     B      |     C      |    A     |  OP  |
            +------------+------------+----------+------+
            |          Bx (or sBx)    |    A     |  OP  |
            +-------------------------+----------+------+

  POS_OP=0  SIZE_OP=6
  POS_A =6  SIZE_A=8
  POS_C =14 SIZE_C=9
  POS_B =23 SIZE_B=9
```

NFSMW's `speed.exe` (confirmed by `ExecuteLuaVMOpcodes @ 0x0060e9d0` and the
jump table at `0x0060fbbc`):

```
            31           23           14         6      0
            +-----+------------+------------+----+------+
  iABC      |  A  |     B      |     C      | -- |  OP  |
            +-----+------------+------------+----+------+
            |  A  |             Bx (or sBx)      |  OP  |
            +-----+------------+------------+----+------+

  POS_OP=0  SIZE_OP=6
  POS_C =6  SIZE_C=9
  POS_B =15 SIZE_B=9
  POS_A =24 SIZE_A=8
```

In Python:

```python
op  =  insn        & 0x3F
c   = (insn >> 6)  & 0x1FF
b   = (insn >> 15) & 0x1FF
a   = (insn >> 24) & 0xFF
bx  = (insn >> 6)  & 0x3FFFF   # 18-bit
sbx = bx - 131071              # canonical Lua 5.0 sBx bias
```

Every other byte of the chunk format (header, constants, line info, debug
locals, nested protos) is byte-for-byte canonical Lua 5.0.2 — only the
instruction word changes. The 35 opcodes (`OP_MOVE`..`OP_CLOSURE`) and the
`MAXSTACK = 250` RK threshold are identical to upstream.

## Opcode map (35 ops, 0x00..0x22)

| Op   | Name      | Mode | Notes                              |
|------|-----------|------|------------------------------------|
| 0x00 | MOVE      | ABC  |                                    |
| 0x01 | LOADK     | ABx  | Bx = constant pool index           |
| 0x02 | LOADBOOL  | ABC  | A = R[A], B = bool, C = jump skip  |
| 0x03 | LOADNIL   | ABC  |                                    |
| 0x04 | GETUPVAL  | ABC  |                                    |
| 0x05 | GETGLOBAL | ABx  | Bx = string constant (name)        |
| 0x06 | GETTABLE  | ABC  | C is RK                            |
| 0x07 | SETGLOBAL | ABx  |                                    |
| 0x08 | SETUPVAL  | ABC  |                                    |
| 0x09 | SETTABLE  | ABC  | B and C are RK                     |
| 0x0a | NEWTABLE  | ABC  |                                    |
| 0x0b | SELF      | ABC  | C is RK                            |
| 0x0c | ADD       | ABC  | B and C are RK                     |
| 0x0d | SUB       | ABC  | B and C are RK                     |
| 0x0e | MUL       | ABC  | B and C are RK                     |
| 0x0f | DIV       | ABC  | B and C are RK                     |
| 0x10 | POW       | ABC  | B and C are RK                     |
| 0x11 | UNM       | ABC  |                                    |
| 0x12 | NOT       | ABC  |                                    |
| 0x13 | CONCAT    | ABC  |                                    |
| 0x14 | JMP       | AsBx | pc += sBx                          |
| 0x15 | EQ        | ABC  | B and C are RK                     |
| 0x16 | LT        | ABC  | B and C are RK                     |
| 0x17 | LE        | ABC  | B and C are RK                     |
| 0x18 | TEST      | ABC  |                                    |
| 0x19 | CALL      | ABC  |                                    |
| 0x1a | TAILCALL  | ABC  |                                    |
| 0x1b | RETURN    | ABC  |                                    |
| 0x1c | FORLOOP   | AsBx |                                    |
| 0x1d | TFORLOOP  | ABC  |                                    |
| 0x1e | TFORPREP  | AsBx |                                    |
| 0x1f | SETLIST   | ABx  |                                    |
| 0x20 | SETLISTO  | ABx  |                                    |
| 0x21 | CLOSE     | ABC  |                                    |
| 0x22 | CLOSURE   | ABx  | Bx = prototype index               |

## Subcommands

```
lua-disasm find  <bundle>            # locate Lua 5.0 chunks (offset + size)
lua-disasm dump  <bundle> <offset>   # extract one chunk to a .luac file
lua-disasm decode <luac_file>        # disassemble a chunk
```

`find` scans for the 5-byte signature `\x1bLua\x50` and **parses each candidate
chunk fully** to determine its real on-disk length and the main-function's
source name. Failed candidates are reported with `size=?` so the user can
sanity-check.

`dump` re-parses the chunk header at the given offset, then writes exactly
that many bytes to a `.luac` file.

`decode` produces output that mimics `luac -l`:

```
function main <@scripts/foo.lua:1,99> (42 insns, 0 upvals, 0 params, ...)
     1   [3]   GETGLOBAL  0 0    ; "print"
     2   [3]   LOADK      1 1    ; "hello, world"
     3   [3]   CALL       0 2 1
     4   [4]   RETURN     0 1
  -- constants:
      K[0] = "print"
      K[1] = "hello, world"
```

## Test command

```sh
# 1. Find chunks in a bundle.
python3 tools/lua-disasm/lua_disasm.py \
        find extracted/app/GLOBAL/decompressed_lzc/gameplay.bun

# 2. Pick an offset from the above output and dump it.
python3 tools/lua-disasm/lua_disasm.py \
        dump extracted/app/GLOBAL/decompressed_lzc/gameplay.bun 0x... \
        -o /tmp/sample.luac

# 3. Disassemble.
python3 tools/lua-disasm/lua_disasm.py decode /tmp/sample.luac
```

Expected: `find` prints at least one row with a non-`?` size and a `source`
that ends in `.lua`; `decode` prints a function header followed by lines of
the form `<pc> [<line>] <OPNAME> <ops> ; <comment>`, ending with a `RETURN`.

## Install

```sh
make            # create ./lua-disasm symlink in this dir
make install    # symlink into $PREFIX/bin (default: $HOME/.local/bin)
```

## Limitations

- No bytecode **assembler** (yet). For round-tripping you'd also need to
  re-emit the flipped-A encoding when writing chunks back into a bundle.
- No source-level decompiler — `lua-disasm decode` is strictly low-level.
- `find` only matches Lua 5.0 (`\x1bLua\x50`). If a chunk is JDLZ-compressed
  inside the bundle, decompress it first with `nfsmw-tool jdlz` (the bundles
  in `decompressed_lzc/` already are).
