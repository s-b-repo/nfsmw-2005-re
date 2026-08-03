---
name: allocator + pool architecture
description: NFSMW heap is hierarchical — main heap → 16 sub-pool arenas → named slot pools (CreateObjectPool). Block header is 0x14 bytes with magic 0x22.
type: project
originSessionId: c4edf485-e85f-4e2f-ac31-e021ba66e8d6
---
## Layers

| Layer | Function | Purpose |
|-------|----------|---------|
| top   | Heap_AllocWithArenaRouting @ 0x4653d0 | main heap; routes by size/flags into arena |
| top   | Heap_FreeBlock @ 0x4655f0             | dual-linked free with magic 0x22 |
| mid   | Heap_InitializeArenaGlobals @ 0x4652a0 | early-boot bootstrap |
| mid   | Arena_QueryLargestFreeBlock @ 0x464080 | scan sub-pool free list |
| pool  | CreateObjectPool @ 0x4662e0           | factory for named slot pools (53 callers) |
| pool  | Pool_PopBlock @ 0x465340              | pop with auto-expand |
| pool  | Pool_AllocateBlockWithHeader @ 0x465d80 | wraps arena sub-pool alloc |
| pool  | Pool_ReturnBlockToFreeList @ 0x4650a0 | doubly-linked free list link |
| pool  | Pool_ExpandIfAutoExpandFlagSet @ 0x465de0 |
| pool  | Pool_InitializeHeader @ 0x4f5170      | sets elem-size/count/name after alloc |
| arena | SubPool_DestroyMaybeFreeArena @ 0x464e10 |
| arena | AudioMixerArena_Allocate @ 0x4ac040   | dedicated audio sub-arena (5.6MB) |
| meta  | DeferredFreeQueue_Process @ 0x6626b0  | drains pending frees during ticks |
| meta  | DeferredFreeQueue_AddSize @ 0x627420  | tracks pending bytes (DAT_00920394) |
| meta  | Heap_SampledAllocationCallback @ 0x465110 | debug profiler hook |

## Block header (0x14 bytes preceding user_ptr)

```
[user_ptr - 0x14] : prev_block_ptr
[user_ptr - 0x10] : next_block_ptr
[user_ptr - 0x0C] : pool_index (byte)
[user_ptr - 0x0B] : magic = 0x22
[user_ptr - 0x0A] : alignment_shift (ushort)
[user_ptr - 0x08] : original_size (uint)
```

## Inventory of named pools (CreateObjectPool callers)

- **Particle**: ParticleSlotPool 0x70×1024 / EmitterSlotPool 0x90×500 / EmitterGroupSlotPool 0x80×200
- **Vehicle/AI**: AIVehicleSlotPool 0x14×3072 / AIVehiclePool 0x54×16 / VehicleDamagePartSlotPool 0x70×240 / VehiclePartDamageZoneSlotPool 0x18×100
- **Animation**: NFSAnimBank, AnimCtrl, AnimPart, AnimSkeleton, WorldAnimInstanceEntry, WorldAnimCtrl, WorldAnimEntityTreeInfo, WorldAnimEntity
- **Render**: FERenderEPoly + Overflow / FERenderObject / eStrip / eAnimTexture / ShadowMapMesh / TexturePack / eLightMaterialPlatInfo / Ecstacy:Model / vertexBufferHeader / textureHeader / FEngMemoryPool
- **Audio**: AudioMemory / AUD:Csis / Turbo Spool / Speech Event / Speech Cache / VoiceActors
- **Streaming**: ResourceFile / QueuedFile / OpenDisculatorFile / CeStreamingPack
- **Game logic**: SkidSet / Clan / EventHandler / Event / bPNode
- **Misc**: EAGL4Anim Memory / EAGL4::SymbolPool::mpSymbolTable / LanguageMemoryPool

**Why:** Every pool you find is an inventory hint — total memory footprint = pool_count × slot_size × max_count. Audio dominates. Knowing this lets you predict OOM scenarios when a track has too many of one entity type.

**How to apply:** When debugging memory issues, use Pool_PopBlock callsite to identify which pool ran dry; the deferred-free queue smoothes spikes but won't help if pool max_count is exceeded.
