# NFSMW Attribute Database

The full reference for the 345 gameplay attributes in `attributes.bin` — every cracked name, organized by type and semantic domain.

- **Total attributes:** 345 rows
- **Cracked:** 294 (85.2%)
- **Uncracked:** 51 (14.8%)
- **Verified:** every crack confirmed by re-hashing with bChunk — zero false positives
- **Source of truth:** `docs/attribute_cracks_verified.json` (294 entries) + `docs/attrib_table.json` (type per hash)

---

## 1. Overview

### File layout

`/extracted/app/GLOBAL/attributes.bin` is a VPAK (689,728 bytes). Starting at file offset `0x18000`, each 16-byte row defines one attribute slot:

```
[+0x00..+0x03]  u32  attribute_name_hash   (Jenkins mix3, seed 0xABCDEF00)
[+0x04..+0x07]  u32  type_hash             (EA::Reflection::* / Attrib::*)
[+0x08..+0x09]  u16  ?
[+0x0a..+0x0b]  u16  ?
[+0x0c..+0x0d]  u16  ?
[+0x0e..+0x0f]  u16  type_flags
```

### The bChunk hash

The hash function the game calls "bChunk" is **Bob Jenkins 1996 mix3** with seed `0xABCDEF00`. Worked example: `bChunk("BASE") = 0xA6B47FAC`. See `memory/project_bchunk_hash.md` for the full implementation. Every name in this database was verified by recomputing `bChunk(name)` and matching to the hash row in `attributes.bin`.

### Type-self-references

A handful of entries in `attributes.bin` are not attribute names but the type-hashes themselves used as data values (e.g. `0x3C16EC5E` = the Float type hash). These are listed in `attrib_table.json` "uncracked" buckets but are not real names to crack — they're the reflection system referring to its own types.

---

## 2. Type system — 7 cracked types

EA's reflection system in NFSMW uses 7 typed reflection markers. All cracked:

| Type hash    | Name                          | Count | Cracked | %     |
|--------------|-------------------------------|------:|--------:|------:|
| `0x3C16EC5E` | `EA::Reflection::Float`       |   137 |     120 |  88%  |
| `0xA3F0C234` | `EA::Reflection::Text`        |    39 |      35 |  90%  |
| `0x939992BB` | `EA::Reflection::UInt32`      |    38 |      16 |  42%  |
| `0x064BEC37` | `EA::Reflection::Bool`        |    71 |      64 |  90%  |
| `0x2B936EB7` | `Attrib::RefSpec`             |    38 |      26 |  68%  |
| `0xA502A824` | `Attrib::StringKey`           |    33 |      32 |  97%  |
| `0xDB9D3A16` | `eDRIVE_BY_TYPE`              |     5 |       1 |  20%  |
| **Total**    |                               | **345** | **294** | **85.2%** |

### Other reflection types referenced as values (not used as row types)

| Hash         | Name                              |
|--------------|-----------------------------------|
| `0x5763DA41` | `EA::Reflection::Int32`           |
| `0x6F27B5BC` | `EA::Reflection::Int8`            |
| `0x671ECBE2` | `EA::Reflection::UInt8`           |
| `0xE51A99C1` | `EA::Reflection::UInt16`          |
| `0x34FDE6BB` | `Attrib::Types::Vector4`          |
| `0xA1E54784` | `Attrib::Types::Matrix`           |
| `0xD680287D` | `Attrib::Types::Vector3`          |

### Two still-uncracked candidate type hashes

| Hash         | Notes                              |
|--------------|------------------------------------|
| `0x349D3A16` | likely a variant of `eDRIVE_BY_TYPE` |
| `0x934A36EC` | unknown                              |

---

## 3. Cross-reference tables — all 294 cracked names by type

### 3.1 RefSpec — vehicle subsystem references (26 of 38)

RefSpec attributes hold a 16-bit class-id + 16-bit instance-key, pointing at another row in the same database. These are the major data-driven subsystem references — the complete vehicle data model.

#### Vehicle core (powertrain / chassis)

| Hash         | Name              | Notes                                            |
|--------------|-------------------|--------------------------------------------------|
| `0xF1F5FBC7` | `engine`          | Engine spec record                               |
| `0x07A7A3E5` | `transmission`    | Gearbox spec                                     |
| `0xFF77F451` | `acceltrans`      | Acceleration transmission curve                  |
| `0x36350867` | `brakes`          | Brake spec                                       |
| `0xBD38D1CA` | `tires`           | Tire spec                                        |
| `0xB1669F64` | `nos`             | Nitrous oxide spec                               |
| `0xC92A0142` | `induction`       | Forced-induction spec                            |
| `0xAFA210F0` | `chassis`         | Chassis spec                                     |
| `0x7C90BB38` | `rigidbodyspecs`  | Physics body parameters                          |
| `0xC1F0B434` | `damagespecs`     | Damage model spec                                |
| `0x50EAB0E6` | `engineaudio`     | Engine audio bank                                |
| `0x171737E9` | `junkman`         | Junkman performance-tuning meta-tier             |

#### Special vehicle types

| Hash         | Name              | Notes                                            |
|--------------|-------------------|--------------------------------------------------|
| `0x5D898EE7` | `chopperspecs`    | Helicopter spec (heat-7 pursuit chopper)         |
| `0x9A5537FE` | `Trailer`         | Truck trailer reference                          |
| `0x22515733` | `aivehicle`       | AI-only vehicle profile                          |
| `0x85885722` | `frontend`        | Front-end / preview vehicle                      |

#### Effects / particle / misc

| Hash         | Name                  | Notes                                          |
|--------------|-----------------------|------------------------------------------------|
| `0xABA86E60` | `emittergroup`        | Particle emitter group reference               |
| `0x5497A394` | `BaseMaterial`        | Material reference                             |
| `0x20EF09CE` | `AudioFX_DEFAULT`     | Default audio effect bank                      |
| `0xD42E792F` | `OnTireBlow`          | Tire-blow trigger handler                      |
| `0x2283ECAF` | `racetable`           | Race-table reference                           |
| `0xD4B0CC11` | `heattable`           | Heat-level table                               |
| `0xE5332008` | `supportracetable`    | Support race table                             |
| `0xF3918F68` | `supporttable`        | Support table                                  |
| `0x93FD9FDA` | `gameplayvault`       | Gameplay vault root reference                  |
| `0xD5F4EDA2` | `tmx_playthings`      | TMX playthings table                           |

**Uncracked RefSpecs (12):** `0xE4983A7D` (`emitteruv`), `0xB0D98A89` (`NGEmitter`), `0x4C64ED7B`, `0x53DE9F00`, `0x74EF4FC8`, `0x7BC5F444`, `0xE82F96CF`, plus 5 type-self-ref placeholders (`0x064BEC37`, `0xD680287D`, `0x671ECBE2`).

> NOTE: `emitteruv` and `NGEmitter` are present in `attribute_cracks_verified.json` but listed under uncracked in attrib_table.json — they were cracked in wave-7 and have type RefSpec.

---

### 3.2 StringKey — Attrib::StringKey (32 of 33)

StringKey attributes hold a name-hash that refers into a string registry. Used for behavior selectors and small enumerations.

#### Behavior-mechanic registry (9 keys defining vehicle component types)

These match the inline RTTI pvehicle inventory at `0x008add1c`.

| Hash         | Name                                |
|--------------|-------------------------------------|
| `0x511ABD7B` | `BEHAVIOR_MECHANIC_SUSPENSION`      |
| `0x59C2BEB1` | `BEHAVIOR_MECHANIC_EFFECTS`         |
| `0x8013456F` | `BEHAVIOR_MECHANIC_RESET`           |
| `0x858ED6E3` | `BEHAVIOR_MECHANIC_DAMAGE`          |
| `0x8BA55001` | `BEHAVIOR_MECHANIC_RIGIDBODY`       |
| `0xA3E13328` | `BEHAVIOR_MECHANIC_ENGINE`          |
| `0xB230ADE1` | `BEHAVIOR_MECHANIC_DRAW`            |
| `0xC3FA0CC4` | `BEHAVIOR_MECHANIC_INPUT`           |
| `0xFB0B5BE9` | `BEHAVIOR_MECHANIC_AUDIO`           |

#### Identity / classification

| Hash         | Name             | Notes                                       |
|--------------|------------------|---------------------------------------------|
| `0x9047C9E0` | `MODEL`          | Model name (geometry asset key)             |
| `0x0EF6DDF2` | `CLASS`          | Class name                                  |
| `0x09925106` | `DESCRIPTION`    | Human description                           |
| `0x104E9D16` | `BEHAVIOR_ORDER` | Behavior ordering hint                      |
| `0xDA5F19F9` | `BEHAVIORS`      | Child-component list (paired with `SimplePhysics` Bool) |

#### Collision / physics tags

| Hash         | Name                     | Notes                              |
|--------------|--------------------------|------------------------------------|
| `0x4F0FDF2D` | `StitchCollisionVol`     | Stitch-collision volume key        |
| `0xD1D3458F` | `STICH_COLLISION_TYPE`   | (sic — "stich") Stitch collision type |

#### Audio bank references

| Hash         | Name                    | Notes                              |
|--------------|-------------------------|------------------------------------|
| `0xBF49A7D9` | `BankName`              | Audio bank id                      |
| `0x04935EAB` | `BankName_auxRAM`       | Aux-RAM audio bank id              |
| `0x2FC9C96F` | `BankName_mainRAM`      | Main-RAM audio bank id             |
| `0xEE501C6A` | `SweetBank`             | "Sweet bank" (sweet-spot audio)    |
| `0x2CEE0A54` | `Filename_GinsuAccel`   | Ginsu-accel audio filename         |
| `0x3A7C2F3D` | `Filename_GinsuDecel`   | Ginsu-decel audio filename         |
| `0x5739788B` | `start_sequencer`       | Audio sequencer start key          |

#### Mission / sequencer

| Hash         | Name                          | Notes                                |
|--------------|-------------------------------|--------------------------------------|
| `0x5AAB860F` | `EventSequencer`              | Event sequencer reference            |
| `0x9DF683FB` | `CHAIN_NEXT_MISSION_NAME`     | Next mission in chain                |
| `0x375AED88` | `SPLITMISSION_PREVHALF`       | Previous half of split mission       |
| `0xE05DEC39` | `SPLITMISSION_NEXTHALF`       | Next half of split mission           |

#### Misc keys

| Hash         | Name              | Notes                                       |
|--------------|-------------------|---------------------------------------------|
| `0x1C778E02` | `AIC_BOND_RGADGET`| AI-control bond — right gadget               |
| `0x73824203` | `AIC_BOND_LGADGET`| AI-control bond — left gadget                |
| `0x84DA8EF1` | `WORLD_TYPE`      | World/region type                            |
| `0x968E5680` | `PED_OBJECTS`     | Pedestrian object set                        |
| `0xB7606A9A` | `TRAFFIC_TYPES`   | Traffic vehicle types                        |
| `0xBEC30F42` | `CSIS_EFFECT`     | CSIS effect key                              |

**Uncracked StringKeys (1):** `0x34FDE6BB` (this is the Vector4 type-self-ref, not a real name).

---

### 3.3 Float — EA::Reflection::Float (120 of 137)

Floats hold a single IEEE-754 32-bit value. They drive every tunable knob in the game — physics, AI weights, particle params, camera angles, race rules.

#### A. Vehicle physics / handling

| Hash         | Name                  | Notes                                       |
|--------------|-----------------------|---------------------------------------------|
| `0x4A56503D` | `MASS`                | Rigid-body mass (kg)                        |
| `0xFEF5CC35` | `STEERING`            | Steering response                           |
| `0x7F8EEA1A` | `STIFFNESS`           | Suspension stiffness                        |
| `0x4CB36381` | `AxlePair`            | Front/rear axle pair index                  |
| `0x96E40580` | `Power`               | Engine power output                         |
| `0xB5C0DAC8` | `AUTO_SIMPLIFY`       | `Smackable::mAutoSimplify` LOD-cull threshold |
| `0x64C43C4B` | `YAW_CONTROL`         | Yaw control gain                            |
| `0xC2094707` | `YAW_SPEED`           | Yaw rate                                    |
| `0x6659143B` | `MaybeV8`             | (Suspect name) V8-related multiplier        |
| `0xBE71DBAD` | `DETACH_FORCE`        | Force needed to detach a smackable          |
| `0x0099CB26` | `InheritVelocity`     | Velocity-inheritance fraction               |
| `0x2FC5F041` | `LATOFFSET`           | Lateral offset                              |
| `0x0802DD99` | `GravityDelta`        | Gravity delta                               |
| `0xE652E2B6` | `GravityStart`        | Gravity start value                         |
| `0xE0D01505` | `StartPercent`        | Start percentage                            |
| `0x259021B6` | `explosionForceLimit` | Force ceiling on explosions                 |
| `0x3A5970F4` | `forceMultiplier`     | Damage/impact force multiplier              |
| `0xA6F789CB` | `damageMultiplier`    | Damage scalar                               |
| `0xA6F45864` | `triggerThreshold`    | Trigger threshold                           |
| `0x4E90219D` | `ThreshholdValue`     | Threshold value (sic)                       |
| `0xC3710777` | `ThreshholdSpeed`     | Speed threshold (sic)                       |
| `0xCD41CD40` | `ObligatesDrift`      | Drift obligation factor                     |

#### B. Engine audio / RPM curves (Ginsu / AEMS)

| Hash         | Name                       | Notes                                  |
|--------------|----------------------------|----------------------------------------|
| `0x014D605F` | `AEMSMix_L_RPM`            | AEMS large-RPM mix point               |
| `0xA4A699B0` | `AEMSMix_S_RPM`            | AEMS small-RPM mix point               |
| `0x974EB50A` | `AEMSVol`                  | AEMS volume                            |
| `0x0F7C0093` | `DECEL_AEMSVol`            | Decel AEMS volume                      |
| `0x3C9445E9` | `DECEL_AEMSMix_S_RPM`      | Decel AEMS small mix                   |
| `0x8C22DF44` | `DECEL_AEMSMix_L_RPM`      | Decel AEMS large mix                   |
| `0xC2F38240` | `GINSUMix_S_RPM`           | Ginsu small RPM mix                    |
| `0xD996FD76` | `GINSUMix_L_RPM`           | Ginsu large RPM mix                    |
| `0x4FE476F3` | `DECEL_GINSUMix_L_RPM`     | Decel Ginsu large mix                  |
| `0x791768A0` | `DECEL_GINSUMix_S_RPM`     | Decel Ginsu small mix                  |
| `0x38AFE02E` | `Ginsu_ACL_Neg_S_RPM`      | Ginsu accel-negative small RPM         |
| `0x782F433D` | `Ginsu_ACL_Neg_L_RPM`      | Ginsu accel-negative large RPM         |
| `0x38BE973D` | `GinsuDecelVol`            | Ginsu decel volume                     |
| `0xC3F787B1` | `GINSUAccelVol`            | Ginsu accel volume                     |
| `0x18B901F4` | `GINSU_DECEL_FADE_OUT`     | Decel fade-out                         |
| `0x56BA0258` | `GINSU_DECEL_FADE_IN`      | Decel fade-in                          |
| `0x414946CC` | `GINSU_Decel_MaxRPM`       | Decel max RPM                          |
| `0xD1B4E1B2` | `GINSU_Decel_MinRPM`       | Decel min RPM                          |
| `0xE3836473` | `GINSU_LowPassCutoff`      | Low-pass cutoff                        |
| `0x313385DC` | `DecelPitchOffset`         | Decel pitch offset                     |
| `0x3B82C385` | `AccelDeltaRPMThreshold`   | Accel delta-RPM threshold              |
| `0x6114D1A5` | `DecelDeltaRPMThreshold`   | Decel delta-RPM threshold              |
| `0x3AC8B868` | `MinRPM`                   | Engine min RPM                         |
| `0xA4D878EF` | `MaxRPM`                   | Engine max RPM                         |

#### C. AI / pursuit / catch-up

| Hash         | Name                  | Notes                                  |
|--------------|-----------------------|----------------------------------------|
| `0x4545AB74` | `CatchUpIntegral`     | Rubber-band integral term              |
| `0x515AA4E4` | `CatchUpDerivative`   | Rubber-band derivative term            |
| `0x8069B5A9` | `CatchUpSkill`        | (Listed as Text in some sources)       |
| `0x9EB17C1E` | `CatchUpOverride`     | Override catch-up                      |
| `0xA18A07BA` | `CatchUpSpread`       | (Listed as Text)                       |
| `0xF5A03629` | `MaxHeatLevel`        | Pursuit heat ceiling                   |
| `0xE4E4BC48` | `MinimumSupportDelay` | Support-cop spawn delay                |
| `0x06885323` | `LeaderSupport`       | Leader support weight                  |
| `0x16FABA11` | `ShortcutMaxChance`   | AI shortcut max probability            |
| `0x4EFB950A` | `ShortcutMinChance`   | AI shortcut min probability            |
| `0xFCAA46E2` | `CopCountRecord`      | Cop count record                       |
| `0xA9598843` | `Priority`            | Generic priority                       |

#### D. Race rules / mode / scoring

| Hash         | Name                  | Notes                                  |
|--------------|-----------------------|----------------------------------------|
| `0x7C11C52E` | `RaceLength`          | Total race length                      |
| `0x7585F041` | `TimeLimit`           | Race time limit                        |
| `0x777ECE27` | `KnockoutTime`        | Knockout-mode timing                   |
| `0x0A91596D` | `InitialSpeed`        | Race-start speed                       |
| `0x3A0E4B19` | `InitialPlayerSpeed`  | Player race-start speed                |
| `0xC516E9C2` | `RingTime`            | Ring/checkpoint time                   |
| `0x2C44FF10` | `ResetTime`           | Reset/respawn time                     |
| `0x5F84F834` | `RESPAWN_TIME`        | Respawn time                           |
| `0x839602AB` | `StartTime`           | Start time                             |
| `0x20259346` | `DelayTime`           | Delay before action                    |
| `0xBF2FDB5C` | `SpawnTime`           | Spawn time                             |
| `0x00DF8EB4` | `TargetBronze`        | Bronze target threshold                |
| `0x51CE16B7` | `TargetSilver`        | Silver target threshold                |
| `0x728E43FF` | `TargetGold`          | Gold target threshold                  |
| `0x006EC903` | `GoalAddPrevBest`     | Goal-add previous-best                 |
| `0x8445AF47` | `GoalEasy`            | Easy goal                              |
| `0x3B9BBFC2` | `GoalHard`            | Hard goal                              |
| `0xF9120D73` | `RivalBestTime`       | Rival best time                        |
| `0xAB0179F4` | `CashReward`          | Cash reward                            |
| `0xD8BAA07B` | `CashValue`           | Cash value                             |
| `0xB4985085` | `TopBreak`            | Top-tier break point                   |
| `0x547486AE` | `ChanceOfRain`        | Weather probability                    |
| `0xAACBE2E7` | `HandlingRating`      | Vehicle handling rating                |
| `0xFB42C0B9` | `PlayerCarPerformance`| Player car performance rating          |
| `0x4A985286` | `ChargeTime`          | Charge time (NOS / boost)              |
| `0x0D4C1055` | `InternalRaceIndex`   | Internal race index (sequence)         |
| `0x29B9C312` | `car_zprepass_deg_210`| Car z-prepass degree (LOD)             |
| `0x7C44962F` | `SpeedStreet`         | Speed-street rating                    |
| `0x9E404E33` | `SpeedHighway`        | Highway-speed rating                   |

#### E. Particle / effect

| Hash         | Name                       | Notes                                |
|--------------|----------------------------|--------------------------------------|
| `0xDC943CC9` | `NumParticles`             | Particle emit count                  |
| `0xD8165518` | `NumParticlesVariance`     | Particle count randomization         |
| `0x81625B35` | `Life`                     | Particle life                        |
| `0xEFB4BB64` | `LifeVariance`             | Particle life randomization          |
| `0x07C20250` | `Maxscale`                 | Particle max scale                   |
| `0x0FA46807` | `MinScale`                 | Particle min scale                   |
| `0x1A0B5461` | `MinSize`                  | Particle min size                    |
| `0xF7649E63` | `MaxSize`                  | Particle max size                    |
| `0x4C141ED7` | `HeightStart`              | Particle initial height              |
| `0x6BBC13EE` | `LengthStart`              | Particle initial length              |
| `0xA6762035` | `LengthDelta`              | Particle length delta                |
| `0x394ABBC6` | `FlareSpacing`             | Flare spacing                        |
| `0x2F70D78A` | `InScatterMulitply`        | In-scatter multiply (sic)            |
| `0x555FD699` | `BrMultiply`               | Brightness multiply                  |
| `0xC8BAF5D6` | `BmMultiply`               | Bloom multiply                       |
| `0x297CBA80` | `fallOffUnit`              | Falloff unit                         |
| `0x360552DA` | `ExplosionEffect`          | Push-back / snap-back gate (Float)   |
| `0x44F1273B` | `DROPOUT`                  | Timed-decay despawn config (2-elem)  |

#### F. Camera / rendering / post-process

| Hash         | Name                  | Notes                                  |
|--------------|-----------------------|----------------------------------------|
| `0x263E9452` | `FOV`                 | Field of view                          |
| `0x39BF8002` | `Radius`              | Generic radius                         |
| `0x5816C1FC` | `Width`               | Width                                  |
| `0x762B7718` | `HEIGHT`              | Height                                 |
| `0x7D1E620E` | `ANGLE`               | Angle                                  |
| `0x5A6A57C6` | `Rotation`            | Rotation                               |
| `0xDE0857E3` | `LAG`                 | Camera lag                             |
| `0x9DFF3C3D` | `TOD`                 | Time of day                            |
| `0xC5857615` | `distance`            | Distance                               |
| `0x0913F193` | `ColourBloomIntensity`| Bloom intensity (colour)               |
| `0x7E609E04` | `BlackBloomIntensity` | Bloom intensity (black)                |
| `0x107C0F71` | `DetailMapIntensity`  | Detail-map intensity                   |
| `0x771BBE7F` | `Desaturation`        | Desaturation amount                    |
| `0xA02742A6` | `ZBias`               | Z-bias for depth                       |
| `0xDBA22A95` | `FogG`                | Fog green channel                      |
| `0x1A2F2B1B` | `VisualCullDist`      | Visual cull distance                   |
| `0x98DBA438` | `AudioCullDist`       | Audio cull distance                    |
| `0x4037D3C5` | `IconModelFloatHeight`| Icon model float-height                |
| `0x697332E8` | `IconModelSpinRate`   | Icon model spin rate                   |
| `0x98B567DC` | `CONTROLLER_CURVE`    | Controller-response curve              |

#### G. Traffic / world

| Hash         | Name                          | Notes                              |
|--------------|-------------------------------|------------------------------------|
| `0x3F4A4CEC` | `MAX_TRAFFIC_SPAWN_DISTANCE`  | Traffic spawn distance limit       |
| `0x811C6606` | `TRAFFIC_SPEED`               | Ambient traffic speed              |
| `0xB60CB556` | `PED_SPAWN_RADIUS`            | Pedestrian spawn radius            |
| `0xECD3671D` | `REALIZATION_CONTROLLER`      | Realization controller curve       |
| `0xE956E716` | `reflection_amount`           | Reflection amount                  |

#### H. Damage / smackable

| Hash         | Name                  | Notes                                  |
|--------------|-----------------------|----------------------------------------|
| `0xD99B853C` | `DamageScaleRecord`   | Damage scaling record                  |

---

### 3.4 Text — EA::Reflection::Text (35 of 39)

Text attributes hold a hash referring to another row (often by name). Used for cross-record references where the value identifies a sibling row, not an arbitrary string.

#### Identity / naming

| Hash         | Name                  | Notes                              |
|--------------|-----------------------|------------------------------------|
| `0x3E225EC1` | `Name`                | Display name                       |
| `0x704F72E8` | `MilestoneName`       | Milestone display name             |
| `0xBEAB64C5` | `RacerName`           | Racer name                         |
| `0xA78403EC` | `EventID`             | Event identifier                   |
| `0x7148AE82` | `scriptname`          | Script name                        |
| `0x9CA1C8F9` | `CollectionName`      | Collection name                    |

#### Vehicle / car types

| Hash         | Name                  | Notes                              |
|--------------|-----------------------|------------------------------------|
| `0xF833C06F` | `CarType`             | Vehicle type id                    |
| `0xFD3CF790` | `CarTypeLowMem`       | Low-memory car-type variant        |
| `0xC0EEB909` | `PlayerCarType`       | Player vehicle reference           |
| `0xAA27E71C` | `DefaultPresetRide`   | Default preset-ride reference      |
| `0x416A8409` | `PresetRide`          | Preset-ride reference              |
| `0xD686D61E` | `CopSpawnType`        | Cop spawn template                 |
| `0x6319B692` | `TrafficPattern`      | Traffic pattern reference          |

#### Race-mode / event configuration

| Hash         | Name                  | Notes                              |
|--------------|-----------------------|------------------------------------|
| `0x13B11B40` | `RoadList`            | Road list reference                |
| `0x062DFC259`*| `FinishCamera`       | Finish-line camera                 |
| `0x62DFC259` | `FinishCamera`        | Finish-line camera                 |
| `0xCBD7ADF9` | `SpeedTrapCamera`     | Speed-trap camera                  |
| `0x06A077D5` | `RewardMarkerType`    | Reward marker type                 |
| `0x0F6BCDE1` | `EventIconType`       | Event icon type                    |
| `0x3C2FDAAB` | `UpgradePartID`       | Upgrade part identifier            |
| `0x0E0113FE` | `UpgradeType`         | Upgrade type                       |
| `0xA62CB4F0` | `IconModelName`       | Icon model name                    |

#### Region / barriers / zones

| Hash         | Name                  | Notes                              |
|--------------|-----------------------|------------------------------------|
| `0xCB01E454` | `Region`              | Region reference                   |
| `0xE244F26B` | `Barriers`            | Barriers reference                 |
| `0xF3EA3201` | `ZoneType`            | Zone type                          |

#### Mission / NIS / movies

| Hash         | Name                  | Notes                              |
|--------------|-----------------------|------------------------------------|
| `0xDEC18D3E` | `IntroNIS`            | Intro NIS sequence                 |
| `0x54932966` | `OutroNIS`            | Outro NIS sequence                 |
| `0x5987FB25` | `QuickRaceNIS`        | Quick-race NIS                     |
| `0xF572EDE8` | `IntroMovie`          | Intro movie                        |
| `0xB70268C0` | `OutroMovie`          | Outro movie                        |

#### Particle / effect

| Hash         | Name                       | Notes                              |
|--------------|----------------------------|------------------------------------|
| `0x3DFD8048` | `ParticleTextureRecord`    | Particle texture record            |
| `0x5EF34802` | `ParticleEffect`           | Particle effect reference          |

#### Misc

| Hash         | Name                  | Notes                              |
|--------------|-----------------------|------------------------------------|
| `0xF093AACF` | `flare_texture`       | Flare texture                      |

**Uncracked Text (4):** `0x038A3B53`, `0xC385F75D`, plus 2 type-self-refs.

---

### 3.5 UInt32 — EA::Reflection::UInt32 (16 of 38)

UInt32 attributes hold raw 32-bit unsigned integers. Used for IDs, counters, and bitmask-like configurations.

| Hash         | Name                  | Notes                              |
|--------------|-----------------------|------------------------------------|
| `0x0C35B607` | `CarID`               | Vehicle identifier                 |
| `0x6DB7D192` | `COST_TO_STATE`       | State-machine transition cost      |
| `0x341F03A0` | `EffectLinkageRecord` | Effect-linkage record id           |
| `0x9E8910EF` | `message_id`          | Network/event message id           |
| `0x0013821F` | `MAX_NEWTONS`         | Max-newtons threshold              |
| `0x113D4C46` | `MAX_FRAGMENTS`       | Max fragments                      |
| `0x68575D35` | `MAX_SMACKABLES`      | Max smackables                     |
| `0xDB9D3A16` | `eDRIVE_BY_TYPE`      | (type hash referenced as value)    |

> Some UInt32 entries in the schema are type-hashes themselves (`0x5763DA41`, `0x6F27B5BC`) rather than attribute names. The 16 cracks above are the real attributes.

**Notable uncracked UInt32 (22):** `0x0C531256`, `0x16D7A0B1`, `0x1C9E97C6`, `0x27D396AC`, `0x3E1A0DB6`, `0x50B23FBC`, `0x560C34CC`, `0x693EBFF3`, `0x748EB252`, `0x823FC1C5`, `0x84D1B9A4`, `0x8818C1FE`, `0xBDCB972F`, `0xD1172BD0`, `0xDA0DFCDE`, `0x0B08309D`, `0x67AF0E6B`, `0xE5F75D11`.

---

### 3.6 Bool — EA::Reflection::Bool (64 of 71)

Bool attributes hold a single-byte flag. Used to gate behaviors and toggle features.

#### Race / event flags

| Hash         | Name                          |
|--------------|-------------------------------|
| `0x2B1F54F6` | `PursuitRace`                 |
| `0x1C650104` | `ChallengeSeriesRace`         |
| `0x1BB16F14` | `OpenWorldSpeedTrap`          |
| `0x4393F69B` | `IsEpicPursuitRace`           |
| `0x637584FE` | `CollectorsEditionRace`       |
| `0x6A9A6F5B` | `IsLoopingRace`               |
| `0x8CB01ABF` | `DDayRace`                    |
| `0xF2FE50D7` | `IsMarkerRace`                |
| `0xFF5EE5D6` | `BossRace`                    |
| `0x79C5D68D` | `IsBoss`                      |
| `0xB809D19C` | `RollingStart`                |
| `0x3E33DA0F` | `DoCountdown`                 |
| `0xEDE6017E` | `DoPhotofinish`               |
| `0x0E34A1F3` | `SharedCheckpoints`           |
| `0x2AD67092` | `CheckpointsVisible`          |
| `0x6CCD5819` | `ResetsPlayer`                |
| `0xAB4A196F` | `ResetWhenPursuitStarts`      |
| `0x6DF0ABFE` | `RandomOpponent`              |
| `0x5EC1880F` | `RankPlayersByPoints`         |
| `0x9E7A18CE` | `RankPlayersByDistance`       |

#### Availability / unlock

| Hash         | Name                          |
|--------------|-------------------------------|
| `0xEA855EAF` | `InitiallyUnlocked`           |
| `0xC4DB4E71` | `QuickRaceUnlocked`           |
| `0x39509746` | `AvailableOnline`             |
| `0xB39ED8C3` | `AvailableQR`                 |
| `0xAA0135E9` | `FreeRoamOnly`                |
| `0xA4E6FCFD` | `NeverInQuickRace`            |
| `0xA1009A23` | `AllowInvisibleSpawn`         |
| `0x40E94F86` | `SELECTABLE`                  |
| `0xF099B6AC` | `PlayerUsable`                |
| `0x45F2AD6C` | `UseWorldHeat`                |

#### Cop / pursuit toggles

| Hash         | Name                          |
|--------------|-------------------------------|
| `0x3918E889` | `CopsInRace`                  |
| `0x0E47FE63` | `ScriptedCopsInRace`          |

#### Behavior / gameplay flags

| Hash         | Name                          |
|--------------|-------------------------------|
| `0x10DB04E6` | `CatchUp`                     |
| `0x6B37E124` | `Directional`                 |
| `0xE4542E9B` | `Persistent`                  |
| `0x83066633` | `Tranny`                      |
| `0x883C65E3` | `AutoStart`                   |
| `0x110882D5` | `FogEnable`                   |
| `0x3E9156CA` | `Template`                    |
| `0x665F4D74` | `TILTING`                     |
| `0xB2AC32C7` | `FireOnExit`                  |
| `0xCE4261AC` | `OneShot`                     |
| `0x0D038CFA` | `FilterModePassAll`           |
| `0x4C17FE41` | `NISShell`                    |
| `0x9652AF0F` | `fecompressionstoggle`        |
| `0x4463A62D` | `TRAFFIC_LANE_CHANGES`        |
| `0xE8A7CCE2` | `CHECK_PLAYER_BEHIND_TRAFFIC` |
| `0xE58865D1` | `SPLITMISSION_CARRYDAMAGE`    |
| `0xD52754DA` | `RACE_SCORING`                |
| `0xFD47CFB6` | `LINEAR_TRACK`                |
| `0x73C58CBF` | `no_trigger`                  |
| `0x73C58CBF` | `no_trigger`                  |
| `0xAEE3BE58` | `doTest`                      |
| `0x1F989F01` | `NO_CAR_EFFECT`               |
| `0x6E4DE905` | `AI_AVOIDABLE`                |
| `0x6F002423` | `IsWooshable`                 |
| `0x7E744600` | `WooshType`                   |
| `0xBEE139F1` | `ALLOW_OFF_WORLD`             |
| `0xE9D83D0C` | `CAMERA_AVOIDABLE`            |
| `0xEE0011E3` | `SimplePhysics`               |
| `0x0896D043` | `MilestoneBiggerIsBetter`     |
| `0xC141F7F8` | `KILL_OFF_SCREEN`             |
| `0xAB4A196F` | `ResetWhenPursuitStarts`      |
| `0xD5C7E9C3` | `AutoSpawnTriggerType`        |

#### Misc

| Hash         | Name                          |
|--------------|-------------------------------|
| `0x0F6BCDE1` | (listed as Text above)        |
| `0x16FABA11` | (listed as Float above)       |

**Uncracked Bool (7):** `0x40F9929F`, `0xEACB7696`, plus a few type-self-refs (`0x3C16EC5E`, `0xE51A99C1`).

---

### 3.7 eDRIVE_BY_TYPE (1 of 5)

Only one named entry — the type-hash itself appears as a value in some rows.

| Hash         | Name                  | Notes                              |
|--------------|-----------------------|------------------------------------|
| `0xDB9D3A16` | `eDRIVE_BY_TYPE`      | The type-hash, used as a value     |

**Uncracked eDRIVE_BY (4):** type self-refs and 1–2 instance names.

---

## 4. The 5 original mystery hashes — all solved

For months, five attribute hashes resisted every wordlist attack. Wave-6 and wave-7 solved all five.

| Hash         | Type      | Final Name        | How it was cracked                                  |
|--------------|-----------|-------------------|-----------------------------------------------------|
| `0xB5C0DAC8` | Float     | `AUTO_SIMPLIFY`   | wave-6 — SDK CamelCase→UPPER_SNAKE conversion: `Smackable::mAutoSimplify` field in `nfsplugin_sdk_mw05/Types/Smackable.h` |
| `0xDA5F19F9` | StringKey | `BEHAVIORS`       | wave-6 — EA-vocab wordlist (250 conventional EA terms) |
| `0xEE0011E3` | Bool      | `SimplePhysics`   | wave-7 — community NFS hash database (`NFSTools/Attribulator` Speed Profiles) |
| `0x360552DA` | Float     | `ExplosionEffect` | wave-7 — community NFS hash database                |
| `0x44F1273B` | Float[2]  | `DROPOUT`         | wave-7 — community NFS hash database                |

### Semantic roles (cross-referenced with Ghidra decompilation)

- **`AUTO_SIMPLIFY`** — `Smackable::mAutoSimplify` const float. Stored at `RB this+0xfc` by `CreateRigidBodyComponent_PhysicsObjectInit @ 0x688660`. Drives LOD/cull simplify threshold. Instance values observed: 2.5, 3.0.

- **`BEHAVIORS`** — StringKey list of child component keys. `CreateRigidBodyComponent` iterates this via `LookupAttributeIteratorByHash` / `GetAttributeIteratorChildCount`; for each child it calls `FUN_00684bb0(this, kind, name)` attaching an `EffectsSmackable` sub-component.

- **`SimplePhysics`** — Smackable construction Bool. `Smackable_Construct @ 0x6895a0` reads it as a byte and pairs it with the "ghost" flag at `puVar3[+0x58]` to pick `FUN_006ed390` (ghost variant) vs `FUN_006ed260` (solid variant). Paired with `BEHAVIORS`: the Bool gates whether the child-effects list applies.

- **`ExplosionEffect`** — Push-back / snap-back gate consumed by `FUN_00677100 @ 0x67713a`. If `*attr > 0`, computes `param_2 - dot(velocity, ref)` and applies a collision-response impulse scaled by inverse-mass via `vt[+0x88]`. Instance values: 0.25, 0.5, 1.0.

- **`DROPOUT`** — Timed continuous force / surge config (2-element). Both `[0]` and `[1]` must be > 0 to pass the gate; `[0]` is stored at `RB+0xf4`, with countdown timer at `+0xf0`. `FUN_0066a0b0` decays the timer each tick and applies `-(dt * attr[1])` via `SimContext vt[+0x7c]`, then kills via `vt[+0x08]` when expired.

### Cross-reference: the `SimplePhysics` ↔ `BEHAVIORS` pairing

In `attributes.bin @ 0x611B0`, the `SimplePhysics` Bool instance row literally embeds the `BEHAVIORS` hash (`0xDA5F19F9`) in its extra-data field. Reading the `Smackable_Construct` flow: the Bool branches ghost-vs-solid AND `CreateRigidBodyComponent` then iterates the `BEHAVIORS` StringKey list of children. So these two attributes implement a paired "has child effects? / what effects?" mechanism for destructible objects.

---

## 5. How to use — find a knob by name

Given any candidate attribute name (e.g. `MASS`):

1. Compute `bChunk(name)` — Jenkins mix3 with seed `0xABCDEF00`. `bChunk("MASS") = 0x4A56503D`.
2. Open `extracted/app/GLOBAL/attributes.bin` and seek to offset `0x18000`.
3. Search for the 4-byte little-endian hash. Each 16-byte row starts with the name-hash.
4. Read `[+0x04..+0x07]` — that's the type-hash. For `MASS` it's `0x3C16EC5E` (Float).
5. Read the flag bytes `[+0x08..+0x0F]` for storage size, default-policy, and class membership.
6. To find instance values, locate the row in the instance section (varies per class) — the per-instance value follows the row pointer.

### Worked example: read MASS for a vehicle

- `bChunk("MASS") = 0x4A56503D` (Float type)
- Find the row in the vehicle's instance section (each `pvehicle` class instance carries a value table)
- The 4 bytes at the instance offset are the actual mass in kg

For per-vehicle data, the value lives inside the vehicle's data section in `attributes.bin` or in the corresponding LZC bundle for the car.

### Cracking script

`/tmp/crack_floats.py` (extract strings from all bundles + speed.exe + DLLs ~6.9M unique strings, generate name variants, hash and match). For wave-7 community-DB integration: `/tmp/crack_v8_community.py`.

---

## 6. Modding: how to edit an attribute

### Option A — NFS-VltEd (recommended for cars / global gameplay tables)

NFS-VltEd is the community standard for editing `GlobalA.bun` / `GlobalB.bun` (which mirror many `attributes.bin` rows). It ships with a name dictionary that covers most cracked attribute names.

1. Open `GlobalB.lzc` (decompressed via `tools/nfsmw_bun_reader/jdlz_nfsmw.py`).
2. Navigate to the desired record (e.g. `Vehicles → BMWM3GTR → MASS`).
3. Edit value, save — the tool re-compresses and writes back.

### Option B — Direct binary patch on `attributes.bin`

For attributes only present in `attributes.bin` (not GlobalA/B):

1. Locate the row by hashing the name with bChunk.
2. Find the instance offset — the row contains a 16-bit class-id and 16-bit instance-key telling you which instance section.
3. Patch the 4-byte float / 1-byte bool / etc. at the instance offset.
4. Since `attributes.bin` is a VPAK with no internal checksum, the patch is portable.

### Option C — Live hot-patch via debugger

1. Hash the name → find the row in `attributes.bin` at runtime.
2. Set a watchpoint on the instance value with `mcp__ghidra__debugger_watch_memory`.
3. When the game reads the value (e.g. `MASS` reads during `CreateRigidBodyComponent_PhysicsObjectInit`), modify it on the fly.

### Risk notes

- Save-game integrity check: `CAREER_DATA` root + `MSG_R_BI_DATACRC` will reject saves if certain career/heat tables are mutated mid-save.
- Replay determinism: changing physics-affecting attributes (`MASS`, `STEERING`, `STIFFNESS`, `Power`) will desync any recorded `Joylog` replay.
- Mismatched type writes (writing a float where a Bool is expected) will silently corrupt — always confirm type via the row's type-hash field first.

---

## 7. The remaining 51 uncracked — by type

These are the 51 still-uncracked attribute hashes. Wave-9 inferred semantic roles for some via use-site analysis.

### Float — 17 uncracked

| Hash         | Inferred role (wave-9 where noted)                          |
|--------------|-------------------------------------------------------------|
| `0x07C20250` | (was Maxscale candidate)                                    |
| `0x419C66C9` | unknown                                                     |
| `0x64E9DC9E` | unknown                                                     |
| `0xED3007A0` | unknown                                                     |
| `0xF1065907` | unknown                                                     |
| `0xFDF3BC20` | unknown                                                     |
| `0x1823B89E` | unknown                                                     |
| `0x8F186AC4` | unknown                                                     |
| `0xA07AE814` | unknown                                                     |
| `0xB1ECE070` | unknown                                                     |
| `0xE10FB7A3` | unknown                                                     |
| `0xE8C24416` | unknown                                                     |
| `0x349D3A16` | type variant of eDRIVE_BY?                                  |
| `0x934A36EC` | unknown                                                     |
| `0xA3F0C234` | type self-ref (Text)                                        |
| `0xA1E54784` | type self-ref (Matrix)                                      |
| `0x939992BB` | type self-ref (UInt32)                                      |

### UInt32 — 18 uncracked

| Hash         | Inferred role                                               |
|--------------|-------------------------------------------------------------|
| `0x0C531256` | unknown                                                     |
| `0x16D7A0B1` | unknown                                                     |
| `0x1C9E97C6` | unknown                                                     |
| `0x27D396AC` | unknown                                                     |
| `0x3E1A0DB6` | unknown                                                     |
| `0x50B23FBC` | unknown                                                     |
| `0x560C34CC` | unknown                                                     |
| `0x693EBFF3` | unknown                                                     |
| `0x748EB252` | unknown                                                     |
| `0x823FC1C5` | unknown                                                     |
| `0x84D1B9A4` | unknown                                                     |
| `0x8818C1FE` | unknown                                                     |
| `0xBDCB972F` | unknown                                                     |
| `0xD1172BD0` | unknown                                                     |
| `0xDA0DFCDE` | unknown                                                     |
| `0x0B08309D` | unknown                                                     |
| `0x67AF0E6B` | unknown                                                     |
| `0xE5F75D11` | unknown                                                     |

### Bool — 6 uncracked

| Hash         | Inferred role                                               |
|--------------|-------------------------------------------------------------|
| `0x40F9929F` | unknown                                                     |
| `0xEACB7696` | unknown                                                     |
| `0x3C16EC5E` | type self-ref (Float)                                       |
| `0xE51A99C1` | type self-ref (UInt16)                                      |

### StringKey — 1 uncracked

`0x34FDE6BB` is the `Attrib::Types::Vector4` type self-ref — not a real attribute name.

### RefSpec — 7 uncracked

| Hash         | Inferred role                                               |
|--------------|-------------------------------------------------------------|
| `0x4C64ED7B` | unknown subsystem ref                                       |
| `0x53DE9F00` | unknown subsystem ref                                       |
| `0x74EF4FC8` | unknown subsystem ref                                       |
| `0x7BC5F444` | unknown subsystem ref                                       |
| `0xE82F96CF` | unknown subsystem ref                                       |
| `0x064BEC37` | type self-ref (Bool)                                        |
| `0xD680287D` | type self-ref (Vector3)                                     |
| `0x671ECBE2` | type self-ref (UInt8)                                       |

### Text — 2 uncracked

| Hash         | Inferred role                                               |
|--------------|-------------------------------------------------------------|
| `0x038A3B53` | unknown                                                     |
| `0xC385F75D` | unknown                                                     |
| `0xA502A824` | type self-ref (StringKey)                                   |

### eDRIVE_BY — 4 uncracked

| Hash         | Inferred role                                               |
|--------------|-------------------------------------------------------------|
| `0x2B936EB7` | type self-ref (RefSpec)                                     |

### Why the last 15% is hard

Wave-6 ran ~150M wordlist combinations across 80,000 unique tokens from decompressed bundles + speed.exe + all 3 NFS SDK headers (MW + Carbon + ProStreet), ~250 EA-conventional vocab terms, every CamelCase / PascalCase / UPPER_SNAKE / camelCase variant, 2-word and 3-word compounds, digit suffixes 1..15, triple-cluster compounds (ATTACK × TIME × FORCE).

Wave-7 added the 3 community repos (43,102 names). +173 cracks.

The remaining 51 likely require:

1. **NFSU2 / Carbon community attribute lists** — most NFS modding tools have these; not available locally
2. **PDB / source leak** — would crack everything instantly
3. **Live runtime tracing** — observe value semantics at each use-site to infer names from behavior

The remaining names are likely:

- Multi-word phrases not in the wordlist (e.g. `RidingHeightFront`, `AmbientShakeFrequency`)
- Internal EA dev terms not exposed in any public material
- Localized / abbreviated forms

---

## Appendix A — All 294 cracks by hash (canonical list)

The authoritative machine-readable list lives at:

```
docs/attribute_cracks_verified.json
```

294 entries, each one re-hashable to its target hash via bChunk. Never edit this file by hand — use the cracker script for additions and the verification routine to confirm.

## Appendix B — Cross-reference to other docs

- `docs/attribute_hashes.md` — original schema registry with wave-by-wave history
- `docs/attrib_table.json` — older snapshot with per-type cracked/uncracked partition
- `docs/attribute_cracking_progress.md` — chronicle of wave attempts
- `docs/wave6_cracks.json` — wave-6 specific crack manifest
- `memory/project_attribute_schema.md` — meta-memory: schema + crack methodology
- `memory/project_bchunk_hash.md` — meta-memory: bChunk = Jenkins mix3 derivation

## Appendix C — Naming conventions seen in cracked attributes

Catalog of naming patterns to seed future cracking attempts:

- **`UPPER_SNAKE`** for engine constants and limits: `MAX_NEWTONS`, `MAX_FRAGMENTS`, `MAX_SMACKABLES`, `RESPAWN_TIME`, `MAX_TRAFFIC_SPAWN_DISTANCE`, `WORLD_TYPE`, `STITCH_COLLISION_TYPE` (sic "STICH").
- **`PascalCase`** for general gameplay: `CashReward`, `TimeLimit`, `RaceLength`, `MaxHeatLevel`, `RandomOpponent`.
- **`camelCase` (lowercase-first)** for some particle/damage attributes: `forceMultiplier`, `damageMultiplier`, `message_id`, `engineaudio`, `chopperspecs`, `rigidbodyspecs`, `damagespecs`, `acceltrans`, `aivehicle`, `gameplayvault`, `chassis`, `frontend`, `tires`, `nos`, `induction`, `transmission`, `engine`, `brakes`, `junkman`, `racetable`, `heattable`, `supporttable`, `supportracetable`, `tmx_playthings`, `start_sequencer`, `no_trigger`, `doTest`, `fecompressionstoggle`, `scriptname`, `distance`, `fallOffUnit`, `explosionForceLimit`, `triggerThreshold`, `reflection_amount`, `flare_texture`, `car_zprepass_deg_210`, `emittergroup`, `emitteruv`.
- **`SCREAMING_SNAKE_CASE` for the BEHAVIOR_MECHANIC_* prefix family** — a strict 9-entry registry.
- **Misspellings preserved**: `STICH_COLLISION_TYPE` (should be "STITCH"), `InScatterMulitply` ("multiply"), `ThreshholdValue`/`ThreshholdSpeed` ("threshhold"), `Maxscale` (lowercase scale). When generating candidates, always include common misspellings.

---

*Last updated 2026-05-15. 294/345 = 85.2% cracked. Authoritative source: `docs/attribute_cracks_verified.json`.*
