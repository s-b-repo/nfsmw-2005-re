#!/usr/bin/env bash
# launch-then-attach.sh — alternative flow:
#   1. Launches speed.exe under Wine in the background
#   2. Waits 3 seconds for the process to spin up
#   3. Prints the PID for you to plug into Ghidra
#
# Use this if the gdbserver path (launch-debug.sh) doesn't connect cleanly.
# After this runs and prints the PID, in Ghidra:
#     Debugger -> Connect... -> "gdb local"
#     Attach by PID: <printed value>

set -e

GAME_DIR="/home/cortix/Downloads/9_Need for Speed Most Wanted Magipack/extracted/app"
EXE="speed.exe"

cd "$GAME_DIR"

echo "[*] Launching $EXE under Wine in the background..."
WINEPREFIX="${WINEPREFIX:-$HOME/.wine}" wine "$EXE" >/tmp/nfsmw_wine.log 2>&1 &
WINE_PID=$!
echo "[*] Wine launcher PID: $WINE_PID"

# Wine forks several processes; the actual speed.exe child is what we want
sleep 3

PID=$(pgrep -f speed.exe | head -1)
if [ -z "$PID" ]; then
    echo "[!] speed.exe not visible after 3s — game may have crashed. Check /tmp/nfsmw_wine.log"
    tail -20 /tmp/nfsmw_wine.log
    exit 1
fi

echo
echo "============================================"
echo "  speed.exe PID: $PID"
echo "  Attach via:  gdb -p $PID"
echo "  Or in Ghidra: Debugger -> Connect... -> gdb local -> Attach by PID -> $PID"
echo "============================================"
echo
echo "Logs streaming to /tmp/nfsmw_wine.log"
echo "Ctrl+C to stop watching (game keeps running)."
tail -f /tmp/nfsmw_wine.log
