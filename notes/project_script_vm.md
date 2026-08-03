---
name: gameplay-scripting-vm-internals
description: NFSMW gameplay scripting is vanilla **Lua 5.0.2** (confirmed by error-string signatures). 35-opcode jump table @ 0x60fbbc; main dispatch @ 0x60e9d0 (luaV_execute). ~150 game-natives registered via lua_register at 0x61e750.
metadata: 
  node_type: memory
  type: project
  originSessionId: c4edf485-e85f-4e2f-ac31-e021ba66e8d6
---

NFSMW's gameplay scripting is **vanilla Lua 5.0** (confirmed 2026-05-14 by an agent that matched the error strings — "binary string", "attempt to yield across metamethod/C-call boundary", "`for' initial value must be a number" — byte-identical to lua-5.0 source). Not a custom Lua-like; it's literal Lua 5.0.2.

## VM dispatch
- `ExecuteLuaVMOpcodes @ 0x0060e9d0` — **luaV_execute**, the main bytecode dispatch loop
- Opcode jump table @ `0x0060fbbc` — 35 × 4-byte targets, indexed by `op & 0x3f`
- `CallLuaScriptFunctionD @ 0x006126a0` — luaD_call (recursion-count at L+0x2e)
- `PrecallLuaFunctionFrame @ 0x0060e7d0` — luaD_precall (sets up Lua/C call frame)
- `HandleLuaReturnFromFrame @ 0x00606d50` — luaD_poscall
- `HandleLuaCallHookEntry @ 0x00606c20` — call-hook entry
- `HandleLuaTraceexecHook @ 0x00607f20` — line/count traceexec hook
- `GrowLuaStackByDelta @ 0x00606b60` — luaD_checkstack
- `ResizeLuaStackArray @ 0x00606af0` — luaD_reallocstack
- `InvokeLuaErrorHandlerAndAbort @ 0x00606980` — luaD_throw
- `CloseLuaOpenUpvaluesUpTo @ 0x0060b9d0` — luaF_close

## Coroutines
- `ResumeLuaCoroutineState @ 0x006150e0` — **lua_resume**
- `SuspendLuaCoroutineYield @ 0x006138b0` — **lua_yield**
- `HandleLuaResumeContinuation @ 0x00612710` — pcall'd body that re-enters luaV_execute after yield

**The gameplay "Run"/"Suspend" natives at 0x6048d0/0x6048e0 are NOT coroutine primitives** — they manipulate gameplay "Activity" objects. The actual Lua coroutine machinery is the lua_resume/lua_yield pair above.

## Opcode table (verified)
| Op | Name | Handler |
|---|---|---|
| 0x00 | MOVE | 0x60ea92 |
| 0x01 | LOADK | 0x60eaaf |
| 0x02 | LOADBOOL | 0x60eacf |
| 0x03 | LOADNIL | 0x60eaf8 |
| 0x04 | GETUPVAL | 0x60eb22 |
| 0x05 | GETGLOBAL | 0x60eb45 |
| 0x06 | GETTABLE | 0x60ec89 |
| 0x07 | SETGLOBAL | 0x60eda0 |
| 0x08 | SETUPVAL | 0x60edc8 |
| 0x09 | SETTABLE | 0x60edeb |
| 0x0a | NEWTABLE | 0x60ee55 |
| 0x0b | SELF | 0x60ef09 |
| 0x0c–0x0f | ADD/SUB/MUL/DIV | 0x60efd9–0x60f14d |
| 0x10 | POW | 0x60f1c9 |
| 0x11 | UNM | 0x60f239 |
| 0x12 | NOT | 0x60f2f4 |
| 0x13 | CONCAT | 0x60f336 |
| 0x14 | JMP | 0x60f372 |
| 0x15 | EQ | 0x60f38f |
| 0x16 | LT | 0x60f436 |
| 0x17 | LE | 0x60f4a1 |
| 0x18 | TEST | 0x60f52a |
| 0x19 | CALL | 0x60f595 |
| 0x1a | TAILCALL | 0x60f595 (shared) |
| 0x1b | RETURN | 0x60fa27 |
| 0x1c | FORLOOP | 0x60f5f6 |
| 0x1d | TFORLOOP | 0x60f72f |
| 0x1e | TFORPREP | 0x60f7b7 |
| 0x1f | SETLIST | 0x60f837 |
| 0x20 | SETLISTO | 0x60f837 (shared) |
| 0x21 | CLOSE | 0x60f8db |
| 0x22 | CLOSURE | 0x60f90d |

## Instruction encoding
32-bit word: `OP[0:6] | C[6:15] | B[15:24] | A[24:32]` for iABC; `Bx[6:24]` (18-bit) for iABx.
**RK threshold = 0xfa (250)** — B/C ≥ 250 means `K[val-250]` (constant pool) instead of `R[val]` (register).

Note: this build flips A to the high bits vs canonical Lua 5.0 (`POS_A=6` in lua-5.0.2). Opcodes and semantics are identical; only shifts differ.

## CallInfo layout (16-byte struct at L+0x14 onward, packed)
| Offset | Field |
|---|---|
| +0 | base (stack slot) |
| +4 | top (stack slot) |
| +8 | status (bit0=C fn, bit4=CIST_YIELDED) |
| +0xc | savedpc |
| +0x10 | pc-ptr |
| +0x14 | nresults? |
| +0x18 | next slot |

## Stack and upvalues
- **Stack window** = `L->base` … `L->top`. R[i] = `((TValue*)L->base) + i` (each TValue = 8 bytes).
- **Constants** = `Closure->Proto->k` (read at `(*(L->base-1))->p->k`).
- **Upvalues**: closure has inline pointer array at `closure + 0x18 + idx*4`.
  - Open: +8 points into a stack slot
  - Closed: +8 points to its own embedded TValue at +0xc
- **L->openupval head** at L+0x48 — sorted linked list keyed by stack-slot address.
- **OP_CLOSE** walks that list, copies slot value into the upvalue's own storage.
- **OP_CLOSURE** reads B pseudo-instructions: GETUPVAL form shares parent upvalue; MOVE form walks openupval to find/create.

## Calling convention (standard Lua 5.0)
Callee at `R[A]`, args at `R[A+1..A+B-1]` (B-1 = nargs; B=0 = "to top"/varargs).
CALL sets `L->top = R[A+B]` when B!=0, then luaD_precall consumes them.
Results land at `R[A]..R[A+C-2]` (C-1 = nresults; C=0 = multret).
Lua-into-Lua re-enters dispatch via `LAB_0060e9e0`; TAILCALL reuses CallInfo first.

## Yield mechanism
1. `lua_yield` sets `L->ci->status |= 0x10` (CIST_YIELDED)
2. Next opcode's prelude in luaV_execute detects bit 0x10, saves PC into `ci.savedpc`, sets status=0x18, returns NULL
3. Frame stack is **preserved** (no unwind — Lua-only frames don't need C stack)
4. `lua_resume` calls `HandleLuaResumeContinuation @ 0x612710`, which copies new yielded-in args, re-reads ci.savedpc, re-enters luaV_execute mid-loop

## Game-side natives (vs Lua stdlib)
- `RegisterScriptNativesGameplay @ 0x61e750` registers ~150 game-native bindings via `lua_register` (StartRace, SpawnCop, AwardPlayerBounty, etc.) — see [[project_script_natives]]
- Lua's own `coroutine.*` library is registered separately via `luaopen_base` (location TBD — not yet xref'd)
- Script-visible singleton: `g_pGRaceStatus @ 0x91e000` exposed as Lua userdata with metatable

**Why:** Identifying this as vanilla Lua 5.0 means you can use lua-5.0.2 source as a Rosetta stone for any function in 0x606xxx-0x615xxx that we haven't yet named. Bytecode files (.lua/.luac) in the bundles can be disassembled with `luac -l` from a stock Lua 5.0 build.

**How to apply:**
- For unnamed VM internals: cross-ref with lua-5.0.2 `lvm.c`, `ldo.c`, `lfunc.c`, `lstate.c`
- For new opcodes/bytecode debugging: use the verified jump table at 0x60fbbc
- For coroutine bugs: lua_yield/lua_resume are the entry points; preserve CIST_YIELDED across saved PCs
- For "where is gameplay logic X?": find native by name in `RegisterScriptNativesGameplay @ 0x61e750`, follow to C++ impl
