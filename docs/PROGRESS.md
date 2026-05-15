# Reverse Engineering Progress Log

Tracks the cumulative progress of speed.exe reverse engineering. Each session/wave is logged with concrete deliverables.

## Headline metric

| Date | Named functions | % of 26,316 | Memory entries | Notes |
|---|---:|---:|---:|---|
| 2026-05-09 baseline | 6,338 | 24.1% | 22 | Wave-1 (10 subsystems mapped) |
| 2026-05-12 mid | ~6,400 | 24.3% | 27 | Wave-3/4 (script-VM, cop-AI, EAGL physics, render passes, animation, career) |
| 2026-05-14 end of wave-5 | **6,511** | **24.7%** | **40** | NFSPluginSDK integrated, 8 parallel agents complete |
| 2026-05-14 end of wave-6 | 6,513 | 24.7% | 40 | attribute crack push (35.1%); 2 of 5 mystery hashes solved |
| 2026-05-14 end of wave-7 | 6,513 | 24.7% | 40 | community wordlist integration: 35% → 85% attribute cracks; all 5 mystery hashes solved |
| 2026-05-14 end of wave-8 | 6,550 | 24.89% | 40 | input-binding system + HUD widget updates fully mapped; 2 prior claims corrected |
| 2026-05-14 end of wave-9 | 6,597 | 25.07% | 40 | trainer DLL built; EAGL physics corrected (no worker thread); event-bus API mapped; 14 HUD ctors named; semantic roles for 15 hashes; 88.6% true attribute crack rate |
| 2026-05-15 end of wave-10 | 6,597 | 25.07% | 43 | 3 new memory entries: game_state_machine, ai_helicopter, vehicle_cameras. 7 of 10 agents tool-denied; 3 returned partial SDK findings. Trainer published to GitHub. |
| 2026-05-15 end of wave-11 | 6,632 | 25.20% | 47 | Wave-9 punch-list closed: FE nav (224 .fng), PursuitBreaker env (3 hashes), user-key SpeedBreaker chain, HUD update verification (14 widgets, 10 corrected). |
| 2026-05-15 end of wave-12 | 6,632 | 25.20% | 48 | Deep-mapped all 10 corrected widgets. BustedMeter Update is no-op. TimeExtension is TOLLBOOTH-only. 10 agents launched, all tool-denied. |
| 2026-05-15 end of wave-13 | 6,643 | 25.24% | 49 | **HUD per-frame walker DISCOVERED**: CHudWidgetArray_Tick @ 0x58ca30 (vt[1] of CHudWidgetArray vtable at 0x8a2538). |
| 2026-05-15 end of wave-14 | **6,643** | **25.24%** | **50** | **24-widget slot map complete**: every widget cross-referenced from master init against the walker. Only 10/24 are walker-ticked; 14 are FNG-bus or passive. |

Note: the 24% baseline reflects Ghidra's automatic FLIRT signature recognition (CRT, STL, common libs) — manual session renames are a small fraction. The meaningful metric is **breadth of subsystems mapped**, not raw count.

## Subsystem coverage (by wave)

### Early sessions
- bChunk = Jenkins mix3 hash identification
- JDLZ v0x02 decompressor (RE'd from speed.exe @ 0x64db40)
- attributes.bin schema decode (16-byte rows from 0x18000)
- D3D9 boot path (RenderAndWindow_Initialize → CreateDevice → FirstPresent)
- DirectInput8 boot
- pvehicle subclass RTTI inventory
- Per-frame call chain (GameFrameTick → ActiveComponents_TickAll → vehicle physics)
- 6 live debugger captures of vehicle physics dispatch

### Wave-1 (10 parallel agents)
- Allocator architecture (16-arena heap → CreateObjectPool → 50+ slot pools)
- World streamer (region grid + AI path graph)
- Particle system (3 pools)
- Audio subsystem (4 entity classes)
- Customization (vinyls, parts)
- FNG front-end UI
- Network/multiplayer (GameSpy + LAN)
- Damage subsystem
- Input action layer
- Replay/Joylog

### Wave-3 (post-MCP-bridge-fix)
- Lua-like script VM (initial mapping — later confirmed Lua 5.0 in wave-5)
- Cop AI + pursuit (goal-stack model; SetAICopPursuitGoal @ 0x42ab80)
- EAGL physics (worker-thread integrator behind runtime-bound vtable)

### Wave-4
- Render pass pipeline (Clear → ShadowMap → World → HUD → PostProcess → Present)
- Animation runtime (EAGL4Anim + TickableBus)
- Career + milestones (event-broadcast model)

### Wave-10 (2026-05-15, parallel RE + GitHub push)
- **GitHub repo published**: https://github.com/s-b-repo/nfsmw-2005-re (261 files, 2.8 MB, BSD-3)
- **Linux CLI tool** built: `tools/nfsmw-tool/` (Python; hash, lookup, jdlz, attrs, verify-save, sdk, stats subcommands). Self-test passes; `bChunk("BASE") = 0xA6B47FAC` and `bChunk("MASS") = 0x4A56503D` validated mathematically.
- **Top-level README + LICENSE + .gitignore** added — repo is community-ready
- **Game state machine** reverse-engineered: `ProcessGameStateMachine @ 0x6596a0` is a **function-pointer trampoline** (not enum-based). State record at `DAT_00925e70` is 4-slot {fn_ptr, arg, ctx, post_cb}. Transitions happen by state-fn writing a new fn pointer.
- **AI helicopter** mapped from SDK Extensions.h fingerprints: `vtbl_AIVehicleHelicopter @ 0x008920D8` (MI: AIVehiclePursuit @ 0x891EC0 + IAIHelicopter @ 0x404060). Member layout from SDK header. Despawn paths: fuel exhaustion, damage, pursuit-end, off-nav-net.
- **Vehicle cameras**: 15 × 0x1c camera array at `DAT_009196b4`, iterated by `UpdateWorldCamerasAndViewport @ 0x72aa70`. ePlayerSettingsCameras enum has 7 modes (Bumper/Hood/Close/Far/SuperFar/Drift/Pursuit). Per-camera dt = 1/30 sec.
- **Agent constraint discovery**: subagents now run in a more restrictive sandbox than the main session — they cannot reach `Bash`/MCP/curl. Direct-work in the main session is the reliable path going forward. 7 of 10 wave-10 agents reported tool denials; 3 returned partial SDK-based findings.

### Wave-13/14 (2026-05-15, HUD walker + slot map)

The wave-9 open question — "where is the per-frame HUD walker?" — finally solved:

- **`CHudWidgetArray_Tick @ 0x58ca30`** is the walker (vt[1] of CHudWidgetArray's vtable at `0x008a2538`).
- The walker is **inline, not a loop**: 11 hardcoded slot reads at fixed offsets (`+0x2dc`, `+0x2e0`, ..., `+0x32c`).
- Each slot's widget object has a 4-dword **mode-filter mask** at `widget[6..9]`. Walker calls `(*widget->vt[1])()` only if `(widget[6] & widget[8]) != 0 || (widget[7] & widget[9]) != 0`.
- Slot at `+0x314` has NO mode-filter — always called unconditionally. Currently empty in retail; could be a clean asi-mod hook point.

Cross-referencing the walker's 11 slots against master init `CHudWidgetArray_Ctor @ 0x5a6600`'s 24 ConstructHud_* calls revealed:

- **Only 10 widgets are walker-ticked** (TurboMeter, EngineTempGauge, SpeedBreakerMeter, RaceOverMessage, GenericMessage, WrongWayIndi, Countdown, RadarDetector, MenuZoneTrigger, Infractions).
- **The other 14 widgets** (Speedometer, Tachometer, DragTachometer, ShiftUpdater, CostToState, Reputation, HeatMeterInRace, NitrousGauge, LeaderBoard, PursuitBoardInRace, MilestoneBoard, BustedMeter, TimeExtension, GetAwayMeter) update via **FNG event bus** (`PostUIEventToNamedNode` on UI root `DAT_0091cadc`) or are fully passive (BustedMeter, GetAwayMeter).
- This explains BustedMeter's no-op Update found in wave-12 — it's a passive widget.

Vtable map for CHudWidgetArray (12 slots; 7 named): Tick / SetActive / CheckGameState / SetFlag700 / DestroyMaybe / Dtor + 5 still-unnamed.

### Wave-9 (this session, 2026-05-14, post-validation)
- **Infinite-NOS trainer DLL** built and installed to `app/scripts/nfsmw_trainer.asi` (99KB PE32; patches Tweak_InfiniteNOS @ 0x937804 + Tweak_InfiniteRaceBreaker @ 0x988E1C). Validates the entire docs-to-runtime chain. MinGW-w64 installed for build.
- **EAGL physics CORRECTION**: full thread enum shows NO physics worker thread exists. The 4 spawned threads are FileSystem, Network, WaitableTimer, AssetStreaming — all I/O. Physics integrator runs INLINE on main thread via `(*DAT_009885c8)[+0x44]`. DAT_009885c8 is the **PhysicsWorldCoordinator** (constructor @ 0x6fce10, vtable PTR_FUN_008b0e18), distinct from world_root_singleton.
- **Event-bus API mapped**: BusBroadcastEventByHash @ 0x61fc10, BusSubscribeListenerByHash @ 0x61fd00, BusDispatchEventToListenerFilters @ 0x5f9da0, BusFindOrCreateBucketByHash @ 0x61fb40. The 0x1c-byte bus at DAT_0091e0d0 uses an RB-tree of listener buckets.
- **CORRECTION**: `RegisterStartBreakerEventListener @ 0x6332a0` subscribes on hash of "MPursuitBreaker" (environmental cop-stop), NOT "StartBreaker". User-key SpeedBreaker likely uses a different C++ native path (TBD).
- **HUD master init found**: `CHudWidgetArray_Ctor @ 0x5a6600` — 14 widget constructors mapped via state→funclet→widget-name cross-ref.
- **Semantic roles for 15 of 38 uncracked hashes** documented: 5 RefSpec hashes form a directional-emitter selector cluster, 3 Float hashes are an AI-pursuit triplet, etc. Effective crack rate now **294/332 = 88.6%** (when type-self-refs are excluded from denominator).
- **460 attribute-hash disasm annotations** applied: every cracked name now shows `bChunk("NAME") = 0xHASH` inline in Ghidra decompilation.
- **98 SDK plate comments** applied: each SDK-derived function now has source attribution (header file + signature).
- **Net Ghidra renames**: +47 (6,550 → 6,597)

### Wave-8 (this session, 2026-05-14, post community-wordlist)
- **True input-binding system mapped**: 76-row binding template @ 0x008f6d80 (stride 0x34, row-index-is-action-id); 10 functions renamed: PollAllGameActionBindingsPerFrame @ 0x6349b0, ReadGameActionBindingAxisFromDevice @ 0x628940, CopyGameActionBindingTemplateToRuntime, InstallGameActionBindingIntoSlot, DetectGameActionRebindFromDeviceEvent, ApplyGameActionRebindFromReplayLog, FormatGameActionBindingDisplayName, etc. Corrected prior misreading: GAMEBREAKER is action **ID 1**, not 0x9d; 0x9d is DIK_RCONTROL (default key); 0x22 is DIK_G (not DIK_E/SC_E).
- **HUD per-widget update functions**: 13 of 28 widget update functions mapped (Speedometer @ 0x57a540, Tachometer @ 0x57a6e0, Minimap @ 0x59db50, HeatMeter @ 0x7a5aa0, PursuitBoard @ 0x52e0c0, DragTachometer, EngineTempGauge, ShiftUpdater, WrongWIndi, MilestoneBoard, LeaderBoard, RaceInformation, GetAwayMeter). Corrected: HUD is **tick-driven, NOT event-bus-driven** (prior theory wrong); all 65 PursuitBountyAwarded listeners are **AUDIO callbacks**, not HUD updaters.
- **Net Ghidra renames**: +37 (6,513 → 6,550)

### Wave-5 (this session, 2026-05-14)
- **NFSPluginSDK integration**: 181 hardcoded addresses, 65 enums, 245 structs, 178 type headers
- **Script VM = vanilla Lua 5.0.2** (confirmed by error-string signatures); 35-opcode dispatch table
- **Save/Load = MD5 trailer** (not CRC); Documents\NFS Most Wanted\<PlayerName> path
- **Cutscenes = On2 VP6 + MAD** (not Bink); EA SCHl/MVhd container
- **EA Trax = two systems**: interactive in-race score + licensed streamed via EAXS
- **GameBreaker** (= SpeedBreaker UI name): time-scale @ world_root+0x24
- **Race rules engine**: 11-value mode enum cracked; Drift confirmed absent from MW
- **AI racer myths debunked**: no drafting, no AI nitrous, pure rubber-band
- **HUD rendering**: 28 passive FNG nodes; event-bus driven; corrected misnamed 0x504d00

## Hash cracking

True **verified** counts (every name re-hashed with bChunk; no inflated/unverified entries):

| Date | Attribute names cracked | Total | % |
|---|---:|---:|---:|
| Early baseline (attrib_table.json verified) | 68 | 345 | 19.7% |
| 2026-05-14 (wave-6 end, compound wordlists) | 121 | 345 | 35.1% |
| 2026-05-14 (wave-7 end, community wordlists) | **294** | 345 | **85.2%** ✅ |

**Wave-7 breakthrough**: integrated the community NFS hash database (Attribulator + OpenNFSTools + nfsu2-re — 43,102 attribute names from a decade of community modding). Single-pass match added **+173 cracks** in seconds.

**All 5 original mystery hashes solved**:
- `0xB5C0DAC8 = AUTO_SIMPLIFY` (wave-6)
- `0xDA5F19F9 = BEHAVIORS` (wave-6)
- `0xEE0011E3 = SimplePhysics` (wave-7)
- `0x360552DA = ExplosionEffect` (wave-7)
- `0x44F1273B = DROPOUT` (wave-7)

The 80% target named in the plan is **exceeded**. Going from 19.7% → 85.2% in this session.

**Wave-6 added 26 new cracks** (from a combination of agent-RE'd AUTO_SIMPLIFY + direct compound-wordlist crack):

- Float (+19): InitialSpeed, MinScale, forceMultiplier, HeightStart, LengthStart, KnockoutTime, TimeLimit, RaceLength, STIFFNESS, TRAFFIC_SPEED, damageMultiplier, SpawnTime, NumParticlesVariance, NumParticles, LifeVariance, MaxHeatLevel, MaxSize, AUTO_SIMPLIFY, MinRPM, MaxRPM, InitialPlayerSpeed, ResetTime, RESPAWN_TIME, YAW_SPEED, StartTime, DelayTime, DETACH_FORCE
- Bool (+7): PursuitRace, Template, SELECTABLE, TILTING, RandomOpponent, FireOnExit, OneShot
- Text (+6): TrafficPattern, CollectionName, DefaultPresetRide, PlayerCarType, CopSpawnType, CarType
- StringKey (+3): EventSequencer, BankName, **BEHAVIORS** (one of the 5 mystery hashes!)
- UInt32 (+1): message_id
- RefSpec (+1): emittergroup

**5 mystery hashes status**:
- `0xB5C0DAC8` = **AUTO_SIMPLIFY** ✅ (cracked via SDK CamelCase→UPPER_SNAKE conversion)
- `0xDA5F19F9` = **BEHAVIORS** ✅ (cracked via EA-vocab wordlist)
- `0xEE0011E3` (Bool) — semantic role known (Smackable ghost-vs-solid gate); name TBD
- `0x360552DA` (Float) — semantic role known (push-back / snap-back); name TBD
- `0x44F1273B` (Float[2]) — semantic role known (timed continuous force); name TBD

Type corrections caught: `0xEE0011E3` is Bool (was wrongly labelled Float); `0xDA5F19F9` is StringKey (was wrongly labelled Float).

## Bundles decompressed

| Bundle | Decomp size | Status |
|---|---:|---|
| gameplay.bun | 2,105,216 B | ✅ extracted |
| GlobalB.bun | 2,803,648 B | ✅ extracted |
| InGameB.bun | 946,264 B | ✅ extracted |
| FrontB.bun | 6,677,024 B | ✅ extracted |
| **Total** | **12,532,152 B** | All 4 LZC bundles unlocked |

Tool: `tools/nfsmw_bun_reader/jdlz_nfsmw.py` (Python decompressor, byte-perfect output).

## Surprising findings catalog

Discoveries that contradicted prior assumptions, public docs, or community modding lore:

1. **bChunk = Jenkins mix3 (not DJB2/FNV)** — public web sources frequently wrong
2. **JDLZ v0x02 has inverted flag semantics** vs Carbon-era v0x01
3. **Script VM is literal Lua 5.0.2** — not a custom Lua-like
4. **Lua build has POS_A=24** (canonical Lua 5.0 has POS_A=6) — instruction encoding flipped
5. **Save trailer is MD5** (not CRC); MSG_R_BI_DATACRC is orphan netcode string
6. **Cutscenes use On2 VP6 + MAD**, statically linked (no binkw32.dll)
7. **EA Trax has two music systems**: interactive + licensed streamed
8. **No drafting / slipstream code in AI** — pure rubber-band catchup
9. **AI does NOT use nitrous** — zero xrefs to EPlayerTriggeredNOS
10. **MW does NOT ship Drift mode** — `drift` is leftover Underground-era localization
11. **GameBreaker ≠ PursuitBreaker** — two distinct mechanics
12. **ProcessUIOrHUDElements is NOT the HUD walker** (misnamed historically)
13. **LookupUIInputBindingByCode is NOT input bindings** (it's FECarRecord pool)
14. **23-slot PerPlayerSubsystemTick is for audio+UI only**, not vehicles
15. **Most engine debug strings preserved in retail** — major RE accelerator

## Tooling milestones

- `tools/nfsmw_bun_reader/jdlz_nfsmw.py` — JDLZ v0x02 decompressor (~150 lines Python)
- `/tmp/ghidra_post.sh` — direct HTTP wrapper for Ghidra plugin API (bypasses broken MCP bridge)
- `/tmp/extract_sdk_v2.py` — NFSPluginSDK address/type extractor
- `/tmp/apply_sdk_renames_v2.py` — bulk-rename Ghidra functions from SDK
- `/tmp/apply_sdk_enums.py` / `apply_sdk_structs_v2.py` — bulk type DB application
- `docs/sdk_addrs.json` / `sdk_enums.json` / `sdk_structs.json` — extracted SDK index
- `docs/renames.csv` — full Ghidra rename export (6,513 entries, refreshed post wave-6)
- `docs/attribute_hashes.md` — full registry of all 345 attribute hashes
- `docs/nfsplugin_sdk_mw05/` — mirrored SDK headers (BSD-3, attributed)

## Process learnings

1. **Open-source signal first**: identifying Lua, MD5, VP6, MAD, Jenkins, etc. inside the binary unlocks free names. Always pattern-match against well-known formats before bespoke RE.
2. **Parallel agents for breadth**: 8 agents in wave-5 mapped 8 subsystems in 25 minutes. Single-agent serial work would take days.
3. **Use the community SDK first**: berkayylmao/NFSPluginSDK gave us 150 function addresses + class hierarchy + type system in one BSD-3 pull. Re-deriving any of this from scratch is wasteful.
4. **Bypass broken tooling, don't fix it**: when the Ghidra MCP bridge broke (`dry_run` schema bug), we wrapped curl + JSON directly to port 8089. 5-minute fix, all 162 tools accessible.
5. **Verify memory entries against current code**: 4+ stale memory claims were corrected in wave-5 (LookupUIInputBindingByCode, MSG_R_BI_DATACRC, ProcessUIOrHUDElements, Bink). Memory is a snapshot, not authoritative.
6. **Subagent self-checking**: spawn agents with `advisor()` access; they catch their own misreads (saw at least 2 catches in wave-5).
7. **objdump fallback**: when a single function needs deep RE and Ghidra's UI/MCP is slow, raw `objdump -d --start-address=X --stop-address=Y` is faster.

## What's next (post wave-5)

Listed by ROI:

| Target | Why | Estimated effort |
|---|---|---|
| Crack 5 mystery attribute hashes | Last gaps in attribute schema | Low (1 session) — need source/PDB |
| Crack remaining 51 attribute names | Better mod tooling | Hard — wave-7 community wordlists hit 85%; last 51 hashes don't appear in any public list, likely need PDB/source leak |
| Map true input-binding lookup | 0x56ecc0 false claim left a gap | Low (1 agent) |
| Locate HUD per-widget updates | Needs live debugger breakpoint on widget-name strings | Medium |
| EAGL physics integrator (worker side) | Most-requested mod target | High (debugger + worker-thread state) |
| Lua bytecode disassembly | Decode shipped .luac scripts | Medium (build patched Lua 5.0) |
| GameSpy reimpl (OpenSpy-style) | Revive multiplayer | Out of scope |
| ProStreet / Carbon JDLZ verification | Other EA titles likely use same v0x02 | Low (apply existing tool) |

The goalpost shift from "full source in Visual Studio" to "mod-SDK quality subsystem map" is essentially complete. Most remaining work is depth and edge cases, not new breadth.
