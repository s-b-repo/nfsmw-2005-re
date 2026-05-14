# lua-disasm — NFSMW Lua 5.0 bytecode tool

`lua-disasm` disassembles Lua 5.0 bytecode chunks shipped inside NFSMW (2005)
asset bundles. NFSMW uses **vanilla Lua 5.0.2** with **two local quirks**:

1. **Flipped iABC encoding.** `A` lives in the high byte of the instruction
   word, not at bit 6.
2. **JDLZ-wrapped chunks.** Each `.luac` is stored inside a JDLZ v0x02 block
   inside the bundle. You can't just grep for `\x1bLua\x50`; you need to walk
   the JDLZ blocks, decompress, then check.

Stock `luac -l` from a clean lua-5.0.2 build cannot read these chunks: even if
you JDLZ-decompress one and hand it to upstream, the header layout differs
(see below) and the operand fields are shifted to different bit positions.

## Quirk 1 — the encoding twist

Stock Lua 5.0 iABC bit layout (lopcodes.h):

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

The 35 opcodes (`OP_MOVE`..`OP_CLOSURE`) and the `MAXSTACK = 250` RK threshold
are identical to upstream.

## Quirk 2 — the chunk header

After the `\x1bLua\x50` sig + version, NFSMW writes a **10-byte explicit detail
block** and **omits the canonical "test number"**:

| Off | Field              | Observed |
|-----|--------------------|----------|
| +0  | endianness         | `01` (little) |
| +1  | sizeof(int)        | `04`     |
| +2  | sizeof(size_t)     | `04`     |
| +3  | format byte        | `00`     |
| +4  | sizeof(Instruction)| `04`     |
| +5  | SIZE_OP            | `06`     |
| +6  | SIZE_A             | `08`     |
| +7  | SIZE_B             | `09`     |
| +8  | SIZE_C             | `09`     |
| +9  | sizeof(lua_Number) | `04` (single-precision float) |

(Compare: stock Lua 5.0.2 writes endian + sizeof(int) + sizeof(size_t) +
sizeof(Instr) + SIZE_INSTRUCTION + SIZE_OP + SIZE_B + sizeof(Number) + an
8-byte `tx = 3.14159…` test value.)

Everything that follows (function tree: source name, line info, locals,
constants, nested protos, code) is byte-for-byte canonical Lua 5.0.2
lundump.c order — only the *instruction word layout* and the *number width*
differ.

## Quirk 3 — JDLZ wrapping

In `extracted/app/GLOBAL/decompressed_lzc/gameplay.bun` (a `decompressed_lzc/`
bundle still contains inner JDLZ blocks per asset), each Lua chunk lives
inside its own JDLZ v0x02 block:

```
+---------+--------+----------+----------+---------+----------+
| "JDLZ"  | 02 ... | decomp_sz| comp_sz  | flag1/2 | payload  |
| 4 bytes | 4 byte | 4 LE     | 4 LE     | 2 bytes | (varies) |
+---------+--------+----------+----------+---------+----------+
       header (0x10)              ^         ^^
                                  +--- start of compressed stream
```

`lua-disasm find` walks the bundle for `JDLZ` magic, decompresses each block,
and checks whether the decompressed buffer starts with `\x1bLua\x50`.

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
lua-disasm find  <bundle>            # locate JDLZ-wrapped Lua 5.0 chunks
lua-disasm dump  <bundle> <offset>   # decompress one block to a .luac file
lua-disasm decode <luac_file>        # disassemble a chunk
```

`find` returns `(jdlz_offset, decomp_size, comp_size, source_name)` for each
chunk whose JDLZ block decompresses successfully and contains a Lua 5.0
header. JDLZ blocks holding non-Lua data are silently skipped.

`dump` parses the JDLZ header at `<offset>` (which must point at the `J`),
decompresses the block, verifies the Lua signature, and writes the
**decompressed** bytes to disk so `decode` can consume them directly.

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
# 1. Find Lua chunks in the gameplay bundle (the only bundle that has any).
python3 tools/lua-disasm/lua_disasm.py \
        find extracted/app/GLOBAL/decompressed_lzc/gameplay.bun

# 2. Pick an offset from the above output and dump it.
python3 tools/lua-disasm/lua_disasm.py \
        dump extracted/app/GLOBAL/decompressed_lzc/gameplay.bun 0x14F660 \
        -o /tmp/sample.luac

# 3. Disassemble.
python3 tools/lua-disasm/lua_disasm.py decode /tmp/sample.luac
```

Expected: `find` prints at least one `0x1bLua`-bearing chunk (in the bundle
shipped with NFSMW PC, gameplay.bun has multiple). `decode` prints a function
header followed by `<pc> [<line>] <OPNAME> <ops> ; <comment>` rows, ending
with a `RETURN`.

## Install

```sh
make            # create ./lua-disasm symlink in this dir
make install    # symlink into $PREFIX/bin (default: $HOME/.local/bin)
```

## Limitations

- **No assembler.** Round-tripping a chunk back into the bundle requires
  re-emitting the flipped-A encoding and re-wrapping in JDLZ — not done.
- **No source-level decompiler.** Output is opcode-level, not Lua source.
- **Bundles only.** This tool reads `.bun` files as-is; if you have a
  `.lzc` from `app/GLOBAL/`, decompress it first with
  `nfsmw-tool jdlz GLOBAL/GAMEPLAY.LZC` (the bundles in
  `decompressed_lzc/` are pre-decompressed exactly this way).
- **Other bundles.** Only `gameplay.bun` has Lua chunks in the shipping
  build; `GlobalB.bun`, `InGameB.bun`, `FrontB.bun` do not.
