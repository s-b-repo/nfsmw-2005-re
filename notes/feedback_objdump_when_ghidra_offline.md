---
name: use objdump when Ghidra MCP is offline
description: When Ghidra MCP server disconnects mid-session, fall back to objdump -d -M intel for direct disassembly. The PE file offsets map cleanly to VAs once you parse section table.
type: feedback
originSessionId: c4edf485-e85f-4e2f-ac31-e021ba66e8d6
---
When Ghidra MCP becomes unavailable (server crash, schema fetch error, etc.), don't abandon RE work — switch to direct disassembly:

```bash
objdump -d -M intel -j .text --start-address=0xVA --stop-address=0xVA "speed.exe"
```

PE file-offset → VA mapping is straightforward. For `speed.exe`:
- .text:  file 0x1000 → VA 0x401000 (size 0x48e2a5)
- .rdata: file 0x490000 → VA 0x890000
- .data:  file 0x4ea000 → VA 0x8ea000

Python helper to find VAs for any byte pattern:
```python
import struct
data = open("speed.exe", 'rb').read()
e_lfanew = struct.unpack_from('<I', data, 0x3c)[0]
# parse section table at e_lfanew+0x18+sizeof(opt_hdr)
```

**Why:** I lost an entire 6-agent wave because they ran during a Ghidra MCP disconnect. Then JDLZ was unsolvable from public algorithms. Disassembling speed.exe @ 0x64db40 directly via objdump cracked the algorithm in minutes — every byte verified.

**How to apply:**
- For RE: search for distinctive constants (magic numbers, struct sentinels) via `grep -aob` on the binary, map file offset to VA, disassemble around it.
- For verification: after deriving an algorithm, run it on real data and `diff` against ground truth.
- Don't wait for Ghidra to come back when there's a binary right there to read.
