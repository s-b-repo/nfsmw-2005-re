---
name: ea-trax-licensed-music-player
description: "Two-flavor music system. Licensed-track (\"EA Trax\") metadata lives in the attribute bundle and feeds an attribute-driven jukebox; the interactive in-race score lives in MW_Music.mus/mpf (Pathfinder5). Both share the same SFXObj_PFEATrax controller class."
metadata: 
  node_type: memory
  type: project
  originSessionId: c4edf485-e85f-4e2f-ac31-e021ba66e8d6
---

## Top-level architecture
- **Controller class**: `EATrax_MusicFlowConstruct @ 0x4f8830` (vtable PTR_FUN_00899b80). 0x18C bytes. Allocated by `EATrax_MusicFlowAllocate @ 0x4f9ca0` from the audio mixer arena tagged "SFXObj_PFEATrax".
- **Event dispatcher**: 8 hash-keyed handlers stored at controller +0x5b..+0x62, registered via FUN_004eb180. Hashed-event names:
  `Pathfinder5` (FUN_004e7bc0), `EATraxInit` (LAB_004df420), `Event` (LAB_004f0770), `Control` (LAB_004dfb80), `PartUpdate` (LAB_004dfbe0), `0x20d60dbf` (LAB_004dfc20), `InteractiveDone` (LAB_004dfc30), `Swap` (LAB_004dfc40).
- Dispatch through `MNotifyMusicFlow` (hash cached in DAT_00913bec via `GetMessageHashMusicFlow @ 0x4ae2d0`).

## Two music modes
Save-byte at `g_pSaveOptions+0x7c`:
- `0` = **Interactive** — score-driven, plays MW_Music.mus/mpf clips chosen by Pathfinder5 hooks (in-race adaptive music). Uses helper `%.*s%d.mus` (`FUN_00830750`) to load numbered .mus stems.
- `1` = **EA Trax** — licensed jukebox, plays licensed songs picked from the playlist.
Toggle: `EATrax_ToggleMusicMode @ 0x51df50`. UI string-hashes 0x4ca36b89 / 0xa9c9c8f7.

## Playlist storage
Lives inside the save / options blob at `g_pSaveOptions+0x324`, 0x108 bytes = up to ~33 entries × 8 bytes:
```
struct PlaylistEntry { u32 trackIdx; u8 mode; u8 pad[3]; }
```
Mode: `0` OFF, `1` FE-only, `2` IG-only, `3` AL (both).
- `EATrax_CycleTrackMode @ 0x51e000` cycles the byte per track (UI string-hashes: 0=0x9cce9f86, 1=0x5278c50b, 2=0x5c1b351c, 3=0x9cce64c4).
- `EATrax_CommitPlaylistEdits @ 0x51e110` writes UI list back.
- `EATrax_DeserializeFromSave @ 0x5acb70` copies the 0x108 block from network/save snapshots, then dispatches `EATraxInit`.

## Active-track bitmasks
`EATrax_RebuildPlaylistBitmasks @ 0x4df330` walks the playlist and writes:
- `g_nMusicActiveBitmaskFE @ 0x8f2080..` (count `DAT_008f2088`)
- `g_nMusicActiveBitmaskIG @ 0x8f2098..` (count `DAT_008f20a0`)
- `g_nMusicModeFlagSaveCopy @ 0x8f2094` mirrors save+0x7c.
Up to 32 tracks per pool (uses `1 << trackIdx`).

## Track-metadata database (the licensed-music table)
`EATrax_LoadTrackDBFromAttributes @ 0x5ab450` loads from the attribute system:
- Bundle hash: **0x7e4b0ed2**
- Track-count attribute hash: **0x5611db83** → `g_nMusicTrackCount @ 0x8f42c4`
- Per-track sub-attribute hash: **0x737714de** (iterated 0..count-1)
- Per-track filename sub-attribute: **0x58f80e5e**

Each track produces a 20-byte struct stored in `g_pMusicTrackDBBegin/End/Cap @ 0x9123d0/d4/d8`:
```
struct MusicTrack {
  +0x00 const char* title;       // attr field [7]
  +0x04 const char* artist;      // attr field [0xb]
  +0x08 const char* defaultMode; // attr field [3] - "FE"|"IG"|"AL"
  +0x0c const char* filename;    // sub-attr 0x58f80e5e, field [3]
  +0x10 u32         flagsOrDur;  // attr field [0xc]
}
```
Default-mode → mode-byte mapping: "FE"=1, "IG"=2, "AL"=3, other=2.

## Audio file formats (split)
- **Interactive score** = `MW_Music.mus` (sequence) + `MW_Music.mpf` (pattern/transitions), plus numbered stems via `"%.*s%d.mus"`. Loaded by `FUN_00830750` (asset-type tag `-0x41205313` / `0xBEDFACED`).
- **Licensed EA Trax tracks** = streamed via the `EAXS_StreamManager` (boot: `EAXSStreamManagerBoot @ 0x4d133a`, gameplay-init: `EAXSStreamManagerInitForGameplay @ 0x4d163a`). Voice/sample wrappers are 0x24-byte structs with vtable `PTR_FUN_00896ae8`. Filenames come from the per-track attribute `0x58f80e5e` — extension not yet confirmed (likely a streamed sample bank, not Bink/.asf — see open questions).

## Volume / duck mechanism
Audio-fade slot queue at `g_abAudioVolumeFadeSlots @ 0x91d928`:
- 12-byte stride, max 63 slots, each `{u32 type, u32 param, u32 enabled}`.
- Inserter: `FERequestAudioVolumeFadeSlot @ 0x576c50`.
- Music duck is `type=2`; calls insert it whenever cop-chatter/speech is active.
- Trigger flags: chained from `PTR_PTR_008f8408` (audio routing controller). Slot 4 = speech path (sets controller+0xac |= 0x40000); slot 5 = cop chatter (sets +0xac |= 0x20000 and pushes a duck fade slot).
- Volume options keys (AOAttribute hashes): `AOEATraxMusicMode`, `AOFEMusicVol`, `AOIGMusicVol`, `AOInteractiveMusicVol`, `AOSpeechVol`, `AOSFXMasterVol`, `AOCarVol`.

## UI bindings
- Screen FNG assets: `EA_Trax.fng`, `EA_TRAX.fng`, `EA_Trax_Jukebox.fng` / `EA_TRAX_JUKEBOX.FNG`.
- UI class strings: `UIEATraxScreen`, `OMEATrax`, `AOEATraxMusicMode`.
- 3 row positions in the jukebox screen: `TRAX_POS_1/2/3`.
- HUD action `HUDACTION_NEXTSONG` (in-race skip-track).
- Audio routing: `EA_Trax.fng` is registered in `FE_AudioRoutingTableByScreenHash @ 0x4c2370` along with the other FE screens.

## Renamed (this session)
| Addr | New name |
|------|----------|
| 0x4f8830 | EATrax_MusicFlowConstruct |
| 0x4f8ac0 | EATrax_MusicFlowDestruct |
| 0x4f9ca0 | EATrax_MusicFlowAllocate |
| 0x4df330 | EATrax_RebuildPlaylistBitmasks |
| 0x5ab450 | EATrax_LoadTrackDBFromAttributes |
| 0x51df50 | EATrax_ToggleMusicMode |
| 0x51e000 | EATrax_CycleTrackMode |
| 0x51e110 | EATrax_CommitPlaylistEdits |
| 0x5acb70 | EATrax_DeserializeFromSave |
| 0x4d133a | EAXSStreamManagerBoot |
| 0x4d163a | EAXSStreamManagerInitForGameplay |
| 0x576c50 | FERequestAudioVolumeFadeSlot |
| g 0x8f42c4 | g_nMusicTrackCount |
| g 0x9123d0/d4/d8 | g_pMusicTrackDBBegin/End/Cap |
| g 0x91d928 | g_abAudioVolumeFadeSlots |
| g 0x8f2080 | g_nMusicActiveBitmaskFE |
| g 0x8f2098 | g_nMusicActiveBitmaskIG |

## Open questions
- Confirm the on-disk extension/container for the licensed EA Trax tracks. No `.asf`, `.mp3`, `.wma`, `.snr`, `.sng`, `.ssx` strings found. Most likely a custom EA streamed-sample bundle accessed by the filename stored in attribute 0x58f80e5e (need to inspect actual `.bin` content or trace `EAXS_StreamManager` open calls).
- Identify the `Pathfinder5` event-handler (`FUN_004e7bc0`) and how it picks `.mus` stems for in-race dynamic transitions.
- License/copyright blob: not yet located in strings — may live in a localized `.bun` outside `speed.exe`.
- Confirm the duck-trigger source flags `PTR_PTR_008f8408 slot[4..5]` correspond to cop-chatter SFXObj_Speech.
