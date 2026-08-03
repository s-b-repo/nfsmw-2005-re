---
name: world streamer + AI path graph
description: Region-grid streaming via DispatchRegionLoaderHandler @ 0x666aa0; track BUNs load on-demand; AI follows 6-byte path-segment nodes via WRoadNetwork.
type: project
originSessionId: c4edf485-e85f-4e2f-ac31-e021ba66e8d6
---
## Streaming architecture

The world is split into **regions** keyed by region IDs. Three parallel pipelines:

1. **InGame bundles** — `InGameA.BUN`, `InGameB.LZC`, optional `InGameSplitScreen.BUN`. Per-region mission/gameplay assets.
2. **Track bundles** — `TRACKS\<name>.BUN` loaded on-demand for race-specific splines + AI paths.
3. **Spline curve cache** — `EnsureSplineCurveCacheReady @ 0x794f80` pre-builds Catmull-Rom-ish interpolation tables (6 nodes × 8 bytes each).

Hashes used by `DispatchRegionLoaderHandler @ 0x666aa0`:
- 0x1974ff09 — InGame bundle key
- 0xcda340f8 — Track bundle key
- 0xeff164cb — exit/stop signal
- 0x98667b3e — state-push signal

`OpenAssetBundleStream @ 0x65fd30` enqueues a stream; `ConstructAssetBundleStream @ 0x65fca0` initializes the AssetBundleStream object.

## AssetBundleStream layout

```
+0x08 : is_active (byte)
+0x0c : mode (1=sync, 2/3/4=async variants)
+0x10 : priority (0..9)
+0x14 : user param
+0x18 : override size (0 = auto)
+0x1c : asset name hash
+0x20 : bytes loaded
+0x24 : duplicate hash
+0x28 : read buffer size (default 0x2000)
+0x3c : error byte
+0x40 : total bytes
```

## Singletons / globals
- Track streamer singleton via `GetTrackStreamerSingleton @ 0x79ca30`
- AI track path table base @ `DAT_009a3a64` — 6-byte nodes; access via `GetAITrackPathSegmentPtr @ 0x723c90` returns base + idx*6
- WRoadNetwork @ 0x8b5df0
- World origin defaults: DAT_008a2fb4 / DAT_008a2fb8 / DAT_008a2fbc

## AI path follower state (~0x40 bytes)
```
+0x10 : current pos (3×float)
+0x1c : current segment idx
+0x20 : target pos (3×float)
+0x2c : active flag (byte)
+0x30 : velocity vec (3×float)
+0x3c : speed magnitude
```

## Anchor functions
- `LoadGlobalAssetsBlocking_GLOBALA @ 0x662b30` — synchronous boot-time `GLOBAL\GLOBALA.BUN` load
- `NextRegionTransition @ 0x666390` — region-graph walk; called at top of DispatchRegionLoaderHandler loop
- `ProbeRegionContainsKey @ 0x6661d0` — sentinel `-0x64ca01c6` indicates miss/exit
- `ResetAIPathFollowerState @ 0x409e60` — clears follower state
- `CreateAIActionRace @ 0x43b800` / `CreateAIActionStaticRoadBlock @ 0x43be50` — AI behaviors that pull the spline-curve cache for traversal
- `CreateAIActionRam @ 0x43ba28` / `UpdateAIActionRam @ 0x43bb28` — cop ramming (ties damage system to AI)

## Speed traps + checkpoints
- `NotifyCheckpointReached_Impl @ 0x6117f0` (mission-event by racer index)
- `NotifySpeedTrapTriggered_Impl @ 0x60a7b0` (event hash 0x822179d1)
- `EnterEngagableTrigger_Impl @ 0x604f80` — allocates 0xc-byte trigger context

**Why:** If you want to add a new track or city region, this is your entry-point map. Adding cars to a track requires adjusting the AI path table + spline cache, not touching pvehicle.

**How to apply:** Region streaming is bundle-keyed — the bundle hash (bChunk = Jenkins mix3) of the region name has to match. The `DispatchRegionLoaderHandler` recipe: hash region name → look up in InGame/Track key tables → `OpenAssetBundleStream` → wait on completion.
