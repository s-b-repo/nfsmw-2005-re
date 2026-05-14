# Anti-RE techniques, coding patterns, and notable findings in `speed.exe`

A field guide to every defensive technique, idiom, and surprising design choice we encountered while reverse-engineering NFS Most Wanted (2005). Each section names the obstacle, shows how it works in the binary, and documents the technique we used to defeat it.

NFSMW is a 2005 retail game — it was built **before** the era of heavy commercial DRM (no Denuvo, no VMProtect, no Themida, no SecuROM kernel hooks). The "protection" here is incidental: middleware obfuscation, hashed indirection, and proprietary formats — not deliberate anti-tamper. That said, the obstacles still slowed analysis significantly, and the patterns are worth documenting because they recur across EA's mid-2000s titles (Underground 2, Carbon, ProStreet).

---

## 1. Hash-keyed everything (Bob Jenkins mix3, seed 0xABCDEF00)

### The pattern
Every named entity at runtime — attributes, events, messages, resources, FNG screens, audio cues, AI goals — is keyed by a 32-bit hash, **not** by string. Strings appear in the SOURCE that wrote the data (asset pipeline, attributes.bin), but rarely in `speed.exe`. The function at 0x454640 (`Attrib::StringToKey`) does the hashing.

```c
uint32_t bChunk(const char* s) {
    // Bob Jenkins 1996 "mix3" hash, seed = 0xABCDEF00
    // (not DJB2, not FNV — common public guess is wrong)
    return jenkins_mix3(s, 0xABCDEF00);
}
```

Verified by computing `bChunk("BASE") == 0xA6B47FAC` and matching to a constant in the binary.

### Why it stops you
- You see `0xa6b47fac` in disassembly. You don't know what attribute that refers to.
- You see `0x20d60dbf` in an event-dispatch. You don't know what event that is.
- The string registry exists in the asset DB (a separate VLT/VPAK), not in `.text`.

### How we beat it
1. **Bundle string corpus** — decompressed all 4 LZC bundles (12.5MB) with our JDLZ reverse and grepped for strings. Built a 36k-word corpus.
2. **Wordlist hash-cracking** — wrote `crack_floats.py` / `crack_v5.py` / `crack_v6.py` / `crack_v7.py` (manual wordlist) and `crack_v8_community.py` (community NFS hash database, 43k names). **294 / 345 attribute hashes cracked** this way (85.2% — every name re-verified by re-hashing). The single biggest unlock was downloading `NFSTools/Attribulator` + `MWisBest/OpenNFSTools` + `yugecin/nfsu2-re` which between them ship a decade of community-RE'd attribute names.
3. **NFSPluginSDK as Rosetta stone** — berkayylmao's BSD-3 SDK ships with 178 type headers that list the canonical string→hash mappings as part of the API. Single biggest accelerator.

### Open
- **All 5 original mystery hashes now cracked.** Wave-6 solved 2 via SDK conversion + EA-vocab wordlist (AUTO_SIMPLIFY, BEHAVIORS). Wave-7 solved the remaining 3 via community wordlist match: `0xEE0011E3 = SimplePhysics`, `0x360552DA = ExplosionEffect`, `0x44F1273B = DROPOUT`. These names confirm the prior semantic-role inferences (SimplePhysics IS the Smackable solid-vs-ghost construction toggle; ExplosionEffect IS the push-back factor used by the collision-response impulse; DROPOUT IS the timed-decay parameter pair used by the despawn animator).

---

## 2. JDLZ compression (proprietary, version 0x02)

### The pattern
All LZC bundles (`GLOBAL.LZC`, `INGAMEA.LZC`, etc.) are compressed with **JDLZ** ("Joe Davenport LZ"), EA's in-house LZ77 variant. NFSMW uses **JDLZ v0x02**, which is *not* the variant publicly documented for NFS Carbon (v0x01 has different flag semantics).

```
JDLZ header:
  +0 magic    "JDLZ" (4 bytes)
  +4 version  0x02
  +5..7       reserved/zero
  +8 decomp_size  (u32 LE)
  +12 comp_size   (u32 LE)
  +16 flag1 first byte
  +17 flag2 first byte
  +18 data starts here
```

Two parallel flag-bytes drive the decode. Two "forms" of back-reference (small-offset/long-length vs. larger-offset/short-length). Public Carbon-era references give a different semantic for v0x02 (literal vs back-ref bit is inverted).

### Why it stops you
You can identify "JDLZ" magic but can't decompress without the algorithm. No public format spec for v0x02.

### How we beat it
1. `objdump -d` the decompressor at `speed.exe!0x64db40` (we found it by xref'ing the "JDLZ" magic check).
2. Hand-translated the assembly to Python over ~3 hours, fixing two off-by-one bugs (flag2 was double-shifted) and one semantic inversion (flag1 LSB 0=literal, not 1).
3. Validated byte-perfect on all 4 LZC bundles → emits `/tools/nfsmw_bun_reader/jdlz_nfsmw.py`.

The same algorithm should work on NFS Carbon/ProStreet LZCs but is untested.

---

## 3. VPAK / attributes.bin — schemaless typed binary

### The pattern
`attributes.bin` (inside GlobalB.bun) is a typed-row database that drives every gameplay knob: vehicle handling, AI difficulty, race rules, customization parts, audio mixes. Format:

```
Row layout (16 bytes from file offset 0x18000):
  +0 class_hash   (u32 — what struct this row instantiates)
  +4 type_hash    (u32 — what TYPE this attribute is — 9 distinct hashes)
  +8 key_hash     (u32 — attribute name hash, e.g. bChunk("MASS"))
  +0xC payload    (4 bytes — either inline value or pointer to extended payload)
```

The **type hash** field is also hashed, not stringed. So you see `0x1234abcd` in the row and don't immediately know if it's a Float, UInt32, RefSpec, or what.

### Why it stops you
No header tells you which attribute is which type. You have to:
- Identify rows by class+key hash
- Figure out the type by inference from use-sites in code
- Then go crack the key hashes back to readable names

### How we beat it
1. We cracked 7 of the 9 type hashes by observing how they're consumed (e.g., type hash `0xC83BC4E5` always feeds into a function that loads 4 bytes as a float → **Float**).
2. Documented full type registry in `docs/attribute_hashes.md`:
   - `0xC83BC4E5` = Float
   - `0x05925565` = Text
   - `0xAD1E0F25` = UInt32
   - `0xB46FAB55` = Bool
   - `0x77BBC9F7` = StringKey
   - `0xC74D7B5D` = RefSpec
   - `0x4D924B5F` = eDRIVE_BY_TYPE enum
   - (2 remaining unidentified)
3. Cracked 294 of 345 attribute names = **85.2%** via wordlist + compound generation + community NFS hash database (`NFSTools/Attribulator` ships 43k names from a decade of community modding). Every name re-verified by re-hashing. 51 remaining — likely need EA source leak.

---

## 4. EAGL middleware — proprietary, no public source

### The pattern
NFSMW is built on EA's internal "EAGL" / "EAGL4" / "EAGL4Anim" engine. None of these have public source releases or public headers (until NFSPluginSDK, which is community-RE'd).

The engine sits between game code and the OS:

```
Game code
   ↓
EAGL4Anim (skeletal animation, TickableBus, MemoryFieldWrapper-style globals)
EAGL physics (worker-thread integrator behind a runtime-bound vtable slot at 0x47c890)
FERender (D3D9 abstraction)
   ↓
DirectX 9, DirectInput8, DirectSound
```

### Why it stops you
- Engine functions are unnamed and follow no documented API. They look like `FUN_006f6cf0` and call into other engine functions via vtables.
- "Standard" things (event bus, pool allocator, scene graph traversal) have a single proprietary implementation per engine, not the libstdc++ patterns you'd expect.
- Cross-class casts via custom interface query (every base class implements `GetIHandle()` returning an `IHandle*` registry token — verified at 0x402820–0x405240, 20+ thunks).

### How we beat it
1. **String-anchor reconnaissance**: every engine subsystem has at least one diagnostic/assert string. e.g., "TickableBus_DispatchActiveSubscribers" wasn't named — but the string "Tickable" appears in 3 places near functions that match the dispatcher pattern.
2. **NFSPluginSDK headers**: berkayylmao's community SDK names the major engine classes (PVehicle, RBVehicle, GRaceStatus, AICopManager, FECustomizationRecord, etc.) with hardcoded addresses. ~150 functions named that way alone.
3. **Vtable archaeology**: the inline RTTI list at `0x008add1c` enumerates every pvehicle subclass + component-key, giving us a class hierarchy without symbols.
4. **Pattern matching against open-source EA**: when we found Lua, we immediately matched its error strings to Lua 5.0.2 source and inherited 30+ free names.

---

## 5. Lua 5.0 with reversed instruction encoding

### The pattern
The script VM at 0x60e9d0 is **literal vanilla Lua 5.0.2** — confirmed by byte-identical error strings (`"binary string"`, `` "`for' initial value must be a number" ``, "attempt to yield across metamethod/C-call boundary"). 150 game-natives are registered via `lua_register` at 0x61e750.

One twist: this build of Lua has the **A/B/C bit positions flipped vs canonical** Lua 5.0.2.
- Canonical: `OP[0:6] | A[6:14] | C[14:23] | B[23:32]`
- NFSMW: `OP[0:6] | C[6:15] | B[15:24] | A[24:32]`

Opcodes (35 total) and RK threshold (250) are identical.

### Why it stops you
Initial assumption (mine, in earlier sessions): this is a "Lua-like custom stack machine". We documented an 8-byte typed slot model with 8 type tags, ~150 natives, cooperative Run/Suspend scheduling — all correct, but framed as if it were a bespoke language. We invented names like `InvokeScriptFunctionByHash`, `RegisterNativeNoArg_Handler` etc. when Lua's stdlib already has names for these.

### How we beat it
1. Subagent in wave-5 spotted the error string `"binary string"` (Lua 5.0's `lundump.c` magic-mismatch message).
2. Cross-referenced against lua-5.0.2 source code.
3. Mapped all 35 opcodes by following the jump table at 0x60fbbc.
4. Identified the bit-shift twist by comparing decode behavior — the build flips POS_A from 6 to 24 (likely a build-time `#define POS_A 24` tweak in `lopcodes.h`).

### Practical implication
- The Lua 5.0.2 source is now a Rosetta stone for any function in 0x606xxx–0x615xxx range we haven't named.
- Bytecode `.lua`/`.luac` files in bundles can be disassembled with stock `luac -l` from a Lua 5.0 build (matching the bit-shift quirk requires a custom build).
- "Run" and "Suspend" gameplay natives at 0x6048d0/0x6048e0 are **NOT** Lua coroutines — they manipulate gameplay "Activity" objects. Real coroutines are `lua_yield @ 0x6138b0` and `lua_resume @ 0x6150e0`, accessible via `coroutine.*` from script.

---

## 6. Static linkage of multimedia codecs (no DLL dependency)

### The pattern
You'd expect:
- Video: `binkw32.dll` import (RAD Game Tools' Bink — standard for the era)
- Audio: `mss32.dll` import (RAD's Miles Sound System)
- Music: an MP3 decoder DLL

What you find:
- **No** `binkw32.dll`, **no** `mss32.dll` imports
- Video: On2 **VP6** + MAD audio, **statically linked** into speed.exe. Internal strings: `VP6_CODEC_INTERNAL::GetFrameFromList` at 0x8c27e8, `MAD_CODEC_INTERNAL::CreateIorP` at 0x8c2828
- Container: EA proprietary **SCHl/MVhd** chunks with codec FOURCC `06PV` and MAD audio chunks `SCHl/GSTR`, keyframe magic `MV0K` (0x4d56304b)
- On-disk extension: `.vp6` (e.g. `attract_movie_english_ntsc.vp6`)
- Music streaming: proprietary **EAXS_StreamManager** wrapping a hardware-accelerated stem player; license tracks come through this, not from `MP3` files

### Why it stops you
- Process Monitor doesn't show `binkw32.dll` being loaded → you wrongly conclude there's no video player
- IDA/Ghidra import tables don't list a codec library → no obvious entry point
- The codec magic strings are buried inside `.text` (compiled into the binary) rather than at format-detect sites

### How we beat it
1. Searched strings for "VP6" — hit `VP6_CODEC_INTERNAL::*` family
2. Searched for MV0K hex constant `0x4d56304b` — found decode loop
3. Cross-referenced with the chunk-reader (`ProcessReadChunkAndCreateCodec @ 0x7f7c7e`) to confirm format
4. Identified the EA SCHl container by hex-dumping a `.vp6` file (`MVhd` header, `SCHl` audio chunks)

---

## 7. Event-bus dispatch by hash (no direct callbacks)

### The pattern
Game systems communicate through a **broadcast event bus** keyed by Jenkins-hashed message names. Examples:
- `MNotifyMilestoneProgress` → hash 0x... → broadcast to N listeners
- `MNotifyPlayerRep` → hash → broadcast
- `MPlayerEnterPursuit`, `MPursuitOver` → hashes
- `PursuitBountyAwarded` → hash `0x20d60dbf` → 65 registered listeners (**all 65 are AUDIO callbacks** via NFSMixMaster command queue DAT_0091e0d0; correction from earlier "HUD updaters" theory caught in wave-8)

Listener registration uses `RegisterPursuitBountyEventListeners @ 0x648590`-style functions that push (hash, callback) pairs into a registry. Dispatch walks the registry.

### Why it stops you
- A function calls "BroadcastEvent(0x20d60dbf, data)" and you don't immediately know who's listening.
- Listeners are scattered across UI, AI, audio, save subsystems — finding them all means brute-forcing the listener registry.
- Event hash literals look like random constants.

### How we beat it
1. Annotated every recognized hash literal in disassembly with a plate comment (122 such comments applied).
2. Mapped listener-registry function (e.g. `RegisterPursuitBountyEventListeners`) and dumped the (hash, callback) pairs.
3. Cross-referenced hash values against a curated list of message-name strings from the bundle string corpus.

---

## 8. Save-file MD5 trailer (light tamper detection)

### The pattern
Profile saves at `%USERPROFILE%\Documents\NFS Most Wanted\<PlayerName>` end with a **16-byte MD5 digest** of the preceding payload. Confirmed by:
- MD5 IV constants `A=0x67452301, B=0xefcdab89, C=0x98badcfe, D=0x10325476` at `ComputeMd5OfSaveBuffer @ 0x57f920`
- Canonical RFC-1321 T-table `0xd76aa478, 0xe8c7b756, 0x242070db, 0xc1bdceee, ...` at `Md5CompressBlock @ 0x650410`
- Standard RFC pad-and-finalize in `Md5PadAndFinalize @ 0x650cb0`

### Why it (kind of) stops you
A modified save file's MD5 won't match, so the game rejects it on load. This makes "save-game cheats" require recomputing the digest after edits.

### How we beat it
1. Confirmed MD5 (not CRC, not custom hash) by IV match
2. Wrote a save-editor that recomputes the trailer after edits
3. No keying — MD5 with no salt, so trivial to recompute. This is *integrity* (anti-corruption), not *authentication* (anti-tamper). Pure integrity check.

### Prior false claim
The string `MSG_R_BI_DATACRC` at 0x8b6b7c had us assume "BI = Binary Integrity = save CRC". **Wrong** — it's an orphan netcode message-name string sitting next to `MSG_R_SC_RESTARTLOAD`. Zero code xrefs. The actual save integrity is MD5 elsewhere.

---

## 9. Worker-thread physics behind a runtime-bound vtable

### The pattern
The main-thread "physics tick" call you'd expect to see — `Physics_Integrate(dt)` — doesn't exist as a single statically-resolvable function. Instead:

```
PerPlayerSubsystemTick @ 0x47c880
  → indirect call at 0x47c8af via vtable slot bound at runtime
  → DAT_009885c8[+0x44]() — the integrator entry, but the function pointer
    is written by the physics worker thread during world setup
```

The physics integrator runs in a **separate worker thread**. The main thread only fills an input buffer and reads back a result buffer. The two are synchronized via a sub-physics object (vtable `0x8ab6a0`).

### Why it stops you
Static analysis can't reach the integrator from the main-thread call graph because the binding happens at runtime. You think "where does this dt go?" and the call chain dead-ends at a vtable slot containing `NULL`.

### How we beat it
1. Live-debugger session: attached, set a breakpoint at `PerPlayerSubsystemTick`, captured the runtime vtable, walked from there
2. Documented the static endpoint (`0x47c890`) as a runtime-bound slot — anyone doing static analysis must look at the worker-thread setup code to find the actual integrator
3. The agent name `vtbl_pvehicle_SubPhysicsObject @ 0x8ab6a0` is the shared sub-object that bridges main and worker

---

## 10. Hardcoded address tables (cutscene paths, audio routes, FNG handlers)

### The pattern
Many "registries" are not data-driven — they're hardcoded address tables in `.data` that pair a name with a callback:

| Table | Address | Entries | Stride | Purpose |
|---|---|---|---|---|
| Cutscene path → flags | `0x008f3818` | 38 | 8 | (`const char* path`, `uint flags`) |
| FE audio routing by screen-hash | `0x008f4320` | varies | 8 | (`hash`, `setup_fn`) |
| HUD widget name table | `0x008a27cc..0x008a2994` | 28 | 4 | (`const char* widget_name`) |
| AI goal factory registry | `0x0090d8e8` | ~30 | varies | (`hash`, `vtable`) |
| Career data section keys | `0x89da2c, 0x89ceb8, 0x89ced0` | 3 strings | n/a | `CAREER_DATA`, `CAREER_COMPLETED_DATA`, `GAME_COMPLETED_DATA` |
| Audio entity vtables | `0x911fa8` (NFSMixMaster) + 4 typed pools | 4 | n/a | (`vtable`) |

These tables are walked by registry-lookup functions. Adding new entries means patching `.data` directly (modders typically use static-address overrides via DLL injection rather than table edits).

### Why it stops you
The "easy" way to find content is "search for the string in the binary". If the registry uses pre-computed hashes (see §1) or lives in a parallel asset DB, you don't find the string in `.text` at all.

### How we beat it
1. Identified registry-lookup functions by their pattern (a loop comparing hash/pointer fields with stride-N over a fixed address range)
2. Dumped each table's contents via `read_memory_block` and decoded the entry shape
3. Cross-referenced entries against the bundle string corpus to identify what each registry holds

---

## 11. Online verification = dead service (GameSpy SDK)

### The pattern
NFSMW's online multiplayer relies on **GameSpy**, EA's outsourced matchmaker. Strings: `gamespy.com`, `gpcm.gamespy.com`, `peerchat.gamespy.com`, `nfsmwpc.master.gamespy.com`.

GameSpy shut down 2014-05-31. All NFSMW online services are dead.

### Why this matters for RE
- Tons of `.text` is multiplayer / GameSpy SDK code (`Net_*` functions) that is **effectively dead code** in any 2024+ analysis session
- Bypassing the dead online check / spoofing the server is a community-modding goal in itself
- The session loop `Net_MultiplayerSessionUpdateLoop @ 0x761b30` branches on `g_nIsNetClient @ 0x9b416c` and is reachable only via the now-unreachable GameSpy handshake

### How we beat it
1. Documented all GameSpy-touching code as "online subsystem (DEAD)" and de-prioritized for now
2. Single-player modding doesn't need any of it
3. To revive multiplayer: redirect GameSpy hostnames via hosts file or proxy DLL, host a private GameSpy reimplementation (community has done this for other EA games via OpenSpy)

---

## 12. Static-data feature gates via multiplex.cfg

### The pattern
A subset of features are toggled by a runtime config file `multiplex.cfg`:

| Key | Effect | Code path |
|---|---|---|
| `SKIPMOVIES=1` | All cutscenes skip immediately | `g_dwSkipMoviesFlag @ 0x926144` |
| (others) | TBD | `Net_ParseMultiplexerConfigFile @ 0x78a9c7` parses |

The parser at 0x78a9c7 reads the file at startup and writes to globals. No on-disk encryption; trivial to flip values.

### Why interesting
- This was clearly a dev-time iteration accelerator (skip movies → faster boot during testing) that shipped in retail
- Anyone with file-system access can enable dev features. **Pure security through obscurity** — nothing checks that the config wasn't edited.

---

## 13. Debug strings preserved in retail

The retail binary still contains:

- Function names in some assert/log paths (e.g., "TickableBus_DispatchActiveSubscribers", "Particle_And_Emitter_Pools_Initialize")
- Lua error strings byte-identical to Lua 5.0.2 source
- Pool names: "Anim_CNFSAnimBank_SlotPool", "WorldAnimEntityTree_SlotPool", "EAGL4Anim Memory Pool"
- Hash-name strings in tables that confirm cracked hashes
- Cutscene path strings (literal, unhashed): "MOVIES\\blacklist_01" etc.
- FNG screen names: "InGameRace.fng", "HUD_SingleRace.fng", etc.

This is a goldmine: every retained string is a free identification of the surrounding code. EA didn't strip the binary aggressively — likely because release builds for the era prioritized debuggability over RE resistance.

---

## 14. Surprising findings (myths debunked, design choices)

### "AI cars draft (slipstream) you"
**Wrong.** There is no drafting code in NFSMW. What players experience as "slipstream" is the **rubber-band catchup multiplier** (`ComputeRacerRubberBandTargetSpeed @ 0x5ff990`). The AI's speed target is `base * difficulty_mult * rubber_band_gain` — and gain rises as you pull ahead. No proximity check, no airflow simulation.

### "AI uses nitrous strategically"
**Wrong.** The `EPlayerTriggeredNOS` event has **zero xrefs** from AI code. AI cars get speed via the rubber-band system, not via N2O consumption. The "AI overtook me using nitrous" perception is rubber-band + scripted catchup, not actual N2O.

### "MW has Drift mode (locked / unused)"
**Wrong.** The string `drift` at `0x89abcc` is leftover localization (from Underground 2 codebase). The race-mode enum has 11 values: p2p / circuit / drag / knockout / tollbooth / speedtrap / checkpointrace / cashgrab / challenge / speedtrapjump / milestonejump. **Drift is not in the enum.** The mechanic was deliberately cut for MW's "police chase" focus.

### "MSG_R_BI_DATACRC = save-file CRC"
**Wrong.** It's an orphan netcode message-name string. Save files use MD5. See §8.

### "ProcessUIOrHUDElements is the HUD update"
**Wrong.** That function at `0x504d00` only runs animation interpolation, camera update, and a flag toggle. Wave-8 mapped the *actual* HUD update path: 13 of 28 widgets have per-widget Update functions (Speedometer @ 0x57a540, Tachometer @ 0x57a6e0, Minimap @ 0x59db50, HeatMeter @ 0x7a5aa0, PursuitBoard @ 0x52e0c0, etc.). HUD is **tick-driven, NOT event-bus-driven** (another correction: the prior "UI event bus" theory was wrong; widgets poll DAT_00925ae8 frame-counter each tick). The parent walker (FuncInfo @ 0x008d5a00 invoker) is still unmapped — every widget-name string is only referenced from destructor funclets.

### "LookupUIInputBindingByCode at 0x56ecc0"
**Wrong.** That function is actually `FEPlayerCarDB_GetCarRecordByHandle` — a 200-slot × 0x14-byte car-record pool lookup, not input bindings. SDK rename caught this.

### Bink video?
**Wrong.** VP6+MAD (see §6).

### Custom Lua-like VM?
**Wrong.** Vanilla Lua 5.0 with one instruction-encoding tweak (see §5).

### "BChunk is DJB2"
**Wrong.** Bob Jenkins mix3, seed 0xABCDEF00 (see §1). Public web sources for NFSMW frequently get this wrong.

---

## 15. Techniques that worked best for us

Ranked by leverage:

1. **NFSPluginSDK by berkayylmao**: pulled 150 function addresses + 178 type headers + 65 enums + 245 structs in one BSD-3 download. 5–10× speedup over manual RE.
2. **Parallel subagents (8x concurrency)**: 8 simultaneous Claude agents, each owning one subsystem, communicating only through shared Ghidra state. Wave-5 mapped 8 major subsystems in ~25 minutes wall-clock.
3. **Direct HTTP to Ghidra plugin (port 8089)**: when the Ghidra MCP bridge broke (schema bug), bypassing it with curl + JSON kept us productive. Wrapper at `/tmp/ghidra_post.sh`.
4. **Pattern matching against open-source**: Lua 5.0 error strings, MD5 IV constants, JDLZ algorithm shape, Jenkins mix3 — every "open-source likely match" pays off massively.
5. **Bundle decompression early**: getting the strings out of LZC bundles unlocked the hash-cracking pipeline. Without bundles → no string corpus → no hash cracks.
6. **objdump fallback when Ghidra unavailable**: for JDLZ decompressor RE specifically, raw `objdump -d` was faster than Ghidra decompilation because the loop is small.
7. **Live debugger for runtime-bound vtables**: static analysis cannot reach worker-thread-installed vtable slots (§9). Live debugger captures them in seconds.
8. **Subagent self-checking via advisor()**: caught at least 2 misreads (vtable slot mix-ups) before they were committed to memory.

## 16. Techniques that wasted our time

- **Brute-forcing all 4-char ASCII as bChunk hash candidates** (too sparse, never matched anything we didn't already know)
- **Trying to identify the integrator without a debugger** (runtime-bound — see §9 — gave up after ~3 hours)
- **Assuming the "MSG_R_BI_DATACRC" string was a function name** — it's just a data string with no xrefs
- **Manually applying SDK names one-by-one before scripting** — first 20 renames took 2 hours; scripted bulk-rename took 5 minutes for the remaining 100+
- **Trusting one agent's claim about `ProcessUIOrHUDElements`** without verification — it took 4 days for another agent to catch the misread

---

## 17. Open / unfinished

- 5 mystery attribute hashes (§1, §3) — likely need PDB or source leak
- 51 of 345 attribute names still uncracked (14.8%) — these don't appear in any public NFS modding hashlist
- ~75% of functions still `FUN_*` (24.7% named is the current floor)
- Real input-binding lookup function not located (§14 false claim noted)
- HUD per-widget update functions not located (needs runtime breakpoint on widget-name string)
- Bytecode disassembly for shipped `.luac` files not yet attempted
- Worker-thread physics integrator: entry point known but per-frame substeps not yet traced from worker side

---

## 18. Closing observations

NFSMW is **not protected** in any modern sense. The obstacles are middleware obfuscation and proprietary formats, not deliberate anti-RE. A motivated single reverser with 1–2 years could push function-name coverage to 60–70% without source. With the NFSPluginSDK + community knowledge contributing, that timeline shortens significantly.

The single most important takeaway: **find the open-source signal in the binary first**. NFSMW contains Lua 5.0, MD5, JDLZ (now public-via-us), Bob Jenkins mix3, On2 VP6, MAD audio — each one a free pile of identifications once recognized. The proprietary EA-only code is a smaller core than it looks at first glance.
