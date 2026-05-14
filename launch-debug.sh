#!/usr/bin/env bash
# launch-debug.sh — start NFSMW under Wine + winedbg's gdbserver mode
#
# After this runs:
#   - speed.exe is running under Wine
#   - winedbg exposes a GDB remote-protocol server on TCP localhost:38002
#   - Ghidra's debugger can connect via "Remote gdb" launcher
#
# Press Ctrl+C in this terminal to kill the game + winedbg.

set -e

GAME_DIR="/home/cortix/Downloads/9_Need for Speed Most Wanted Magipack/extracted/app"
EXE="speed.exe"
PORT=38002

echo "[*] Game dir: $GAME_DIR"
echo "[*] Will listen for Ghidra's GDB connection on tcp:$PORT"
echo "[*] Ctrl+C to terminate."
echo

cd "$GAME_DIR"

# winedbg --gdb mode listens on a port and translates the GDB remote protocol
# into Wine's debugger. Ghidra's "Remote gdb" launcher targets this.
exec env WINEPREFIX="${WINEPREFIX:-$HOME/.wine}" \
     winedbg --gdb --no-start --port $PORT "$EXE"
