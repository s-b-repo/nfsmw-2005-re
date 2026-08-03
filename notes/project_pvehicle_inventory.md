---
name: pvehicle class hierarchy inventory
description: Inline RTTI string list at speed.exe!0x008add1c enumerates every pvehicle subclass and component-key in NFSMW
type: project
originSessionId: c4edf485-e85f-4e2f-ac31-e021ba66e8d6
---
At `speed.exe!0x008add1c` (just past the 24-method `vtbl_pvehicle_ComponentList` at `0x008adcc0`) is an inline RTTI/identity inventory that lists every class and component-key in the pvehicle universe. Useful as a wordlist for cracking attribute hashes via `BChunkHash_JenkinsMix3` (Jenkins mix3, seed `0xABCDEF00`).

**Strings present (each null-terminated, contiguous, 0x008add1c..0x008ade94):**

```
pvehicle             chopperspecs       damagespecs       rigidbodyspecs
RBVehicle            RBTrailer          RBCop             EffectsVehicle
EffectsCar           EffectsFragment    DamageRacer       DamageHeli
DamageCopCar         SuspensionTraffic  SuspensionTrailer EngineRacer
EngineTraffic        SimpleChopper      DrawHeli          DrawTraffic
DrawNISCar           DrawCopCar         Draw              RaceCar
SoundTraffic         SoundCop           SoundRacer        SoundHeli
SpikeStrip
```

The list ends at `SpikeStrip` (terminator at ~0x8ade94); `NFS Most Wanted` and language names follow as a separate localization table.

**Why:** The pvehicle = "physics vehicle" entity is the central NFSMW driveable. The class identity tag is `pvehicle`; concrete bodies are `RBVehicle / RBTrailer / RBCop`; the rest are component-keys for damage submodels, suspension/engine variants, draw submodels, and effects overlays. EAGL stores the tag list inline after the vtable so the runtime reflection system can walk it without a separate string table.

**How to apply:**
- When reversing a function that takes a 32-bit hash via `LookupAttributeByHash` or `LookupTypeRegistryEntry`, hash these strings (and lowercase/uppercase/title variants) before going hash-cracking elsewhere.
- The pvehicle vtable (24 methods at `0x008adcc0` -> `0x6Bxxxx`) is component-list management (add/remove/iterate/destroy children), not the per-frame Step. Per-frame Step is somewhere else — likely registered via the engine's component-update bus, not via this vtable.
- The RB factory `RigidBody_AllocAndInitFromAttributes (0x6895a0)` is a pvehicle-spawn-time path: a pvehicle is created → it requests a RigidBody → factory builds it via `CreateRigidBodyComponent (0x688660)`, which then registers the SmackTrigger / AIParams / VehicleParamsCluster sub-components.
