# Ghidra MCP — quick-reference cheatsheet (v5.7.1)

Daily-driver subset of the 193 endpoints. Full reference in `GHIDRA_MCP_ENDPOINTS.md`.

Base URL (TCP): `http://127.0.0.1:8089` · Plugin: GhidraMCP v5.7.1.

**v5.7.1 highlights:**
- 10 new **function-tag** endpoints (`/create_function_tag`, `/add_function_tag`, `/batch_add_function_tags`, `/search_functions_by_tag`, …) — bucket functions into named tags queryable by tag
- Project mgmt: `/create_project`, `/open_project`, `/close_project`, `/get_project_info`
- Multi-program: `/load_program`, `/load_program_from_project`, `/switch_program`, `/list_open_programs`
- Globals: `/set_global`, `/audit_global`, `/audit_globals_in_function`
- Doc archive: `/merge_program_documentation`, `/archive_ingest_function`, `/archive_ingest_program`
- `search_functions_enhanced` adds `isThunk` / `isExternal` filters

## listing

- `GET  /list_methods` — List all function names with pagination
    - params: [offset] [limit] [program]
- `GET  /list_functions` — List all functions (no pagination)
    - params: [program]
- `GET  /list_strings` — List defined strings with optional filter
    - params: [offset] [limit] [filter]
- `GET  /list_imports` — List external/imported symbols
    - params: [offset] [limit] [program]
- `GET  /list_exports` — List exported entry points
    - params: [offset] [limit] [program]
- `GET  /list_namespaces` — List namespace hierarchy
    - params: [offset] [limit] [program]
- `GET  /search_strings` — Search strings by regex pattern
    - params: <search_term> [min_length] [encoding] [offset]
- `GET  /search_functions` — Search functions by name pattern
    - params: [name_pattern] [offset] [limit]
- `GET  /search_functions_enhanced` — Advanced function search with filtering
    - params: [name_pattern] [min_xrefs] [max_xrefs]

## function

- `GET  /decompile_function` — Decompile function at address to pseudocode
    - params: <address> [program] [timeout]
- `POST /rename_function` — Rename function by old and new name
    - params: <oldName> <newName> [program]
- `GET  /get_function_count` — Get total function count
    - params: [program]
- `POST /set_function_prototype` — Set function prototype (return type, parameter types, calling convention) by address
    - params: <function_address> <prototype> [calling_convention] [program]
- `GET  /get_function_variables` — List all variables in a function
    - params: [function_name] [address] [program]
- `POST /rename_function_by_address` — Rename function at specific address
    - params: <function_address> <new_name> [program]
- `POST /create_function` — Create function at address
    - params: <address> [name] [disassemble_first] [program]
- `POST /delete_function` — Delete function at address
    - params: <address> [program]

## symbol

- `POST /rename_data` — Rename data at address
    - params: <address> <newName> [program]
- `POST /create_label` — Create a label at address
    - params: <address> <name> [program]
- `POST /rename_label` — Rename a label at address
    - params: <address> <old_name> <new_name> [program]
- `GET  /list_globals` — List global DATA symbols
    - params: [offset] [limit] [filter]
- `POST /set_global` — Atomically apply name + type + plate-comment + array length to a global variable
    - params: <address> <name> <type_name> <plate_comment> [array_length] [program]
- `GET  /audit_global` — Audit a global variable's documentation state
    - params: <address> [program]
- `GET  /audit_globals_in_function` — Audit every global variable referenced from within a function in one call
    - params: <address> [program]

## comment

- `POST /set_plate_comment` — Set function header/plate comment
    - params: <address> <comment> [program]
- `POST /set_decompiler_comment` — Set decompiler PRE_COMMENT at address
    - params: <address> <comment> [program]
- `POST /set_disassembly_comment` — Set disassembly EOL_COMMENT at address
    - params: <address> <comment> [program]

## xref

- `GET  /get_xrefs_to` — Get cross-references to an address
    - params: <address> [offset] [limit] [program]
- `GET  /get_xrefs_from` — Get cross-references from an address
    - params: <address> [offset] [limit] [program]
- `GET  /get_function_callers` — Get functions calling a function
    - params: [name] [address] [offset]
- `GET  /get_function_callees` — Get functions called by a function
    - params: [name] [address] [offset]
- `GET  /get_function_call_graph` — Traverse call graph from a function
    - params: [name] [address] [depth]

## tags

- `POST /create_function_tag` — Create a program-wide function tag definition with an optional comment
    - params: <name> [comment] [program]
- `GET  /list_function_tags` — List all program-wide function tag definitions with their use counts
    - params: [offset] [limit] [program]
- `POST /add_function_tag` — Attach one or more tags to a function
    - params: <function> <tags> [program]
- `POST /batch_add_function_tags` — Attach tags to many functions in one transaction
    - params: <assignments> [program]
- `GET  /get_function_tags` — List all tags assigned to a specific function
    - params: <function> [program]
- `GET  /search_functions_by_tag` — List all functions that have a specified tag attached
    - params: <tag> [offset] [limit] [program]
- `POST /remove_function_tag` — Detach one or more tags from a function
    - params: <function> <tags> [program]
- `POST /delete_function_tag` — Delete a program-wide function tag definition
    - params: <name> [program]
- `POST /set_function_tag_comment` — Update the comment/description on an existing program-wide function tag
    - params: <name> <comment> [program]

## datatype

- `GET  /list_data_types` — List all data types with optional category filter
    - params: <category> [offset] [limit] [program]
- `POST /create_struct` — Create a structure data type
    - params: <name> <fields> [program]
- `POST /add_struct_field` — Add a field to a structure
    - params: <struct_name> <field_name> <field_type> [offset] [program]
- `POST /apply_data_type` — Apply data type at address
    - params: <address> <type_name> [clear_existing] [program]
- `GET  /get_struct_layout` — Get structure field layout
    - params: <struct_name> [program]

## analysis

- `GET  /analyze_function_complete` — Comprehensive single-call function analysis
    - params: <name> [include_xrefs] [include_callees] [include_callers]
- `GET  /inspect_memory_content` — Inspect memory with string detection
    - params: <address> [length] [detect_strings] [program]
- `GET  /analyze_dataflow` — Trace how a value propagates through a function using the decompiler's PCode graph
    - params: <address> [variable] [direction] [max_steps]
- `GET  /find_code_gaps` — Find gaps of undefined/unanalyzed bytes in executable memory not covered by any function body
    - params: [min_size] [offset] [limit]
- `GET  /find_undocumented_by_string` — Find FUN_* functions referencing a string
    - params: <address> [program]

## documentation

- `?? /build_hash_index` — _(not present in current schema)_
- `?? /find_undocumented_functions` — _(not present in current schema)_
- `POST /merge_program_documentation` — Bulk merge: copy ALL RE documentation from one program to another at matching addresses, in a single server-side transaction
    - params: <source> <target> [dry_run]
- `POST /archive_ingest_function` — Ingest a single function's documentation into the cross-version archive (re_kb
    - params: <address> [program] [version_override] [dry_run]
- `POST /archive_ingest_program` — Bulk-ingest every function in a program into the cross-version documentation archive
    - params: [program] [version_override] [limit]

## program

- `GET  /save_program` — Save current program
    - params: [program]
- `GET  /get_metadata` — Get program metadata
    - params: [program]
- `GET  /read_memory` — Read raw memory bytes
    - params: <address> [length] [program]
- `?? /run_script` — _(not present in current schema)_
- `GET  /list_bookmarks` — List bookmarks with optional filter
    - params: [category] [address] [program]
- `?? /load_program` — _(not present in current schema)_
- `?? /load_program_from_project` — _(not present in current schema)_
- `GET  /switch_program` — Switch MCP context to a different program
    - params: <program>

## project

- `?? /get_project_info` — _(not present in current schema)_
- `?? /open_project` — _(not present in current schema)_
- `?? /close_project` — _(not present in current schema)_
- `?? /create_project` — _(not present in current schema)_

## debugger

- `?? /debugger_status` — _(not present in current schema)_
- `?? /debugger_attach` — _(not present in current schema)_
- `?? /debugger_set_breakpoint` — _(not present in current schema)_
- `?? /debugger_step_over` — _(not present in current schema)_
- `?? /debugger_registers` — _(not present in current schema)_
- `?? /debugger_read_memory` — _(not present in current schema)_

## malware

- `?? /detect_anti_analysis` — _(not present in current schema)_
- `?? /extract_iocs` — _(not present in current schema)_
- `?? /find_suspicious_strings` — _(not present in current schema)_

## emulation

- `POST /emulate_function` — Emulate a single function with controlled register/memory inputs
    - params: <address> <registers> <memory> [max_steps] [return_registers] [program]

## Common recipes

```bash
# count + sanity
curl -sS http://127.0.0.1:8089/get_function_count
curl -sS http://127.0.0.1:8089/get_metadata    # current program
curl -sS http://127.0.0.1:8089/list_open_programs

# decompile by address (works with or without 0x prefix)
curl -sS 'http://127.0.0.1:8089/decompile_function?address=0x688660'

# rename a function
curl -sS http://127.0.0.1:8089/rename_function -X POST \
  -H 'Content-Type: application/json' \
  -d '{"oldName":"FUN_006897d0","newName":"ConstructRBVehicle"}'

# set a plate comment
curl -sS http://127.0.0.1:8089/set_plate_comment -X POST \
  -H 'Content-Type: application/json' \
  -d '{"address":"0x688660","comment":"Constructs RBVehicle physics body"}'

# === function tags (NEW in v5.7.1) ===
# create a tag
curl -sS http://127.0.0.1:8089/create_function_tag -X POST \
  -H 'Content-Type: application/json' \
  -d '{"name":"Render","comment":"Direct3D9 stuff"}'

# tag a single function
curl -sS http://127.0.0.1:8089/add_function_tag -X POST \
  -H 'Content-Type: application/json' \
  -d '{"function":"D3D9_CreateDeviceAndFirstPresent","tags":"Render"}'

# batch tag many (single call, much faster than looping)
curl -sS http://127.0.0.1:8089/batch_add_function_tags -X POST \
  -H 'Content-Type: application/json' \
  -d '{"assignments":[
        {"function":"D3D9_BuildPresentParameters","tags":"Render"},
        {"function":"D3D9_QueryAdapterCapabilities","tags":"Render"}]}'

# query everything in a tag
curl -sS 'http://127.0.0.1:8089/search_functions_by_tag?tag=Render&limit=100'

# search FUN_ stubs by xref count
curl -sS -G http://127.0.0.1:8089/search_functions_enhanced \
  --data-urlencode 'name_pattern=^FUN_' --data-urlencode 'regex=true' \
  --data-urlencode 'min_xrefs=5' --data-urlencode 'max_xrefs=50' \
  --data-urlencode 'sort_by=xref_count' --data-urlencode 'limit=20'
# v5.7.1 also adds --data-urlencode 'is_thunk=false' / 'is_external=false'

# walk callers from an anchored function
curl -sS 'http://127.0.0.1:8089/get_xrefs_to?address=0x688660'

# save the project (transactions must be closed)
curl -sS -X POST http://127.0.0.1:8089/save_program
```