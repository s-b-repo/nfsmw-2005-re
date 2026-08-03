---
name: NFSMW asset streamer anchors (BUN/LZC)
description: Central asset-bundle stream API, the load-and-bind convenience wrapper, and the active-stream linked list anchors
type: project
originSessionId: c4edf485-e85f-4e2f-ac31-e021ba66e8d6
---
The asset streamer in `speed.exe` is built around a small, central API that opens BUN/LZC bundles and registers their load callbacks. Higher-level loaders are blocking spinners that wait on a pair of pending counters.

**Central API (all already named in the binary):**
```
OpenAssetBundleStream(path, mode, prio, ?, ?)    0x0065fd30
  pops a node from `asset_stream_node_pool @ 0x00925878`
  ConstructAssetBundleStream(node, path, mode, prio, ?, ?)
  splices into circular list:
    `asset_stream_list_head_sentinel @ 0x009259a4`
    `asset_stream_list_tail          @ 0x009259a8`

BindBundleLoadCallback(stream, cb, arg)          (already named)
QueryAssetSizeByHash(name)                       (already named)
LoadAttributeBundle(buf, "db", ...)              (already named)
CalculateAssetNameHash(name)                     (already named)
InsertAssetNameIntoCache(hash)                   (already named)

OpenAssetBundleAndBindCallback(path, mode, prio, cb, arg, ?, ?)   0x00661760
  thin wrapper: OpenAssetBundleStream(...) + BindBundleLoadCallback(...).
  Use this convenience as the canonical "load asynchronously" call.
```

**Boot-time blocking loaders** (spin until counters drain):
```
LoadGlobalAssets_GLOBALA_Blocking   0x00662b30
  OpenAssetBundleStream("GLOBAL\\GLOBALA.BUN", 1, 0, 0, 0)
  spin while (asset_load_pending_count_a || asset_load_pending_count_b)

LoadFrontendBootAssets              0x00664780
  loads MemoryFile, attributes.bin (VPAK "db"), GLOBALB.LZC,
  CARS\\BRAKES\\GEOMETRY.BIN, CARS\\BRAKES\\TEXTURES.BIN,
  then spins for completion.

UI_LoadDynamicAssetByContext        0x00662b80
  asset name fetched from `GetGlobalUIRootContext()`-derived string;
  stream stored at UI_root[+0x20], flags=0x2007, hash at [+0x24].
```

**State-machine entry points (already named):**
```
StateBeginGameFlowLoadTrack         calls TRACKS\\STREAM%s.BUN format
StateLoadingFrontEnd                FRONTB.LZC, FRONTA.BUN
DispatchRegionLoaderHandler         INGAMEB.LZC + several region BUNs
```

**Pending-load counters** — both must read 0 before a blocking loader returns:
- `asset_load_pending_count_a @ 0x00925858`
- `asset_load_pending_count_b @ 0x0092585c`

**Why:** This map shows the streamer's seam: every load goes through `OpenAssetBundleStream` (or its convenience wrapper). To trace what gets loaded for a specific asset, get xrefs to those two functions and read the path string at the call site.

**How to apply:**
- For "what triggers loading X": grep xrefs of `OpenAssetBundleStream` and `OpenAssetBundleAndBindCallback`, then read the path string passed at each callsite.
- For "is the load done?": check `asset_load_pending_count_a/b` post-issue.
- For per-asset hashing: the path is hashed via `CalculateAssetNameHash` (uses Jenkins mix3, seed 0xABCDEF00 — see `project_bchunk_hash.md`).
- The streamer's actual chunk-reader / LZC decompressor sits below `ConstructAssetBundleStream` and below `BindBundleLoadCallback`; those are the next functions to chase if needed.
