---
name: multiplayer/network subsystem
description: Host-authoritative GameSpy + LAN replay-sync model; session state machine in Net_MultiplayerSessionUpdateLoop @ 0x761b30 driven by g_nIsNetClient flag.
type: project
originSessionId: c4edf485-e85f-4e2f-ac31-e021ba66e8d6
---
NFSMW shipped with GameSpy multiplayer (now defunct) and LAN play. The network code is still present — the same code path drives both, just different transport.

## Globals
- `g_nIsNetClient @ 0x9b416c` — 0 = host, 1 = client. Branch across the entire session loop.
- `g_dwNetClientVehicleSlots @ 0x9b40f8 [3]` — vehicle handles for remote clients (0 = unoccupied).
- `g_nNetSessionState @ 0x9b41fc` — state-machine counter. 1 idle / 2 init / 4 racing / 5 post-race / 6 finished.
- `g_pNetCarReplaySingletonRef @ 0x9b4218` — cached CarReplay singleton.
- Game name buffer at 0x9b4180 (char[64]).

## Config file (Multiplexer)
`Net_ParseMultiplexerConfigFile @ 0x78a900` parses a launch-time config. Keys: `ISSERVER`, `NUMCLIENTCARS`, `SERVERIP`, `SERVERPORT`, `CLIENTIP%d`, `FORCE CLIENTSHUTDOWN`, `NetworkDebug`, `NetworkUserName`, `LobbyServerAddr`, `LobbyServerPort`. Populates client slots via Net_PopulateClientSlots @ 0x79aa50.

## Session lifecycle
1. `Net_SessionInitialize @ 0x7617d0` — transitions state 1→2; calls config init + quantizer setup
2. `Net_QuantizerInitializeAndServerCheck @ 0x7a15d0` — branches on `g_nIsNetClient`:
   - host → FUN_0079f690 (host-side handshake)
   - client → `Net_ClientReplayHandshake @ 0x7a1310`
3. `Net_MultiplayerSessionUpdateLoop @ 0x761b30` — per-frame loop, big switch on session state. Handles vehicle-state pkt send/recv, timeout (Net_ServerTimeoutCheck @ 0x7a12e0 / Net_ClientTimeoutCheck @ 0x7a13c0).

## Replay-sync as transport
Vehicle telemetry is broadcast via the **CarReplay singleton** (already named GetCarReplaySingleton). Updates flow:
- Host records reference frames per vehicle
- Clients register via `Net_RegisterClientVehicleWithReplay @ 0x78c1d0` at race start
- Frame state via `Net_GetCarReplayFrameState @ 0x78c380`, count via `Net_GetCarReplayRecordedFrameCount @ 0x78c2a0`

Compression: `Net_QuantizerInitialize @ 0x78a220` builds two quantizers (`m_messageTypeQuantizer`, `m_driverNumberQuantizer`) for bandwidth-efficient binary encoding.

## Script-visible events
`MPlayerEnterPursuit` and `MPursuitOver` are bChunk-hashed and dispatched as script events. Hash getters: `GetEventHash_MPlayerEnterPursuit @ 0x626480`, `MPursuitOver` at FUN_00626550 (cache pattern same).

## Winsock
`WSARecv`, `WSASend`, `WSACreateEvent` imports → standard async socket model. Lobby uses TCP; vehicle-state probably UDP given the quantizer + frame-loss-tolerant replay model.

**Why:** Knowing the architecture (host-authoritative, replay-driven) tells modders that "online play" can't easily be revived without reimplementing the lobby; LAN play might still work if you bypass GameSpy login.

**How to apply:** When debugging multiplayer issues, branch the analysis: (a) before-race = lobby + handshake, look at Net_SessionInitialize chain; (b) in-race = state machine in Net_MultiplayerSessionUpdateLoop, vehicle telemetry via CarReplay; (c) error = check timeouts + g_nNetSessionState.
