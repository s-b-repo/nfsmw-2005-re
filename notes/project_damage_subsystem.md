---
name: damage + collision subsystem
description: Damage is data-driven via mission flags keyed by vehicle + part hash; per-vehicle damage classes (DamageRacer/DamageCopCar) instantiated via Vehicle_DamageInitConstructor @ 0x6b9920; cop ramming feeds DamageMultiplier × ImpactSpeed^2.
type: project
originSessionId: c4edf485-e85f-4e2f-ac31-e021ba66e8d6
---
## Class hierarchy
- **DamageVehicle** (base) — string @ 0x8ad648
- **DamageRacer** (subclass) — @ 0x8adda0
- **DamageCopCar** (subclass) — @ 0x8addb8
- Configuration root: `damagespecs` data string @ 0x8add38

## Per-vehicle init
`Vehicle_DamageInitConstructor @ 0x6b9920` (THISCALL): registers DamageVehicle ptr at this+0x4c, plus 5 damage-event slots at +0x50/+0x54/+0x58/+0x5c/+0x60.

## Damage state struct (vehicle + offsets)
```
+0x100 : DAMAGE0_FRONT      flag ptr
+0x104 : DAMAGE0_FRONTLEFT  flag ptr
+0x108 : DAMAGE0_FRONTRIGHT flag ptr
+0x10C : DAMAGE0_REAR       flag ptr
+0x110 : DAMAGE0_REARLEFT   flag ptr
+0x114 : DAMAGE0_REARRIGHT  flag ptr
+0x168 : DECAL_LEFT_DOOR_RECT_MEDIUM
+0x16C : DECAL_RIGHT_DOOR_*
+0x170 : DECAL_LEFT_QUARTER_*
+0x174 : DECAL_RIGHT_QUARTER_*
```

Flags are stored via `Damage_StoreVehiclePartFlags @ 0x756e90` into mission-flag table at root `DAT_009b26a8`.

Per-part deformation meshes are looked up via `bChunk("KIT%02d_DAMAGE0_<part>")` → mission flag → mesh blend amount.

## Pools
`Damage_InitializePartZonePools @ 0x73eb20` creates two pools:
- `VehicleDamagePartSlotPool` (0x70 × 240 instances) at DAT_009b0a78
- `VehiclePartDamageZoneSlotPool` (0x18 × 100 instances) at DAT_009b0a7c

## Events / message hashes
- `MNotifyEngineBlown` @ 0x8a6b24 — `GetMessageHashEngineBlown @ 0x621a2a` returns the cached hash
- `EEngineBlown` @ 0x8a6b54 — event flag for engine destroyed
- `ETireBlown` @ 0x8a7664 — tire burst (links to CARFX_BLOWN_TIRE particle)
- Script-exposed: `BlowEngine` / `SabotageEngine` (registered at 0x61a470 — see RegisterScriptNativesGameplay)

## Cop ramming (collision → damage)
- `CreateAIActionRam @ 0x43ba28`
- `UpdateAIActionRam @ 0x43bb28` — applies `DamageMultiplier × ImpactSpeed^2` (constants TBD)
- `AIActionTooDamaged` @ 0x892c00 — state flag; AI skips actions when damage above threshold

## Configuration
`GetDamageParamsHash @ 0x668850` — Jenkins-mix3 of "DamageParams"; seeds the data-driven damage-type table.

**Why:** Damage is mostly data-driven (mission flags + attribute lookups). Tuning car-specific damage doesn't require code changes — change the attribute table.

**How to apply:** When investigating a damage scenario, the chain is: collision detect → damage event hash → mission flag store at vehicle+offset → render-time mesh deformation. For cop-RAM-specific behavior, look at UpdateAIActionRam, not the generic damage path.

**Open question** (high-leverage next step): the per-frame contact-resolution function lives in a vt slot of the pvehicle sub-physics object; not yet pinned. Likely vt[+0x3c]..vt[+0x44] of the 0x8ab6a0 sub-physics vtable.
