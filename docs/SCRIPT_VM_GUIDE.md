# SCRIPT_VM_GUIDE.md — NFSMW Lua 5.0.2 Script VM, Natives, and Tooling

This guide consolidates everything currently known about the gameplay scripting
runtime inside `speed.exe`: the embedded Lua virtual machine, its custom
instruction encoding, the coroutine plumbing, the C++ native bindings exposed
to scripts, and the `tools/lua-disasm/` workflow used to extract and decode
bytecode from the shipping bundles.

It is intended both as a reference for anyone reverse-engineering a routine in
`0x606xxx-0x615xxx` and as a how-to for modders who want to intercept or
replace gameplay scripts.

---

## 1. Overview — NFSMW VM = vanilla Lua 5.0.2

The gameplay scripting VM embedded in `speed.exe` is **not a custom Lua-like
language**. It is literal, byte-for-byte **Lua 5.0.2** — the same reference
implementation released by PUC-Rio in 2004.

This was confirmed by matching error strings extracted from `speed.exe` against
the upstream `lua-5.0.2` source tarball. Three signatures are byte-identical:

- `"binary string"`
- `"attempt to yield across metamethod/C-call boundary"`
- `"`for' initial value must be a number"`

(Note the unusual backtick-then-apostrophe quoting in the third string — a
PUC-Rio idiom found nowhere else.)

**Implication.** When working in the address range `0x606xxx-0x615xxx`, you
can use the upstream `lua-5.0.2` source as a Rosetta stone. Any unnamed
function in this range almost certainly maps 1:1 to a function in `lvm.c`,
`ldo.c`, `lfunc.c`, `lstate.c`, `lapi.c`, `lstring.c`, or `ltable.c`. The
data structures (`lua_State`, `Proto`, `Closure`, `TValue`, `Table`, `CallInfo`)
are unchanged save for the two storage quirks described below.

Two things differ from upstream:

1. **iABC bit layout is flipped** (see §2).
2. **Chunk header omits the test number; `lua_Number` is 32-bit float** (see §10).

Bytecode files are JDLZ-wrapped on disk (see §10).

---

## 2. Instruction encoding twist — POS_A=24 vs canonical POS_A=6

Stock Lua 5.0 packs the `A` operand at bits 6..13 of the instruction word
(immediately above the opcode). NFSMW moves `A` to the **high byte** (bits
24..31), pushing `C` down to bit 6 and `B` down to bit 15:

```
Stock Lua 5.0:
            31           23           14         6      0
            +------------+------------+----------+------+
  iABC      |     B      |     C      |    A     |  OP  |
            +------------+------------+----------+------+
  POS_OP=0  POS_A=6  POS_C=14  POS_B=23

NFSMW:
            31           23           14         6      0
            +-----+------------+------------+----+------+
  iABC      |  A  |     B      |     C      | -- |  OP  |
            +-----+------------+------------+----+------+
  POS_OP=0  POS_C=6  POS_B=15  POS_A=24
```

Field widths are the same (`SIZE_OP=6`, `SIZE_A=8`, `SIZE_B=9`, `SIZE_C=9`),
only the **shifts** differ. `Bx` (and `sBx`) occupy bits 6..23 — 18 bits
wide, same as upstream — sitting under `A` instead of beside it.

In Python:

```python
op  =  insn        & 0x3F
c   = (insn >> 6)  & 0x1FF
b   = (insn >> 15) & 0x1FF
a   = (insn >> 24) & 0xFF
bx  = (insn >> 6)  & 0x3FFFF   # 18-bit unsigned
sbx = bx - 131071              # canonical sBx bias (2^17 - 1)
```

**RK threshold is unchanged**: `MAXSTACK = 250`. If `B` or `C` is `>= 250`,
the value indexes the constant pool (`K[val - 250]`) instead of the register
file (`R[val]`). All 35 opcodes have the same numeric IDs and semantics as
upstream Lua 5.0.

Why was this done? Pure guess: the EA Black Box build pipeline emitted the
encoding from a fork of `lopcodes.h` with rotated `POS_*` constants — either
deliberately to break casual hex-poke modding, or as a leftover from a
console-byte-order experiment. Either way, the change is purely cosmetic at
the dispatch level — the jump table indexes by `op & 0x3f` and reads the
operands with the new shifts.

**Consequence for tooling.** A stock `luac -l` from a clean `lua-5.0.2`
build will print the right opcode mnemonics for an NFSMW chunk but will then
display **garbage operands** (it shifts by the wrong amounts). You must use
`tools/lua-disasm/` or any tool that knows the flipped layout.

---

## 3. Dispatch loop — `ExecuteLuaVMOpcodes @ 0x0060e9d0`

This is `luaV_execute` — the main bytecode dispatch loop.

```
ExecuteLuaVMOpcodes @ 0x0060e9d0
```

Typical structure (matches `lvm.c` from lua-5.0.2):

1. Read `L->ci` (the current `CallInfo`) into a register.
2. Restore `pc` from `ci.savedpc` (re-entrant after yield/call).
3. Top-of-loop label at `LAB_0060e9e0`: fetch instruction at `*pc++`,
   mask off opcode (`& 0x3f`), index the 35-entry jump table at
   `0x0060fbbc`, jump.
4. Each handler reads operands using the **NFSMW** shifts (POS_A=24,
   POS_B=15, POS_C=6), performs its work, and jumps back to the top of the
   loop.
5. A yield prelude detects `ci->status & 0x10` (CIST_YIELDED) at top of
   loop and exits gracefully (see §5).

Supporting functions in the same module:

| Address      | Name (renamed)                          | Upstream equivalent          |
|--------------|-----------------------------------------|------------------------------|
| `0x0060e9d0` | `ExecuteLuaVMOpcodes`                   | `luaV_execute`               |
| `0x006126a0` | `CallLuaScriptFunctionD`                | `luaD_call`                  |
| `0x0060e7d0` | `PrecallLuaFunctionFrame`               | `luaD_precall`               |
| `0x00606d50` | `HandleLuaReturnFromFrame`              | `luaD_poscall`               |
| `0x00606c20` | `HandleLuaCallHookEntry`                | call-hook entry              |
| `0x00607f20` | `HandleLuaTraceexecHook`                | line/count traceexec hook    |
| `0x00606b60` | `GrowLuaStackByDelta`                   | `luaD_checkstack`            |
| `0x00606af0` | `ResizeLuaStackArray`                   | `luaD_reallocstack`          |
| `0x00606980` | `InvokeLuaErrorHandlerAndAbort`         | `luaD_throw`                 |
| `0x0060b9d0` | `CloseLuaOpenUpvaluesUpTo`              | `luaF_close`                 |

`luaD_call` keeps the C-recursion counter at `L+0x2e` (a `byte`), guarding
against runaway Lua-from-C re-entry.

---

## 4. The 35-opcode jump table @ `0x0060fbbc`

The dispatch table is **35 × 4-byte pointers** indexed by the low 6 bits of
the instruction word. Below is the verified mapping; addresses are the
handler labels inside `ExecuteLuaVMOpcodes`.

| Op   | Name      | Mode | Handler addr | Notes                                     |
|------|-----------|------|--------------|-------------------------------------------|
| 0x00 | MOVE      | ABC  | `0x0060ea92` | `R[A] = R[B]`                             |
| 0x01 | LOADK     | ABx  | `0x0060eaaf` | `R[A] = K[Bx]`                            |
| 0x02 | LOADBOOL  | ABC  | `0x0060eacf` | `R[A] = (bool)B`; if C, skip next insn    |
| 0x03 | LOADNIL   | ABC  | `0x0060eaf8` | `R[A..B] = nil`                           |
| 0x04 | GETUPVAL  | ABC  | `0x0060eb22` | `R[A] = U[B]`                             |
| 0x05 | GETGLOBAL | ABx  | `0x0060eb45` | `R[A] = G[K[Bx]]` (Bx is string name)     |
| 0x06 | GETTABLE  | ABC  | `0x0060ec89` | `R[A] = R[B][RK(C)]`                      |
| 0x07 | SETGLOBAL | ABx  | `0x0060eda0` | `G[K[Bx]] = R[A]`                         |
| 0x08 | SETUPVAL  | ABC  | `0x0060edc8` | `U[B] = R[A]`                             |
| 0x09 | SETTABLE  | ABC  | `0x0060edeb` | `R[A][RK(B)] = RK(C)`                     |
| 0x0a | NEWTABLE  | ABC  | `0x0060ee55` | `R[A] = {}` with array hint B, hash hint C|
| 0x0b | SELF      | ABC  | `0x0060ef09` | `R[A+1] = R[B]; R[A] = R[B][RK(C)]`       |
| 0x0c | ADD       | ABC  | `0x0060efd9` | `R[A] = RK(B) + RK(C)`                    |
| 0x0d | SUB       | ABC  | `0x0060f069` | `R[A] = RK(B) - RK(C)`                    |
| 0x0e | MUL       | ABC  | `0x0060f0d9` | `R[A] = RK(B) * RK(C)`                    |
| 0x0f | DIV       | ABC  | `0x0060f14d` | `R[A] = RK(B) / RK(C)`                    |
| 0x10 | POW       | ABC  | `0x0060f1c9` | `R[A] = RK(B) ^ RK(C)`                    |
| 0x11 | UNM       | ABC  | `0x0060f239` | `R[A] = -R[B]`                            |
| 0x12 | NOT       | ABC  | `0x0060f2f4` | `R[A] = not R[B]`                         |
| 0x13 | CONCAT    | ABC  | `0x0060f336` | `R[A] = R[B] .. R[B+1] .. ... .. R[C]`    |
| 0x14 | JMP       | AsBx | `0x0060f372` | `pc += sBx`                               |
| 0x15 | EQ        | ABC  | `0x0060f38f` | `if (RK(B)==RK(C)) ~= A then pc++`        |
| 0x16 | LT        | ABC  | `0x0060f436` | `if (RK(B)< RK(C)) ~= A then pc++`        |
| 0x17 | LE        | ABC  | `0x0060f4a1` | `if (RK(B)<=RK(C)) ~= A then pc++`        |
| 0x18 | TEST      | ABC  | `0x0060f52a` | `if (R[B]<=>C) then R[A]=R[B] else pc++`  |
| 0x19 | CALL      | ABC  | `0x0060f595` | `R[A], ... ,R[A+C-2] = R[A](R[A+1],..)`   |
| 0x1a | TAILCALL  | ABC  | `0x0060f595` | shared dispatch with CALL                 |
| 0x1b | RETURN    | ABC  | `0x0060fa27` | return `R[A], ..., R[A+B-2]`              |
| 0x1c | FORLOOP   | AsBx | `0x0060f5f6` | numeric `for` step                        |
| 0x1d | TFORLOOP  | ABC  | `0x0060f72f` | generic `for` step                        |
| 0x1e | TFORPREP  | AsBx | `0x0060f7b7` | generic `for` prepare                     |
| 0x1f | SETLIST   | ABx  | `0x0060f837` | bulk array assignment                     |
| 0x20 | SETLISTO  | ABx  | `0x0060f837` | shared dispatch with SETLIST              |
| 0x21 | CLOSE     | ABC  | `0x0060f8db` | close all open upvalues up through R[A]   |
| 0x22 | CLOSURE   | ABx  | `0x0060f90d` | `R[A] = closure(KPROTO[Bx], ...)`         |

Notes:

- `CALL` and `TAILCALL` share `0x0060f595`. The handler reads `op` to
  branch between the two return-path policies (`luaD_precall` vs.
  `tailcall` re-use of the current `CallInfo`).
- `SETLIST` and `SETLISTO` share `0x0060f837`. They differ only in
  whether the count comes from `B` or is "to top".
- The jump table is 35 entries even though Lua 5.0 has 35 op IDs
  (`OP_MOVE`..`OP_CLOSURE`); IDs `>0x22` are not used and would index
  past the table — the VM trusts the bytecode is well-formed (loaded
  from `luac` output).

---

## 5. Coroutines

NFSMW uses Lua 5.0's stock coroutine machinery. The two entry points:

| Address      | Name                                  | Equivalent     |
|--------------|---------------------------------------|----------------|
| `0x006150e0` | `ResumeLuaCoroutineState`             | `lua_resume`   |
| `0x006138b0` | `SuspendLuaCoroutineYield`            | `lua_yield`    |
| `0x00612710` | `HandleLuaResumeContinuation`         | pcall'd body that re-enters `luaV_execute` after yield |

### Yield protocol (4 steps)

1. **`lua_yield` sets `L->ci->status |= 0x10`** — the `CIST_YIELDED` bit.
2. The next time `luaV_execute` reaches the top of its dispatch loop, the
   prelude detects `0x10`, **saves `pc` into `ci.savedpc`**, sets
   `status = 0x18` (yielded + persisted), and returns NULL up the C stack.
3. The Lua-only frame stack is **preserved** — there is no need to unwind
   C frames because no native call straddled the yield (Lua 5.0 forbids
   yielding across a metamethod/C-call boundary, hence that famous error
   string).
4. **`lua_resume`** calls `HandleLuaResumeContinuation @ 0x612710`. That
   function copies the new "yielded-in" arguments into the slot vacated by
   the yield, re-reads `ci.savedpc`, and re-enters `luaV_execute` mid-loop
   at `LAB_0060e9e0`.

### "Run" / "Suspend" gameplay natives are NOT coroutines

A common confusion: there are gameplay natives at `0x6048d0` ("Run") and
`0x6048e0` ("Suspend"). These are **not** Lua coroutine primitives. They
manipulate gameplay **Activity** objects (the higher-level task/scheduler
abstraction NFSMW uses for missions and AI plans). The actual coroutine
machinery is the `lua_resume`/`lua_yield` pair above.

---

## 6. `CallInfo` layout

The `CallInfo` struct describes one Lua-frame's metadata. It is allocated
in a stack-grown array hanging off `L+0x14` (`L->base_ci`) and walked
front-to-back as calls nest.

Layout (16-byte struct, packed):

| Offset | Field        | Notes                                             |
|--------|--------------|---------------------------------------------------|
| `+0`   | `base`       | `StkId` — first arg of this frame                 |
| `+4`   | `top`        | `StkId` — top of this frame's stack window        |
| `+8`   | `status`     | flag byte. `bit0`=C function, `bit4 (0x10)`=CIST_YIELDED, `bit3 (0x8)`=yield persisted |
| `+0xc` | `savedpc`    | saved program counter (instr ptr into `Proto.code`) |
| `+0x10`| `pc-ptr`     | live pc pointer (when this is the current frame)  |
| `+0x14`| `nresults`   | expected return count from this frame             |
| `+0x18`| `next slot`  | (padding / next `CallInfo` for tailcalls)         |

Adjacent fields on `lua_State`:

- `L+0x14` — `base_ci` (start of `CallInfo` array)
- `L+0x2e` — C-recursion counter (byte)
- `L+0x48` — `openupval` head (sorted linked list, see §7)

The yield protocol relies on `+0x8` (status) and `+0xc` (savedpc) being
preserved across the C-stack unwind — both live in heap-allocated
`CallInfo` storage, not on the C stack.

---

## 7. Script-VM stack and upvalue mechanism

### Stack window

- The **stack** is an array of 8-byte `TValue`s.
- `L->base` (offset depends on `lua_State` layout, but is the second word)
  points to the first slot of the **current frame's window**.
- `R[i]` is `((TValue*)L->base) + i`.
- `L->top` points one past the last live slot.
- `L->stack` is the base of the array, `L->stack_last` is the end.

A `TValue` packs an 8-byte typed slot:

| Tag (byte) | Lua type           | Payload                          |
|------------|--------------------|----------------------------------|
| 0          | nil                | —                                |
| 1          | boolean            | int                              |
| 2          | function (Closure*)| pointer                          |
| 3          | number (float)     | **single-precision float**       |
| 4          | string (TString*)  | pointer                          |
| 5          | table (Table*)     | pointer                          |
| 6          | native userdata    | pointer (engine objects)         |
| 7          | userdata (Udata*)  | pointer                          |

`lua_Number` here is **4-byte float**, not 8-byte double — see §10. The
tag and the 4-byte payload fit in 8 bytes total.

### Constants

The constants pool for a function is read off the active closure:

```
constants = (*(L->base - 1))->p->k
```

i.e. one slot **below** the frame base is the active closure; `closure->p`
is the `Proto*`; `p->k` is the `TValue*` constant array. `LOADK`,
`GETGLOBAL`, and `SETGLOBAL` index into this directly with `Bx`.

### Upvalues

A `Closure` carries an inline pointer array of upvalues starting at
`closure + 0x18`:

- Each entry is a 4-byte pointer to an `UpVal` struct.
- An open `UpVal` has `+8` pointing **into a parent stack slot**.
- A closed `UpVal` has `+8` pointing to its own embedded `TValue` at `+0xc`.

The `L->openupval` head at `L+0x48` is a sorted linked list keyed by the
stack-slot address each upvalue currently references. Sorting allows
`OP_CLOSE` (`luaF_close @ 0x0060b9d0`) to walk down to a target slot and
"close" every upvalue at or above it: it copies the slot's `TValue` into
the upvalue's own `+0xc` storage and flips `+8` to point there.

### `OP_CLOSURE` upvalue capture

`CLOSURE` is followed in the bytecode by `Proto.nups` "pseudo-instructions"
that the VM reads (not dispatches) — these are either `GETUPVAL` or `MOVE`
form:

- **GETUPVAL form** — the new closure shares the parent closure's existing
  upvalue (just copies the `UpVal*` pointer).
- **MOVE form** — walks `L->openupval` looking for an existing open
  `UpVal` referencing the same stack slot; reuses it if found, allocates
  a fresh one (linked into the list) otherwise.

This is exactly what `lfunc.c` does upstream; the address `0x0060f90d`
implements it for NFSMW.

---

## 8. Game-side natives — `RegisterScriptNativesGameplay @ 0x0061e750`

`RegisterScriptNativesGameplay` is a huge function that registers **~150
C++ natives** as Lua-callable globals via `lua_register` (a thin wrapper
over `lua_pushcfunction` + `lua_setglobal`).

Internally it calls a family of registrar helpers — `FUN_0061a2f0`,
`FUN_0061a370`, `FUN_0061cf50`, `FUN_0061d050`, etc. — each takes
`(const char *name, void *fnptr)` plus optional category/arity flags. Each
implementation lives in the address range `0x604xxx`..`0x612xxx`.

Some of these implementations are LAB (local-anonymous-block) targets
rather than full functions in Ghidra. That's fine: the registrar takes a
function pointer and the entry point doesn't need to be a "function" by
Ghidra's heuristic — just a valid code address.

The Lua-visible singleton **`g_pGRaceStatus @ 0x91e000`** is registered as
a Lua userdata with a metatable via `FUN_0061adf0(g_pGRaceStatus, "GRaceStatus")`.
Scripts use this to query race state (lap, position, time, etc.) without
calling any function — just field access through the metatable.

### Why this is the single best entry point

Every gameplay-side script-callable primitive funnels through one of these
registrations. If you are investigating **any** gameplay event — "what
happens when the player wins a race?", "where is a bounty awarded?", "who
triggers a cop spawn?" — the answer is:

1. Search for the **native name as a string** in the binary.
2. Find the matching `RegisterScriptNativesGameplay` call site.
3. Follow the function-pointer arg to the `_Impl`.

The naming convention in the renamed Ghidra database is `XxxYyy_Impl`
(e.g. `StartRace_Impl`, `SpawnCop_Impl`).

### Curiosity: misspelled native

`"NotifyActivityFinsihed"` (sic — "Finsihed" instead of "Finished") is
registered with that exact misspelling, preserved from the EA Black Box
source. The string hashes/dispatches by the misspelled form — any
script-side caller has to spell it wrong, too.

---

## 9. Sample native list (high-confidence mappings)

| Native (Lua-side name)     | C++ implementation                 |
|----------------------------|------------------------------------|
| `AwardPlayerBounty`        | `AwardPlayerBounty_Impl @ 0x612220`|
| `AwardPoints`              | `AwardPoints_Impl @ 0x60e030`      |
| `StartRace`                | `StartRace_Impl @ 0x60dbd0`        |
| `AbandonRace`              | `AbandonRace_Impl @ 0x60deb0`      |
| `SpawnCop`                 | `SpawnCop_Impl @ 0x60a670`         |
| `SetCopsEnabled`           | `SetCopsEnabled_Impl @ 0x604f40`   |
| `ShowPauseMenu`            | `ShowPauseMenu_Impl @ 0x6050f0`    |
| `ShowRaceOverSummary`      | `ShowRaceOverSummary_Impl @ 0x6120c0`|
| `SetWorldHeat`             | `SetWorldHeat_Impl` (in 0x604xxx range) |
| `NotifyActivityFinsihed`   | (LAB inside `0x604xxx`)            |

Many more (~30) have been renamed with the `_Impl` suffix in the Ghidra
database; the full list is most easily enumerated by listing all functions
matching `*_Impl` in the project. The remaining ~120 are unnamed or named
by string-reference only.

### Where to look for specific subsystems

- **Cops / pursuit**: search natives starting with `Cop`, `Pursuit`,
  `Heat` (also see `project_cop_ai_pursuit.md`).
- **Race state**: `StartRace`, `AbandonRace`, `EndRace`, `IsRaceXxx`.
- **Career**: `MilestoneXxx`, `CareerXxx` (also see
  `project_career_milestones.md`).
- **UI / menus**: `Show*`, `Hide*`, `NotifyMenu*`, `FE*` (also see
  `project_fe_engine.md`).
- **AI / driving**: `AIGoal*`, `AISet*`, `SetAI*`.
- **World / streaming**: `LoadRegion`, `UnloadXxx`, `SetWorldXxx`.
- **Activities** (high-level scheduler): `Run`, `Suspend`, `Activity*`,
  `NotifyActivityFinsihed`.

---

## 10. `tools/lua-disasm/` usage

Bytecode files (`.luac`) are stored inside the gameplay bundle. The shipping
PC build has Lua chunks only in `gameplay.bun`; `GlobalB.bun`, `InGameB.bun`,
and `FrontB.bun` have none.

### Chunk header (NFSMW dialect)

After `\x1bLua\x50` (magic + version 0x50 = Lua 5.0), NFSMW writes a
**10-byte explicit detail block** and **omits the canonical test number**:

| Off | Field              | Typical |
|-----|--------------------|---------|
| +0  | endianness         | `01` (little-endian) |
| +1  | sizeof(int)        | `04`    |
| +2  | sizeof(size_t)     | `04`    |
| +3  | format byte        | `00`    |
| +4  | sizeof(Instruction)| `04`    |
| +5  | SIZE_OP            | `06`    |
| +6  | SIZE_A             | `08`    |
| +7  | SIZE_B             | `09`    |
| +8  | SIZE_C             | `09`    |
| +9  | sizeof(lua_Number) | `04` (single-precision float) |

Stock Lua 5.0.2 instead writes a slightly different ordering and then an
8-byte `tx = 3.14159…` test value (so the loader can verify endian + FP
format). NFSMW skips the test number entirely — it's not present in the
chunk and the VM doesn't read for it.

Everything that follows the header — the function tree: source name, line
info table, locals, upvalue names, constant pool, nested protos, code —
is **byte-for-byte canonical Lua 5.0.2 `lundump.c` order**. Only the
instruction word **layout** and the `lua_Number` **width** differ.

### JDLZ wrapping

Each `.luac` lives inside its own **JDLZ v0x02 block** inside the (already
LZC-decompressed) bundle:

```
+---------+--------+----------+----------+---------+----------+
| "JDLZ"  | 02 ... | decomp_sz| comp_sz  | flag1/2 | payload  |
| 4 bytes | 4 byte | 4 LE     | 4 LE     | 2 bytes | (varies) |
+---------+--------+----------+----------+---------+----------+
       header (0x10)              ^         ^^
                                  +--- start of compressed stream
```

To enumerate chunks, walk the bundle looking for `JDLZ` magic, decompress
each block, and check whether the decompressed buffer starts with
`\x1bLua\x50`. The lua-disasm tool does this automatically; it silently
skips JDLZ blocks holding non-Lua data.

(JDLZ v0x02 is documented separately — see `project_jdlz_format.md` /
`tools/nfsmw_bun_reader/jdlz_nfsmw.py` for the algorithm and a
byte-perfect Python implementation.)

### Subcommands

```
lua-disasm find  <bundle>            # locate JDLZ-wrapped Lua 5.0 chunks
lua-disasm dump  <bundle> <offset>   # decompress one block to a .luac file
lua-disasm decode <luac_file>        # disassemble a chunk
```

- **`find`** returns `(jdlz_offset, decomp_size, comp_size, source_name)`
  for each chunk whose JDLZ block decompresses successfully and contains a
  Lua 5.0 header.
- **`dump`** parses the JDLZ header at `<offset>` (which must point at
  the `J` of `JDLZ`), decompresses, verifies the Lua signature, and writes
  the **decompressed** bytes to disk so `decode` can consume them.
- **`decode`** produces `luac -l`-style output.

### Example session

```sh
# 1. Find Lua chunks in the gameplay bundle.
python3 tools/lua-disasm/lua_disasm.py \
        find extracted/app/GLOBAL/decompressed_lzc/gameplay.bun

# 2. Pick an offset from the above output and dump it.
python3 tools/lua-disasm/lua_disasm.py \
        dump extracted/app/GLOBAL/decompressed_lzc/gameplay.bun 0x14F660 \
        -o /tmp/sample.luac

# 3. Disassemble.
python3 tools/lua-disasm/lua_disasm.py decode /tmp/sample.luac
```

Expected `decode` output:

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

### Install

```sh
make            # create ./lua-disasm symlink in this dir
make install    # symlink into $PREFIX/bin (default: $HOME/.local/bin)
```

### Limitations of the current tool

- **No assembler.** Round-tripping a chunk back into the bundle requires
  re-emitting the flipped-A encoding and re-wrapping in JDLZ. Not done.
- **No source-level decompiler.** Output is opcode-level, not Lua source.
  A separate decompiler pass (LuaDec-style) would be a useful follow-up.
- **Bundles only.** This tool reads `.bun` files as-is. If you have a
  `.lzc` from `app/GLOBAL/`, decompress with `nfsmw-tool jdlz GLOBAL/GAMEPLAY.LZC`
  first — the bundles in `decompressed_lzc/` are already pre-decompressed
  exactly this way.

---

## 11. Hooking scripts — replacing a native, intercepting bytecode

There are two practical attack surfaces for modders.

### 11a. Replacing a native (recommended)

Each native registration boils down to a 4-byte function pointer stored in
the Lua globals table (or in a closure's upvalue slot, depending on the
registrar variant). Easiest path:

1. Locate the call site in `RegisterScriptNativesGameplay @ 0x0061e750`
   that registers the target name (`"SpawnCop"`, etc.). The function
   pointer is a 32-bit immediate baked into the call instruction.
2. Patch the `push <fnptr>` immediate to point to your replacement DLL's
   trampoline.
3. Your replacement must match the standard Lua-C function signature:
   `int (*)(lua_State *L)`. Returns the number of results pushed on the
   Lua stack.

For runtime hooking (instead of binary patching), hook
`lua_register` itself or rewrite the global table entry post-registration
by walking globals from `L->_gt` (the globals table TValue).

The implementations all use `lua_to*`/`lua_push*` accessor calls — these
are stock Lua C-API functions. Their addresses can be derived by
single-stepping any of the `_Impl` functions and noting which API
calls they make.

### 11b. Intercepting at the bytecode level

For experimenting without recompiling C code, you can swap the `.luac`
chunk inside the bundle:

1. `lua-disasm find <bundle>` to locate the chunk.
2. `lua-disasm dump` to extract `.luac`.
3. Edit by writing a fresh `.lua` source file, compiling with a patched
   `luac` (you need a `luac` that emits the **NFSMW** flipped encoding
   and the NFSMW header — currently no public tool does both; assembling
   one is on the lua-disasm TODO list).
4. JDLZ-compress the new `.luac`, splice it back over the original block
   (matching the JDLZ-block size; if smaller, pad; if larger, rebuild the
   surrounding bundle TOC).

A more tractable variant: hook `lua_load`/`luaU_undump` (the chunk loader)
to substitute a chunk from a side-loaded path. The loader lives in
`0x60bxxx`-`0x60cxxx`; it reads the magic, the 10-byte header, then
delegates to `LoadFunction` (recursive) which reads code, lines, locals,
constants, sub-protos.

### 11c. Intercepting `luaV_execute` directly

For trace logging or single-instruction debugging:

- Patch the JMP at the top of `ExecuteLuaVMOpcodes` to redirect through
  a trampoline that logs `(L, ci, pc, *pc)`.
- The 35 jump table entries at `0x0060fbbc` can be replaced with
  trampolines too — useful for opcode-level profiling or for swapping in
  a sandboxed version of, e.g., `OP_CALL`.

For coroutine debugging, hook `SuspendLuaCoroutineYield @ 0x006138b0`
and `ResumeLuaCoroutineState @ 0x006150e0`. Yielding across a C boundary
trips an error you'll see immediately if your hook is misbehaving.

---

## Appendix A — Source cross-reference

For any unnamed function in `0x606xxx-0x615xxx`, consult these
upstream Lua 5.0.2 source files (Rosetta-stone candidates):

| Range            | Upstream file | Typical contents                          |
|------------------|---------------|-------------------------------------------|
| `0x606xxx`       | `ldo.c`       | call/return frames, error handling        |
| `0x607xxx`       | `ldo.c`, `ldebug.c` | hooks, stack traceback              |
| `0x608xxx`-`0x609xxx` | `lapi.c`, `lobject.c` | C-API surface, TValue helpers   |
| `0x60axxx`       | `lstring.c`, `ltable.c` | string/table internals           |
| `0x60bxxx`       | `lfunc.c`, `lundump.c` | closures, upvalues, chunk loader   |
| `0x60cxxx`       | `lundump.c`, `lstate.c` | loader, state init                |
| `0x60dxxx`-`0x60exxx` | `lvm.c` | bytecode dispatch                          |
| `0x60fxxx`       | `lvm.c` (jump table + handlers) |                              |
| `0x610xxx`-`0x611xxx` | `lapi.c` | high-level C API                         |
| `0x612xxx`-`0x613xxx` | `lstate.c`, `ldo.c`, coroutines |                       |
| `0x614xxx`-`0x615xxx` | coroutine `lua_resume`/`lua_yield`, `ltm.c` (metamethods) |   |

The boundaries above are approximate. When in doubt, match against the
upstream file by string constants and function-call signatures.

---

## Appendix B — Quick reference card

```
VM entry      : ExecuteLuaVMOpcodes        0x0060e9d0
Jump table    : opcode handlers, 35 × 4    0x0060fbbc
Native reg.   : RegisterScriptNativesGameplay 0x0061e750
Resume        : ResumeLuaCoroutineState    0x006150e0
Yield         : SuspendLuaCoroutineYield   0x006138b0
GRaceStatus   : g_pGRaceStatus             0x0091e000

Instruction   : op = insn & 0x3F
                a  = (insn >> 24) & 0xFF
                b  = (insn >> 15) & 0x1FF
                c  = (insn >>  6) & 0x1FF
                bx = (insn >>  6) & 0x3FFFF
                RK threshold = 250

Header        : 1B 4C 75 61 50 <10-byte detail block> (no test number)
Number        : 4-byte float (not double)

Bytecode      : JDLZ v0x02 wrapped, inside gameplay.bun only
Tool          : tools/lua-disasm/ (find / dump / decode)
```

