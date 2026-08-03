---
name: Ghidra MCP endpoint docs
description: Local docs covering all ~193 Ghidra MCP HTTP tools served by bethington/ghidra-mcp v5.7.1
type: reference
originSessionId: c4edf485-e85f-4e2f-ac31-e021ba66e8d6
---
The Ghidra MCP plugin (bethington/ghidra-mcp **v5.7.1**) at `http://127.0.0.1:8089` exposes ~193 tools across 14 categories. The live discovery endpoint is `GET /mcp/schema` (returns `{tools:[…], count}`), and `/mcp/health` is the liveness check.

**v5.7.1 vs v5.6.0:** +23 endpoints, 0 removed. Highlights:
- **Function tags** (10 new): `/create_function_tag`, `/list_function_tags`, `/add_function_tag`, `/batch_add_function_tags`, `/get_function_tags`, `/search_functions_by_tag`, `/remove_function_tag`, `/batch_remove_function_tags`, `/delete_function_tag`, `/set_function_tag_comment` — bucket functions into named tags queryable by tag.
- **Project mgmt**: `/create_project`, `/open_project`, `/close_project`, `/get_project_info`
- **Program loading**: `/load_program`, `/load_program_from_project`
- **Globals**: `/set_global`, `/audit_global`, `/audit_globals_in_function`
- **Archive ingestion**: `/archive_ingest_function`, `/archive_ingest_program`, `/merge_program_documentation`
- **Server**: `/server/status`
- `search_functions_enhanced` adds `isThunk` / `isExternal` fields and filters
- GUI toggle for function-name enforcement (turn off PascalCase linter warnings if needed)

Local docs in this project (regenerate from live schema if the plugin updates):

- `docs/GHIDRA_MCP_ENDPOINTS.md` — full per-category reference, every endpoint with method/params/types/defaults (~120 KB, generated from `/mcp/schema`).
- `docs/GHIDRA_MCP_CHEATSHEET.md` — daily-driver subset with curl recipes including the new tag/project/multi-program flows.

Helper script `/tmp/ghr.sh` wraps the most-common calls (`rename`, `decomp`, `search`, `plate`, `save`, `count`, `info`).

**Speed.exe project tag inventory (created with the new function-tag feature):**
- `Render` (14), `Streamer` (21), `Input` (14), `Physics` (30), `AI` (24), `Engine` (35), `Hash` (9), `Boot` (5) — query each via `GET /search_functions_by_tag?tag=<Name>`.

To regenerate docs after a plugin update:
```
curl -sS http://127.0.0.1:8089/mcp/schema -o /tmp/mcp_schema.json
# then run the python renderer that produced GHIDRA_MCP_ENDPOINTS.md
```

To switch active program (avoid querying the wrong binary):
```
curl -sS -X POST http://127.0.0.1:8089/switch_program \
  -H 'Content-Type: application/json' -d '{"program":"speed.exe"}'
```
