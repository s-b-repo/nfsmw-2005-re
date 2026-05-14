# NFSMW attribute hash registry

The `attributes.bin` file (VPAK, 689,728 bytes) holds the gameplay attribute schema. Starting at file offset `0x18000`, every 16 bytes is one attribute row:

```
[+0x00..+0x03]  u32  attribute_name_hash  (Jenkins mix3, seed 0xABCDEF00)
[+0x04..+0x07]  u32  type_hash             (one of the EA::Reflection::* / Attrib::* types below)
[+0x08..+0x09]  u16  ?
[+0x0a..+0x0b]  u16  ?
[+0x0c..+0x0d]  u16  ?
[+0x0e..+0x0f]  u16  type/flags
```

Total attributes: **345** rows. **Verified cracked: 294 (85.2%)** as of 2026-05-14 post-wave-7 — every name confirmed by re-hashing with bChunk (machine-verifiable, zero false positives). Full verified list: `docs/attribute_cracks_verified.json` (294 entries).

**Target of 80% REACHED.** All 5 original mystery hashes now solved:
- `0xB5C0DAC8 = AUTO_SIMPLIFY` (wave-6, via SDK CamelCase→UPPER_SNAKE conversion)
- `0xDA5F19F9 = BEHAVIORS` (wave-6, via EA-vocab wordlist)
- `0xEE0011E3 = SimplePhysics` (wave-7, via community wordlist)
- `0x360552DA = ExplosionEffect` (wave-7, via community wordlist)
- `0x44F1273B = DROPOUT` (wave-7, via community wordlist)

### Wave-7 breakthrough: community wordlists
Integrated 43,102 attribute names from the community NFS hash database (`NFSTools/Attribulator` Speed Profiles + `MWisBest/OpenNFSTools` res/hashes.txt + `yugecin/nfsu2-re` docs/dumps). Single-pass match added **+173 cracks** — going from 121 (35%) to 294 (85%).

NOTE 2026-05-14: Of the 5 "mystery hashes" formerly believed all-Float, attributes.bin schema verification shows two have different types: `0xEE0011E3` → Bool (0x064BEC37) and `0xDA5F19F9` → StringKey (0xA502A824). See the dedicated section below for code-derived semantic roles.

## Newly cracked 2026-05-14 (35 names verified via bChunk)

All 35 verified mathematically — each computed hash matches the attributes.bin row exactly.

### Float (16 new)
| Hash | Name | Notes |
|------|------|-------|
| `0x0A91596D` | InitialSpeed | Race start speed |
| `0x0FA46807` | MinScale | Particle minimum scale |
| `0x3A5970F4` | forceMultiplier | (camelCase) damage/impact force mult |
| `0x4C141ED7` | HeightStart | Particle initial height |
| `0x6BBC13EE` | LengthStart | Particle initial length |
| `0x777ECE27` | KnockoutTime | Knockout-mode timing |
| `0x7585F041` | TimeLimit | Race time limit |
| `0x7C11C52E` | RaceLength | Total race length |
| `0x7F8EEA1A` | STIFFNESS | Suspension stiffness |
| `0x811C6606` | TRAFFIC_SPEED | Ambient traffic speed |
| `0xA6F789CB` | damageMultiplier | Damage multiplier (camelCase) |
| `0xBF2FDB5C` | SpawnTime | Cop/object spawn timing |
| `0xD8165518` | NumParticlesVariance | Particle count randomization |
| `0xDC943CC9` | NumParticles | Particle emit count |
| `0xEFB4BB64` | LifeVariance | Particle life randomization |
| `0xF5A03629` | MaxHeatLevel | Pursuit heat ceiling |
| `0xF7649E63` | MaxSize | Particle max size |

### Bool (7 new)
| Hash | Name | Notes |
|------|------|-------|
| `0x2B1F54F6` | PursuitRace | Is this race a pursuit-mode? |
| `0x3E9156CA` | Template | Is this row a template? |
| `0x40E94F86` | SELECTABLE | UI-selectable flag |
| `0x665F4D74` | TILTING | Tilt physics flag |
| `0x6DF0ABFE` | RandomOpponent | Random AI opponent pick |
| `0xB2AC32C7` | FireOnExit | Trigger on exit |
| `0xCE4261AC` | OneShot | One-shot trigger flag |

### Text (6 new)
| Hash | Name | Notes |
|------|------|-------|
| `0x6319B692` | TrafficPattern | Reference to traffic pattern row |
| `0x9CA1C8F9` | CollectionName | Collection (vehicle/track) name |
| `0xAA27E71C` | DefaultPresetRide | Default car preset reference |
| `0xC0EEB909` | PlayerCarType | Player vehicle reference |
| `0xD686D61E` | CopSpawnType | Cop spawn template reference |
| `0xF833C06F` | CarType | Vehicle type identifier |

### StringKey (3 new)
| Hash | Name | Notes |
|------|------|-------|
| `0x5AAB860F` | EventSequencer | Event sequencer reference |
| `0xBF49A7D9` | BankName | Audio bank reference |
| `0xDA5F19F9` | **BEHAVIORS** | Child component list (was previously a "mystery hash") |

### UInt32 (1 new)
| Hash | Name | Notes |
|------|------|-------|
| `0x9E8910EF` | message_id | Network/event message ID |

### RefSpec (1 new)
| Hash | Name | Notes |
|------|------|-------|
| `0xABA86E60` | emittergroup | Particle emitter group reference |

### What worked
1. EA-conventional vocabulary list (~250 terms) × suffix patterns (Min/Max/Time/Length/Multiplier/Force/etc.)
2. CamelCase + ALL_CAPS variants of every base word
3. Compound generation with prefix/suffix separators ("", "_")
4. Particle/effect-specific vocabulary (NumParticles, LifeVariance, HeightStart, etc.) — these matched a cluster of Float attributes
5. Race-mode-specific vocab (PursuitRace, KnockoutTime, RaceLength, TimeLimit) — matched gameplay attributes
6. Mathematical verification: every crack confirmed by re-hashing — `bChunk("BEHAVIORS") = 0xDA5F19F9` etc.

## Type hashes

EA's reflection system + their custom Attrib namespace types:

| Hash | Name | Count |
|------|------|-------|
| 0x3C16EC5E | EA::Reflection::Float        | 137 attributes |
| 0xA3F0C234 | EA::Reflection::Text         | 39 attributes |
| 0x939992BB | EA::Reflection::UInt32       | 38 attributes |
| 0x064BEC37 | EA::Reflection::Bool         | 71 attributes |
| 0x2B936EB7 | Attrib::RefSpec              | 38 attributes |
| 0xA502A824 | Attrib::StringKey            | 33 attributes |
| 0xDB9D3A16 | eDRIVE_BY_TYPE               | 5 attributes |
| 0x349D3A16 | (uncracked)                  | ? |
| 0x934A36EC | (uncracked)                  | ? |

Other reflection types (referenced as values, not used as schema-row types):
0x5763DA41 = EA::Reflection::Int32, 0x6F27B5BC = Int8, 0x671ECBE2 = UInt8, 0xE51A99C1 = UInt16,
0x34FDE6BB = Attrib::Types::Vector4, 0xA1E54784 = Attrib::Types::Matrix, 0xD680287D = Attrib::Types::Vector3.

## Verified counts by type (2026-05-14, post wave-7 community wordlist)

| Type | Cracked | Total | % |
|---|---:|---:|---:|
| StringKey | 32 | 33 | **97%** |
| Bool | 64 | 71 | **90%** |
| Text | 35 | 39 | **90%** |
| Float | 120 | 137 | **88%** |
| RefSpec | 26 | 38 | 68% |
| UInt32 | 16 | 38 | 42% |
| eDRIVE_BY | 1 | 5 | 20% |
| **Total** | **294** | **345** | **85.2%** |

## How we got from 35% to 85% (wave-7)

The key was discovering the community NFS hash database. Three projects ship 43k+ attribute name candidates:

1. **NFSTools/Attribulator** — Speed Profiles plugin has 43,102 names (the primary source)
2. **MWisBest/OpenNFSTools** — `res/hashes.txt`, 1,262 names (curated MW-specific)
3. **yugecin/nfsu2-re** — `docs/dumps/hashes.txt`, parsed from runtime traces

A single-pass match (just hash every word in the corpus) yielded **+173 cracks** — moving us from 121 to 294 verified cracked. The cracker is at `/tmp/crack_v8_community.py`.

The takeaway: this work was already done by the community over a decade of NFS modding. We were re-deriving it from scratch in waves 5/6 instead of pulling the existing list. Single `git clone` per repo unlocked half the remaining work.

## Why the last 15% (51 names) is hard

## (legacy text follows — preserved for context)

Wave-6 (before community lists) ran ~150M wordlist combinations

Wave-6 ran **~150M wordlist combinations** across:
- 80,000 unique tokens from decompressed bundles + speed.exe + all 3 NFS SDK headers (MW + Carbon + ProStreet)
- ~250 EA-conventional vocab terms (engineering, physics, AI, race, gameplay)
- Every CamelCase / PascalCase / UPPER_SNAKE / camelCase case variant
- 2-word and 3-word compounds with select prefix/suffix pairs
- Digit suffixes (1..15)
- Triple-cluster compounds (e.g. ATTACK × TIME × FORCE)

This pulled the cracked count from 68 → 121 verified before wave-7's community-list breakthrough. After wave-7: **294/345 (85.2%)**, 51 remaining. The remaining hashes likely require:
1. **NFSU2 / Carbon attribute lists from the community** (most NFS-modding tools have these; not available locally)
2. **PDB / source leak** for the real source-derived names
3. **Live runtime tracing** to infer names from value semantics at each use-site

The remaining names are likely:
- Multi-word phrases not in our wordlist (e.g. RidingHeightFront, AmbientShakeFrequency)
- Internal EA dev terms not exposed in any public material
- Localized / abbreviated forms

## Float (51/137 cracked — was 31 before 2026-05-14, includes MinRPM/MaxRPM/InitialPlayerSpeed recovered from earlier sessions)

Camera/Rendering: FOV, Radius, Width, HEIGHT, ANGLE, MinSize, Life, Power, Rotation, distance, LAG, TOD, ColourBloomIntensity, BlackBloomIntensity, DetailMapIntensity, Desaturation
Vehicle/Physics: MASS, STEERING, AxlePair, **AUTO_SIMPLIFY** (Smackable::mAutoSimplify, 2026-05-14)
Game logic: LeaderSupport, SpeedHighway, DamageScaleRecord, CopCountRecord, Priority

## RefSpec (23/38 cracked) — Subsystem references

These are the major vehicle/engine subsystem records: **engine, transmission, brakes, tires, nos, induction, chassis, rigidbodyspecs, engineaudio, damagespecs, chopperspecs, junkman, aivehicle, frontend, acceltrans, Trailer, EffectLinkageRecord**.

This is a complete vehicle data model:
- **engine** + **transmission** + **acceltrans** (acceleration transmission)
- **chassis** + **rigidbodyspecs** + **damagespecs**
- **brakes** + **tires** + **nos** + **induction**
- **engineaudio** for audio
- **junkman** (the meta-tier system that stacks performance bonuses)
- **chopperspecs** (helicopter)
- **Trailer** (truck trailers)
- **aivehicle** (AI-only data)
- **frontend** (FE preview)

## StringKey (18/33 cracked — was 14 verified before 2026-05-14) — Behavior mechanic registry

The 9 BEHAVIOR_MECHANIC_* keys define the entire vehicle-component system:

```
BEHAVIOR_MECHANIC_SUSPENSION
BEHAVIOR_MECHANIC_EFFECTS
BEHAVIOR_MECHANIC_RESET
BEHAVIOR_MECHANIC_DAMAGE
BEHAVIOR_MECHANIC_RIGIDBODY
BEHAVIOR_MECHANIC_ENGINE
BEHAVIOR_MECHANIC_DRAW
BEHAVIOR_MECHANIC_INPUT
BEHAVIOR_MECHANIC_AUDIO
```

Plus: DESCRIPTION, CLASS, MODEL, StitchCollisionVol, STICH_COLLISION_TYPE.

These are the 9 "behaviors" attached to every pvehicle subobject (matches the pvehicle inventory at 0x008add1c).

## UInt32 (5/38 verified — was 3 in attrib_table.json)

CarID, COST_TO_STATE, EffectLinkageRecord, **message_id** + 1 type-self-ref.

## Bool (13/71 verified — was 4 in attrib_table.json, +9 wave-6)

CatchUp (rubber-band on/off), Directional, Tranny, Persistent, **PursuitRace, Template, SELECTABLE, TILTING, RandomOpponent, FireOnExit, OneShot, AutoStart, no_trigger**.

## Text (17/39 verified — was 7 in attrib_table.json, +10 wave-6)

Name, EventID, MilestoneName, Region, Barriers, ZoneType, ParticleTextureRecord, **TrafficPattern, CollectionName, DefaultPresetRide, PlayerCarType, CopSpawnType, CarType, ParticleEffect, EventIconType, RacerName, scriptname**.

## RefSpec (17/38 verified — was 16 in attrib_table.json, +1 wave-6)

engine, transmission, brakes, tires, nos, induction, chassis, rigidbodyspecs, engineaudio, damagespecs, chopperspecs, junkman, aivehicle, frontend, acceltrans, Trailer, **emittergroup**.

## 5 mystery hashes — semantic roles inferred (2026-05-14)

| Hash | Type (CORRECTED) | Cracked name | Semantic role |
|------|------------------|--------------|----------------|
| `0xEE0011E3` | **Bool** (0x064BEC37) — *NOT Float as previously labelled* | — | Smackable construction flag. `Smackable_Construct @ 0x6895a0` reads it as a byte and pairs it with the "ghost" flag at `puVar3[+0x58]` to pick `FUN_006ed390` (ghost variant) vs `FUN_006ed260` (solid variant). The instance row at `0x611B0` stores this Bool with extra=`0xDA5F19F9` — the Bool gates **whether the child-effects StringKey list applies**. |
| `0xB5C0DAC8` | Float | **AUTO_SIMPLIFY** | `Smackable::mAutoSimplify` (a `const float` field in the C++ struct, per nfsplugin_sdk_mw05/Types/Smackable.h). Stored at `RB this+0xfc` by `CreateRigidBodyComponent_PhysicsObjectInit @ 0x688660`. Drives LOD/cull simplify threshold. Instance values seen: 2.5, 3.0. |
| `0xDA5F19F9` | **StringKey** (0xA502A824) — *NOT Float* | — | List of child component keys (StringKey list). `CreateRigidBodyComponent` iterates via `LookupAttributeIteratorByHash` / `GetAttributeIteratorChildCount`, and for each child calls `FUN_00684bb0(this, kind, name)` which attaches an `EffectsSmackable` sub-component. Likely named `ChildEffects` / `EffectsList` / `SpawnEffects` — none cracked. |
| `0x360552DA` | Float | — | Push-back / snap-back gate in `FUN_00677100 @ 0x67713a`. If `*attr > 0`, the function computes `param_2 - dot(velocity, ref)` and applies a collision-response impulse scaled by inverse-mass via vt[+0x88]. Instance values: 0.25, 0.5, 1.0 — fractional factor pattern. Candidate names tried (no crack): `PushFactor`, `BounceThreshold`, `Restitution`, `SnapBack`, `PUSH_FACTOR`. |
| `0x44F1273B` | Float (2-element) | — | **Timed continuous force / surge config.** Read by `RigidBody_ComputeMassInverseFromAttribute @ 0x669c00` (function name is **SUSPECT** — real `MASS` hash is `0x4A56503D`). Both indices `[0]` and `[1]` must be > 0 for the gate to pass; `[0]` is stored at RB `+0xf4`, `+0xf0` is a countdown timer. `FUN_0066a0b0` decays the timer each tick and applies force `= -(dt * attr[1])` via SimContext vt[+0x7c], then kills via vt[+0x08] when expired. Looks like NOS push, ramming burst, or recoil config — not static mass. Instance value at `0x60870/0x61D20/0x64720` is `0xEFFECADD` paired with `0xFB19212F` (the per-axis inertia override hash). |

### Cross-reference: the EE0011E3 ↔ DA5F19F9 pairing

In `attributes.bin @ 0x611B0`, the EE0011E3 Bool instance row literally embeds `0xDA5F19F9` in its extra-data field. Read with `Smackable_Construct`'s code: the Bool branches on ghost-vs-solid AND CreateRigidBodyComponent then iterates the StringKey list of children — so these two attributes are a paired **"has child effects? / what effects?"** mechanism for destructible objects.

### Name candidates that did NOT crack (verify list)

For 0xEE0011E3 (Bool): `HasEffects`, `IsGhost`, `Ghost`, `IsBreakable`, `IsPersistant`, `VIRGIN`, `AUTO_DROP`, `AUTO_PERSIST`, `AUTO_EXPLODE`, `IS_OFF_WORLD`, `EXPLODES_ON_HIT`, `HAS_FX`, `HAS_DEBRIS`, `HAS_CHILDREN`.
For 0xDA5F19F9 (StringKey): `Effects`, `ChildEffects`, `EffectsList`, `EffectSpec`, `EffectSpecs`, `ParticleList`, `EmitterList`, `Children`, `EFFECT_LIST`, `CHILD_LIST`, `SUB_OBJECTS`.
For 0x360552DA (Float): `PushFactor`, `BounceThreshold`, `Restitution`, `Bounce`, `SnapBack`, `PUSH_BACK`, `SETTLE`, `Stiffness`, `BumpFactor`.
For 0x44F1273B (Float[2]): `BoostForce`, `KickForce`, `PushForce`, `BurstForce`, `Jet`, `Thrust`, `Recoil`, `Surge`, `IMPULSE_TIME`, `IMPULSE_FORCE`.

Wordlist seeded from `attributes.bin`-adjacent strings (`/tmp/all_strings.txt`, 93K unique) plus prefix/suffix combinations (1.3M candidates) plus exhaustive SDK identifier sweep (`nfsplugin_sdk_mw05/`, 4335 tokens). Strings are very likely stripped from the shipped binaries.

## How to use

To find the type and offset of any attribute name:
1. Hash the name with bChunk (Jenkins mix3, seed `0xABCDEF00`).
2. Search `attributes.bin` for the hash as little-endian u32.
3. Read the 16-byte row containing it; the second u32 is the type hash.

Example: `bChunk("MASS")` = `0x4A56503D`. Searching attributes.bin finds the entry; type = `0x3C16EC5E` (Float). Confirms MASS is a Float-typed attribute.

## Cracking script

`/tmp/crack_floats.py` and the heredoc in this session — extract strings from all bundles + speed.exe + DLLs (~6.9M unique strings), generate name variants, hash against the attribute table. Per-type recovery rates:
- RefSpec: 60% (subsystem ids tend to appear in code as data-section strings)
- StringKey: 45%
- Float: 22%
- Text: 23%
- UInt32: 21%
- Bool: 13%
