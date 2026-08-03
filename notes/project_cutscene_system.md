# Cutscene / Movie Player Subsystem

## Codec — NOT Bink

NFSMW does **NOT** use Bink. PE imports contain no `binkw32.dll`. The codec
strings `VP6_CODEC_INTERNAL`, `MAD_CODEC_INTERNAL`, `print_ch_codec`, `FRAME`
appear in the binary at `0x008c2438..0x008c28d0` — statically-linked **On2 VP6
video + MAD audio** in a custom EA chunk container. On-disk extension is `.vp6`
(e.g. `MOVIES\blacklist_01_english_ntsc.vp6`, `MOVIES\storyfmv_saf25_english_ntsc.vp6`).

Chunk container: **EA SCx / MVhd** (verified by hexdump of
`MOVIES\attract_movie_english_ntsc.vp6` — starts with `MVhd` then `06PV`
(="VP06" little-endian), interleaved with `SCHl`/`GSTR` audio blocks and
`MV0K` (=`0x4d56304b`) video-keyframe markers). `ProcessReadChunkAndCreateCodec
@ 0x007f7c7e` reads the FOURCC, then `FUN_007faaee`→audio (MAD), `FUN_007faad1`
→VP6-keyframe (`MV0K`), `FUN_007faac2`→VP6-frame. The `MV0K` magic appears as
loop-resync sentinel in `ProcessVp6DecodeFrameDispatch @ 0x007fa092`.

Codec vtable `g_apOnVp6MadCodecVtable @ 0x008c2850`. Decode entry
`ProcessVp6DecodeFrameToYuvBuffer @ 0x007f9fc2` brackets the decode with
`__control87(0x10000, 0x30000)` (denormals-flush; classic codec FP hygiene).

## High-level player class

`g_pMoviePlayerSingleton @ 0x0091cb10` — lazy-allocated 328-byte (0x148) object
(see `MoviePlayer_GetOrCreateSingleton @ 0x00525df0`). Built by
`MoviePlayer_ConstructInitState @ 0x00517520`. Key fields:
- `+0x11c` = state (3=idle, 5=playing, transitions through 0/4)
- `+0x120` = next-state
- `+0x140` = movie streamer object (codec wrapper at 0x007f7fcd)
- `+0x144` = active decoder
- `g_MovieFrameTexture @ 0x0091cb28` — current decoded RGB(A) texture used as
  movie quad source

`MoviePlayer_IsActivelyPlaying @ 0x00517a20` = `state ∈ {3,4,5}`.

## Lifecycle

1. **Entry**: `ProcessMovieOpenAndBegin @ 0x00542a40` (Movie state-machine
   entry). Reads filename from `param_1[1]`, loop flag from `param_1[5]`,
   audio-mute from `param_1+0x15`. Calls `FUN_007f7dcb` to mount the .vp6
   stream, then `InitializeMovieStreamerAndOpenDecoders @ 0x007f7fcd` to bind
   VP6+MAD codecs. On success: `InitializeMovieTextureShape @ 0x006e1880` builds
   the on-screen quad, state→5. On failure or `g_dwSkipMoviesFlag @ 0x00926144`
   set, immediately fires `0xc3960eb9` (movie_done event hash) via
   `ScheduleUIDeferredEvent` to skip.
2. **Per-frame tick**: `ProcessMoviePlayerPerFrameTick @ 0x00525f70` advances
   the stream (`FUN_007f81df`) and decodes a frame (`FUN_007f7bba`). Guarded by
   `DAT_0091cc80` (re-entry lock).
3. **Render**: `ProcessMovieScreenRenderQuad @ 0x00599db0` (only when state==5)
   pulls `g_MovieFrameTexture`, builds UVs from width/height in screen struct,
   submits quad via `FUN_00591460`. Stretch/letterbox handled here.
4. **End / cleanup**: `ProcessMovieStateTickAndCleanup @ 0x00542c50` —
   detects state==5 with next-state==MOVIE_DONE, broadcasts message-hash
   `0xc3960eb9` to all UI listeners, calls `FUN_006cb2a0` (resume world sim),
   tears down texture and decoder.

## FE screen wrappers

- `FEAnyMovieScreen` (vtable `0x008a17d4`, ctor
  `InitializeFeAnyMovieScreen @ 0x0058eca0`) — frontend movie playback (intro,
  attract, blacklist intros).
- `InGameAnyMovieScreen` — same class family, used for tutorial popups and
  storyfmv during gameplay.
- `MovieScreen` string at 0x008a0f64.
- `FEANYMOVIE.FNG`, `MW_LS_IntroFMV.fng`, `MW_LS_AttractFMV.fng`,
  `LS_PSA.FNG`, `LS_EALOGO.FNG`, `LS_THXMovie.fng` are the .fng layouts that
  host the quad.
- `CheckIsActualGameplayScreen @ 0x005864b0` returns false for these (so HUD
  doesn't draw over them).

## Movie path → flags table

`g_apMoviePathFlagsTable @ 0x008f3818..0x008f3948` — 38 entries × 8 bytes
`{const char* path, uint flags}`. Iterated by
`FindMovieFlagsByPathString @ 0x005178b0` doing a linear strcmp scan.

Flag values observed:
- `0x5A` — `MOVIES\attract_movie`
- `0x55` — tutorial movies (drag/sprint/tollbooth/bounty/pursuit/speedtrap)
- `0x4B` — `MOVIES\psa` (special: returns 0 if `DAT_009260b8` already-seen flag set, suppressing replay)
- `0x41` — all 15 `MOVIES\blacklist_NN` boss intros
- `0x7F` — all 13 storyfmv mission cutscenes
- `0xFFFFFFFF` — sentinel before `MOVIES\attract_movie`

The high bit of these flags appears to be the **skip-cutscene allowed**
mask (PSA legally must not be skippable on first view; storyfmv have higher
priority hence different flag).

## Cutscene catalog (verified from .vp6 + path strings)

### 15 Blacklist boss intros
`MOVIES\blacklist_NN` (NN = 01..15). Per NFSMW canon:
1. Sonny  2. Bull  3. Ronnie  4. Taz  5. Vic  6. Big Lou  7. Baron
8. Earl  9. Kaze 10. Ming 11. Webster 12. Jewels 13. Izzy 14. Bull (Vince?) 15. Razor.
*Identifiers in code are purely numeric — no per-rival name strings here;
the matching to character names happens in the LANGUAGES\ENGLISH.BIN via
`BLACKLIST_RIVAL_%02d_NAME`.*

### 13 Story (mission) FMVs
`MOVIES\storyfmv_NN` codes — these track mission slugs:
- `rac01` (race intro), `saf25` (safehouse), `roc02`, `raz08` (Razor),
  `rap30` (rap sheet), `pol17_mot21` (cops/motorcycle), `pin11` (pink slip),
  `her136` (heroine?), `epi138` (epilogue), `dda01` (DDay), `cro06_coh06a`
  (crossroads), `bus12` (bust), `bla134` (blacklist final).

### Tutorials (5)
`drag_tutorial`, `sprint_tutorial`, `tollbooth_tutorial`, `bounty_tutorial`,
`pursuit_tutorial`, `speedtrap_tutorial`.

### Pre-game / system
`intro_movie`, `attract_movie`, `ealogo`, `psa`.

## Trigger mechanism

Movies are triggered by **script natives** (registered in
`RegisterScriptNativesGameplay @ 0x0061e750`):
- `PlayTutorial` → `LAB_006124e0` — calls
  `ProcessQueueTutorialMovieByName @ 0x00525d50` with short name like
  `pursuit_tutorial`, pushes `FEAnyTutorial.fng` screen.
- `IntroduceRival` → `DAT_00605550` — used for blacklist intros.
- `PlayHackE3FMV` → `DAT_00604c60` — devkit/E3-demo hack play function.
- `Fade` → `Fade_Impl` — used before/after movie transitions.
- `DoSafeHouseIntro` → `LAB_00605560` — fires `storyfmv_saf25`.
- `SkipCareerIntro` → `SkipCareerIntro_Impl` — instant-skip for intro_movie.

No central "trigger table"; cutscenes are scheduled by the **gameplay scripts**
(parsed earlier in InGameA.bun) by calling these natives at race-end / engage /
milestone events.

## Skip-cutscene flow

Two skip paths:

1. **Config-level skip**: `g_dwSkipMoviesFlag @ 0x00926144`, parsed from
   `Net_ParseMultiplexerConfigFile @ 0x0078a9c7` (multiplex.cfg `SKIPMOVIES=1`).
   When set, `ProcessMovieOpenAndBegin` short-circuits — no .vp6 load,
   immediate `0xc3960eb9` (movie_done) event.

2. **Runtime skip (button press)**: handled in the FE event handler
   `FUN_00551f80` for `FEAnyTutorialScreen`. Buttons map via UI hashes:
   - `0xc407210` = Accept/A (sometimes acts as next/skip)
   - `0xc3960eb9` = MovieFinished (broadcast when user presses skip OR EOF)
   - `0xb5971bf1` = Cancel/B (skip path)
   - `0xc519bfc3`, `0xd05fc3a3`, `0x9120409e` = other tutorial actions.
   The handler clears the screen, fires deferred-event `0xc3960eb9` to all FE
   children, which propagates to `ProcessMovieStateTickAndCleanup` to tear
   down the player.

PSA is exempted from skip-via-config because of the `DAT_009260b8`
already-seen guard on lookup — PSA still plays on first launch even with
SKIPMOVIES=1 (suspected; not yet confirmed dynamically).

## Audio sync

Audio is **internal** to the .vp6 container (MAD codec — not external WAV).
Same chunk stream interleaves video and audio; `ProcessReadChunkAndCreateCodec`
peels them apart by FOURCC tag. There is one separate path
`eSNDPAUSE_MOVIE @ 0x00896908` indicating the **game's NFSMixMaster** is
silenced while a movie plays (the in-engine audio bus is paused, MAD audio
takes over).

`SFXObj_Movies` (string @ 0x0089814c) hints there's a small SFX bus dedicated
to movie-audio routing back into the main mixer.

## Key renamed addresses (apply when revisiting)

| Address | New Name | Role |
|---------|----------|------|
| 0x00517520 | MoviePlayer_ConstructInitState | ctor of 328-byte player |
| 0x00525df0 | MoviePlayer_GetOrCreateSingleton | lazy alloc + init |
| 0x00517a00 | MoviePlayer_GetCurrentFrameTexture | returns texture or default |
| 0x00517a20 | MoviePlayer_IsActivelyPlaying | state ∈ {3,4,5} |
| 0x00525b20 | CheckShouldDeferToMovieOrFade | gate on movie+fade |
| 0x00525d20 | InitializeStoryFmvSaf25Filename | sets default story filename |
| 0x00525d50 | ProcessQueueTutorialMovieByName | tutorial entry from script |
| 0x00525f40 | ProcessMovieDecoderInitFromOpenFile | binds decoder to MoviePlayer |
| 0x00525f70 | ProcessMoviePlayerPerFrameTick | per-frame decode+advance |
| 0x00542a40 | ProcessMovieOpenAndBegin | top-level open .vp6 + start |
| 0x00542c50 | ProcessMovieStateTickAndCleanup | end-of-movie teardown |
| 0x005178b0 | FindMovieFlagsByPathString | path → flag lookup |
| 0x0058eca0 | InitializeFeAnyMovieScreen | FE screen ctor |
| 0x00599db0 | ProcessMovieScreenRenderQuad | per-frame quad render |
| 0x005864b0 | CheckIsActualGameplayScreen | FE screen classifier |
| 0x00595d40 | CheckShouldShowPauseOrMovieDuringHud | HUD-suppress gate |
| 0x006e1880 | InitializeMovieTextureShape | builds the on-screen quad |
| 0x006f0150 | InitializeMovieFinishedNotifyMessage | event ctor for 0xc3960eb9 |
| 0x007f7c7e | ProcessReadChunkAndCreateCodec | container tag → codec |
| 0x007f7fcd | InitializeMovieStreamerAndOpenDecoders | wires decoders |
| 0x007f9e82 | GetVp6CodecAllocateFreeFrameNode | VP6 frame pool |
| 0x007f9ed3 | InitializeVp6CodecObject | VP6 codec ctor |
| 0x007f9fc2 | ProcessVp6DecodeFrameToYuvBuffer | VP6 frame decode |
| 0x007fa07c | GetVp6CodecFactoryNew | VP6 factory |
| 0x007fa092 | ProcessVp6DecodeFrameDispatch | VP6 vtable[2] |
| 0x007fa552 | GetMadCodecAllocateIorPFrame | MAD I/P-frame pool |
| 0x007fa5a3 | GetMadCodecAllocateBFrame | MAD B-frame pool |

| Data | New Name |
|------|----------|
| 0x0091cb10 | g_pMoviePlayerSingleton |
| 0x0091cb28 | g_MovieFrameTexture (still default-typed) |
| 0x00926144 | g_dwSkipMoviesFlag |
| 0x008f3818 | g_apMoviePathFlagsTable |
| 0x008c2850 | g_apOnVp6MadCodecVtable |

## Event hashes

- `0xc3960eb9` — movie_done / MNotifyMovieFinished
- `0xc407210`  — accept (advances tutorial pages / commits skip)
- `0xb5971bf1` — cancel (tutorial back / cancel)
- `0xdbdf2888` — tutorial text-finished sub-event
- `0x935a6a7f`, `0x911ab364`, `0x911c0a4b`, `0x9120409e` — tutorial transitions
- `0xe1fde1d1`, `0xc98356ba` — start/stop helper events

## Open questions

1. **DAT_009260b8** — exact semantics of the PSA-skip guard flag. Likely "user
   has already watched PSA at least once during session" (set by PSA finish
   handler) — not yet xref'd.
2. **DAT_009260b8 vs SKIPMOVIES** interaction at startup — does the launcher
   path actually still play `intro_movie`, `ealogo`, `psa` when SKIPMOVIES=1?
   Decompiled control flow says yes for PSA (lookup short-circuits to 0 only
   when already-seen) but no for the others. Needs runtime confirmation.
3. **Storyfmv → mission mapping**: codes like `cro06_coh06a`, `pol17_mot21`
   pair two mission slugs — implies one cutscene covers two events. The
   trigger source (which script native fires storyfmv playback for which
   mission) is in InGameA.bun gameplay scripts, not in speed.exe directly.
4. **PlayHackE3FMV** — what playlist did the E3 2005 demo use? Likely
   bypassed normal trigger flow and went straight to a sequence of
   `attract_movie`/`intro_movie`.
5. **Audio bus**: SFXObj_Movies + eSNDPAUSE_MOVIE imply a routed bus, but
   the exact NFSMixMaster channel index is not yet renamed.
6. **Real-time engine cutscenes** — searched for `.scn`, `cutscene`,
   `Cutscene` — nothing matches. All "cinematics" in NFSMW PC appear to be
   pre-rendered .vp6 FMV. No real-time engine cutscenes confirmed.
   `FmvCameras` string @ 0x008950a8 might hint at in-engine "FMV-style"
   camera moves but that's separate (race-end cam scripts, not cutscenes).
