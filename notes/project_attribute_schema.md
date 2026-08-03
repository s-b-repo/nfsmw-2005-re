---
name: NFSMW attribute schema in attributes.bin
description: VPAK file with 16-byte fixed rows starting at offset 0x18000. Each row = (name_hash, type_hash, flags). 7 of 9 type hashes cracked; 29 of 137 Float-typed attributes cracked.
type: project
originSessionId: c4edf485-e85f-4e2f-ac31-e021ba66e8d6
---
`/extracted/app/GLOBAL/attributes.bin` is the central gameplay attribute schema.

## Row layout (16 bytes, starting at offset 0x18000)

```
[+0x00] u32 attribute_name_hash    (Jenkins mix3, seed 0xABCDEF00)
[+0x04] u32 type_hash               (EA::Reflection::* / Attrib::*)
[+0x08] u16 ?
[+0x0a] u16 ?
[+0x0c] u16 ?
[+0x0e] u16 type_flags
```

## Cracked type hashes

| Hash | Name |
|------|------|
| 0x3C16EC5E | EA::Reflection::Float (137 attribs) |
| 0xA3F0C234 | EA::Reflection::Text (39) |
| 0x939992BB | EA::Reflection::UInt32 (38) |
| 0x064BEC37 | EA::Reflection::Bool (71) |
| 0x2B936EB7 | Attrib::RefSpec (38) |
| 0xA502A824 | Attrib::StringKey (33) |
| 0xDB9D3A16 | eDRIVE_BY_TYPE (5) |

## Crack rates (98/345 = 28% recovered)
- RefSpec: 23/38 (60%) — subsystem refs like engine, transmission, brakes, tires, nos
- StringKey: 15/33 (45%) — BEHAVIOR_MECHANIC_* registry (the 9 vehicle behaviors)
- Float: 30/137 (22%) — FOV, Radius, MASS, STEERING, Power, Life, Rotation, etc.
- Text: 9/39 (23%) — Name, EventID, MilestoneName, Region, ZoneType
- UInt32: 8/38 (21%) — CarID, COST_TO_STATE, EffectLinkageRecord
- Bool: 9/71 (13%) — CatchUp, Directional, Tranny, Persistent
- eDRIVE_BY: 4/5

## Vehicle subsystem inventory (from RefSpec attributes)
The 23 cracked RefSpec names define the complete vehicle data model:
**engine, transmission, brakes, tires, nos, induction, chassis, rigidbodyspecs, engineaudio, damagespecs, chopperspecs, junkman, aivehicle, frontend, acceltrans, Trailer, EffectLinkageRecord** — every car/cop/heli/trailer pulls these by reference.

## Behavior mechanic registry (StringKey-cracked)
9 BEHAVIOR_MECHANIC_* keys define the pvehicle subobject types: **SUSPENSION, EFFECTS, RESET, DAMAGE, RIGIDBODY, ENGINE, DRAW, INPUT, AUDIO**. Matches the inline RTTI at 0x008add1c.

## 5 mystery hashes (uncracked)

`0xEE0011E3, 0xB5C0DAC8, 0xDA5F19F9, 0x360552DA, 0x44F1273B` — all Float-typed. Their name strings are NOT present in any shipped asset. Likely stripped from release build but preserved as hashes.

**Why:** Now we know the canonical attribute store schema and can extract type info for any attribute name on demand. This gives us a partial map of "what gameplay knobs exist" — a precondition to tuning anything.

**How to apply:**
- For any attribute name string, hash with bChunk → look up in attributes.bin → get type → read value where it's stored.
- Cracking script: `/tmp/crack_floats.py` (covers all 137 Float-typed targets).
- Full cracked-name registry: `/home/cortix/Downloads/9_Need for Speed Most Wanted Magipack/docs/attribute_hashes.md`.
- For comprehensive name discovery, search:
  - decompressed LZC bundles (`extracted/app/GLOBAL/decompressed_lzc/*.bun`)
  - speed.exe / DLLs
  - try CamelCase + UPPERCASE variants (EA naming inconsistent across the schema)
