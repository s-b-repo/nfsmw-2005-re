# Attribute hash cracking progress

**SUPERSEDED 2026-05-14 — see authoritative sources below.**

This file was a session-by-session tally; it has been replaced by the more comprehensive `docs/attribute_hashes.md` (registry + per-type tables + technique notes) and `docs/attribute_cracks_verified.json` (machine-readable, every entry hash-verified).

## Current verified state (2026-05-14, post wave-7)

- **294 / 345 attribute names cracked = 85.2%** ✅ (every name re-hashed with bChunk — zero false positives)
- 51 remaining
- ALL 5 of the original 5 mystery hashes solved:
  - `0xB5C0DAC8 = AUTO_SIMPLIFY` (wave-6)
  - `0xDA5F19F9 = BEHAVIORS` (wave-6)
  - `0xEE0011E3 = SimplePhysics` (wave-7)
  - `0x360552DA = ExplosionEffect` (wave-7)
  - `0x44F1273B = DROPOUT` (wave-7)
- 80% target exceeded thanks to integrating community NFS hash database (NFSTools/Attribulator + MWisBest/OpenNFSTools + yugecin/nfsu2-re)

## See also

- `docs/attribute_hashes.md` — full registry, per-type tables, naming conventions, wordlist techniques
- `docs/attribute_cracks_verified.json` — authoritative machine-readable list (294 entries)
- `~/.claude/projects/.../memory/project_attribute_schema.md` — schema + use-site notes
- `docs/PROGRESS.md` — session-by-session crack-rate history
