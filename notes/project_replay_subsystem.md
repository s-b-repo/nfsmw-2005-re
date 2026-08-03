---
name: replay/joylog subsystem
description: NFSMW captures a deterministic input log per race (CaptureJoylog.jlg) and can replay from one (ReplayJoylog.jlg). Separate higher-level CarReplay singleton holds per-vehicle physics snapshots.
type: project
originSessionId: c4edf485-e85f-4e2f-ac31-e021ba66e8d6
---
Two distinct replay layers:

## 1. Joylog (low-level input/sim capture)
Master switch `g_nJoylogEnabled @ 0x9258c8`. When enabled, `InitializeJoylogReplayOrCapture @ 0x660530` decides:
- "ReplayJoylog.jlg" present → playback mode (`g_nJoylogPlaybackActive @ 0x9258d4 = 1`, allocates 0x4118 byte buffer at `g_pJoylogPlaybackBuffer @ 0x9258dc`)
- otherwise → capture mode (`g_nJoylogCaptureActive @ 0x9258d8 = 1`, opens "CaptureJoylog.jlg" mode 6 (write), buffer at `g_pJoylogCaptureBuffer @ 0x9258e0`)

The deterministic sim-step generator `SimTickStepWithJoylogHook @ 0x661280` reads tick counts from playback buffer or accumulates real-time dt + writes ticks to capture buffer. Channels include `JOYLOG_CHANNEL_*` constants (sim step count, sub-tick, input axes, button state).

## 2. CarReplay (vehicle-state replay singleton)
`GetCarReplaySingleton @ ?` (already in Ghidra as that name). `BeginCarReplayRecording @ 0x56c3e0` starts recording for self ("TheHost") plus up to 3 multiplayer clients ("ClientN" for n in 0..2 from DAT_009b40f8). Spins until first frame of recorded data lands.

**Why:** Knowing this dual-layer structure means: (a) deterministic-replay tools can target the joylog format, (b) a third-party replay-camera tool needs to hook the CarReplay singleton (ReplayCameras array @ 0x00895098), not the joylog. Helps separate "rerunning the inputs" from "playing back the camera path".

**How to apply:** When asked about replay/capture/recording, distinguish which layer. Joylog is determinism-driven (sim ticks, inputs); CarReplay is presentation-driven (camera, vehicle interpolation, multiplayer client list).
