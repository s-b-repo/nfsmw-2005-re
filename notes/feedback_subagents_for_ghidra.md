---
name: Ghidra MCP subagents need explicit program-switch
description: When parallelizing Ghidra investigation via Explore subagents, force them to confirm/switch to the right program first
type: feedback
originSessionId: c4edf485-e85f-4e2f-ac31-e021ba66e8d6
---
When spawning parallel subagents to investigate a multi-program Ghidra session (e.g. NFSMW has both `speed.exe` and `server.dll` open), the MCP HTTP server's "current program" defaults to whatever was last touched — and subagents inherit that state, which leads to:

- Address lookups silently returning "no function found" because the agent's addresses are in the wrong program's range
- Strings/imports lists returning the *other* program's data (e.g., `server.dll` 0x1004xxxx range when looking for `speed.exe` 0x4xxxxx symbols)
- Reports that look authoritative but are entirely cross-binary

**Why:** Hit this 2026-05-08 spawning 4 parallel Explore agents on speed.exe subsystems while Ghidra had `server.dll` as current. All agents got 0 useful results from `/decompile_function` and `/list_strings`. Discovered only after re-verifying; cost a turn.

**How to apply:** In every subagent prompt for Ghidra investigation:
1. Force them to call `GET /get_metadata` first and confirm the program name matches the target.
2. If wrong, call `POST /switch_program` with `{"program":"<target>.exe"}` (note: the endpoint returns an error message but actually does switch — verify with another `/get_metadata`).
3. Tell them to abort the investigation and report the mismatch if they cannot switch.

The same applies to one's own foreground work — always verify `/get_metadata` after a Ghidra restart or extension reload.
