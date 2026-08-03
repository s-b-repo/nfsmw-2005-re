---
name: audio subsystem class roles + heap
description: Four audio entity classes (TypeA/TypeD/SmoothAudio/UIScreenAnim), each with its own vtable; NFSMixMaster is the master mixer; ~5.6MB pre-allocated arena.
type: project
originSessionId: c4edf485-e85f-4e2f-ac31-e021ba66e8d6
---
## Audio entity classes
Four distinct audio entity types. Each has its own vtable and a different role in the audio mix. All four entity types tick under the 23-slot PerPlayerSubsystemTick array (slot 1 explicitly is audio).

| Class | Role | Vtable global |
|-------|------|---------------|
| AudioEntity_TypeA   | 3D positional sounds (vehicles, world emitters)        | g_pVtableAudioEntityTypeA @ 0x894cc8 |
| AudioEntity_TypeD   | 2D ambient/non-spatial loops                            | g_pVtableAudioEntityTypeD @ 0x894e48 |
| SmoothAudioEntity   | Damped parameter interpolator (RPM, throttle, etc.)     | g_pVtableSmoothAudioEntity @ 0x894e90 |
| UIScreenAnimAudio   | UI screen anim overlays (front-end clicks, transitions) | g_pVtableUIScreenAnimAudio @ 0x894f70 |

**Why:** Earlier I had mislabeled `SmoothEntity_DampedParamInterpStep` as a vehicle integrator (incorrect — it's audio param interp). Correct mental model: PerPlayerSubsystemTick slot 1 = audio entity tick array, NOT a vehicle physics path.

## Audio infrastructure globals
- `g_pNFSMixMaster @ 0x911fa8` — master mixer singleton (massive xref count, used by every audio path)
- `g_pAudioMixerArenaBase @ 0x008ee558` — base of the audio heap (used by `AllocFromAudioMixerArena @ 0x4ac010`); ~5.6 MB allocated at boot in `InitializeAudioMixer @ 0x4cc3a0`
- `EAXS_StreamManager` — streaming-music subsystem (see strings)
- `EAX_CarState` — per-car audio state passed to vehicle audio dispatcher

## File formats
- `MW_Music.mus` — score sequence file
- `MW_Music.mpf` — music pattern/transition file
- Engine sound banks: `CARSFX_TrafficEngine`, `CARSFX_Skids`, `CARSFX_Nitrous`, `CARSFX_Turbo`, `CARSFX_BottomOut`
- Cop chatter bank
- `SFXCTL_Engine` — engine-sound controller class

**How to apply:** When debugging an audio issue, classify by entity type first (3D? UI? smoothing param?). Then look at calls into the matching vtable. The mix master coordinates all four feeds.
