---
name: customization/vinyl subsystem
description: Performance-part picker hashes "CUSTOMIZATION_%s_%d" string; vinyls/textures load from CARS\<name>\{TEXTURES,VINYLS,PREVINYL}.BIN; 9 part categories with numeric ID groups.
type: project
originSessionId: c4edf485-e85f-4e2f-ac31-e021ba66e8d6
---
## Per-car bundle loader
`VinylLoadPerCarBundle @ 0x75bb40` loads three bundles for a given car:
1. `CARS\<carname>\TEXTURES.BIN` (mandatory) → per-car body textures
2. `CARS\<carname>\PREVINYL.BIN` or `VINYLS.BIN` (optional) — chosen by `*(char*)(param_1+7)` flag (vinyl-design-mode? 2 = preview, else final). When `DAT_009b09fc != 0`, force PREVINYL.BIN.
3. Two more streams (probably DAMAGE.BIN, internal mesh refs) via FUN_00753060 calls.

## Performance-part dispatch
`GetCustomizationPartHashByCategory @ 0x7b5ef0` validates a part-category ID (range 0x101..0x70b) and hashes `"CUSTOMIZATION_%s_%d"` to get the FNG/UI string-ID for that part. Returns sentinel 0x9BB9CCC3 for invalid IDs.

ID ranges (high byte = group):
- **0x1xx — Body kits / spoilers** (0x101 PD_BodyKit, 0x102 PD_FrontBumper, 0x104 PD_Spoiler, 0x105 PD_RearBumper)
- **0x2xx — Engine / drivetrain** (0x201..0x207 — PD_ENGINE_*, PD_TURBO, PD_TRANSMISSION, PD_NITROUS, PD_TIRES, PD_SUSPENSION, PD_BRAKES — driven by `PD_ENGINE_%d_%d`)
- **0x3xx — Exhaust / nitrous** (0x301, 0x303, 0x304, 0x306, 0x307)
- **0x5xx — Suspension / tires** (0x501..0x506)
- **0x6xx — Brakes** (0x601..0x607)
- **0x7xx — Vinyl / paint** (0x701..0x70b — VINYL_LAYER0, VINYL_COLOUR0_R/G/B, etc.)

## Front-end FNG screens
- `Showcase.fng` — paint/vinyl showcase
- `CustomizePerformance.fng` — performance upgrade screen

**Why:** Deep modding (custom car packs, new vinyl layers) hits these paths. The 0x101..0x70b range tells you which IDs are reserved by the game; new categories must avoid them.

**How to apply:** When asked "where is vinyl applied?" or "where is engine upgrade tier set?", trace from `VinylLoadPerCarBundle` (per-car bundle path) and `GetCustomizationPartHashByCategory` (UI label resolution). The hash function feeds an FE database lookup.
