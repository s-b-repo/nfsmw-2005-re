# Live Debugger Plan — capture integrator + Present targets

Two outstanding runtime-binding walls in static analysis. A 5-minute debugger session resolves both.

## Pre-flight — already done for you

- ✅ Ghidra running speed.exe @ v5.7.1 (177 tools, debugger endpoints exposed)
- ✅ Wine 11.7 + winedbg installed
- ✅ GDB 17.1 installed (`pacman -S gdb` ran this turn)
- ✅ Wine prefix at `~/.wine` with D3D9 + D3DX9_24..43 DLLs present
- ✅ Two launcher scripts in the project root:
  - `launch-debug.sh` — winedbg gdbserver mode (Ghidra connects via Remote gdb)
  - `launch-then-attach.sh` — plain Wine launch, then attach by PID (fallback if gdbserver path fails)

## Step-by-step (do these in order)

### 1. Open Ghidra's Debugger tool

In your existing CodeBrowser window with `speed.exe` open:

> **`Window` → `Debugger`**

A second tool window appears with sub-panes for Targets, Threads, Stack, Registers, Memory, Listing.

### 2. Pick ONE of the two launcher paths

#### Path A (preferred) — gdbserver via winedbg

In a terminal:
```bash
"/home/cortix/Downloads/9_Need for Speed Most Wanted Magipack/launch-debug.sh"
```
This blocks. winedbg loads `speed.exe` and sits paused at the entry point listening on `tcp:38002`.

In Ghidra Debugger:
- `Debugger` → `Connect...` → pick **`gdb local · Remote gdb · IN-VM`** (or any "Remote gdb" entry)
- In the dialog: target = `localhost:38002`, architecture = `i386`, OS = `windows`
- Click **Connect**. Targets pane shows `speed.exe` paused at entry.

#### Path B (fallback) — Wine launch + PID attach

In a terminal:
```bash
"/home/cortix/Downloads/9_Need for Speed Most Wanted Magipack/launch-then-attach.sh"
```
Game launches normally. Script prints the PID, e.g. `speed.exe PID: 12345`.

In Ghidra Debugger:
- `Debugger` → `Connect...` → pick **`gdb local · IN-VM`**
- After GDB starts: `Targets` pane → **Attach** → enter PID `12345`

### 3. Confirm via MCP

Once attached, run this from any terminal to verify:
```bash
curl -sS http://127.0.0.1:8089/debugger/status
```
Expected: `{"state":"<stopped|running>","target":"speed.exe", ...}` instead of the "Debugger not active" error.

### 4. Tell me "debugger attached"

That's your only step from then on. I'll execute the capture script below autonomously.

---

## What I'll do once you confirm attached

Run autonomously via MCP:

```bash
TCP=http://127.0.0.1:8089

# 1) Verify state
curl -sS $TCP/debugger/status

# 2) Set integrator probe — break-on-execute at the indirect-call site
curl -sS $TCP/debugger/set_breakpoint -X POST -H 'Content-Type: application/json' \
  -d '{"address":"0x0047c890","type":"execute","name":"integrator_probe"}'

# 3) Set Present probe — break on access of g_pIDirect3DDevice9
curl -sS $TCP/debugger/set_breakpoint -X POST -H 'Content-Type: application/json' \
  -d '{"address":"0x00982bdc","type":"read","name":"d3d9device_read"}'

# 4) Resume execution — let the game run; reach the gameplay screen
curl -sS $TCP/debugger/resume -X POST

# 5) When the integrator BP fires, capture:
#    - registers (the dispatch target is in [eax] or [ecx+0])
#    - stack (which player slot is being ticked)
#    - read 128 bytes at the resolved vtable to identify the concrete class
curl -sS $TCP/debugger/registers
curl -sS $TCP/debugger/stack_trace
curl -sS "$TCP/debugger/read_memory?address=<resolved_eax>&len=128"

# 6) Translate runtime → static address
curl -sS "$TCP/debugger/dynamic_to_static?address=<runtime_addr>"

# 7) Write the result back as a label / function rename
curl -sS $TCP/create_label -X POST -d '{"address":"0xNNNNN","name":"PerVehicle_Step_Concrete"}'
curl -sS $TCP/rename_function -X POST -d '{"oldName":"FUN_xxxxx","newName":"PerFrame_PresentWrapper"}'

# 8) Final save
curl -sS $TCP/save_program -X POST
```

## Expected outcomes

- **Per-vehicle integrator** — the address that gets called via `slot[-1].vt[2](dt)` inside `PerPlayerSubsystemTick`. Identifies the concrete class (likely a vtable in the `0x0089xxxx` range pointing into `pvehicle` or a derived `RBVehicle/RBCop/RBTrailer` Step method).
- **Per-frame Present wrapper** — the function (or instruction) that loads `g_pIDirect3DDevice9` and dispatches `vt[0x44]`. Lets us name the render-submit tail and finally close out the per-frame Present site.

## Notes / troubleshooting

- **Game won't reach gameplay** — even if it stays on the loading screen, the Present BP will fire (Present is called every frame including during loading screens). The integrator BP requires being in-race; if the game only reaches the menu, set a savestate with a partial menu-mode integrator probe instead.
- **Wine launch fails** — check `/tmp/nfsmw_wine.log` for D3D9 / OpenAL errors. Common fixes: `winetricks d3dx9 dotnet35` or use the bundled `~DSOAL/` DSound→OpenAL wrapper.
- **GDB attach fails** — Ghidra's Remote gdb expects `multiprocess on` and `extended-remote` mode. winedbg's `--gdb --port` exposes both. If the connection drops, check that port 38002 is free (`ss -tln | grep 38002`).

## Time budget

- Steps 1–3: 30 seconds.
- Game launch + reach a frame: 30 seconds to 2 minutes (depends on load).
- Capture + label + save: ~2 minutes after attach.

Total: under 5 minutes once the game window is up.
