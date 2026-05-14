# Ghidra MCP — endpoint reference (live `/mcp/schema` snapshot, v5.7.1)

Captured from `http://127.0.0.1:8089/mcp/schema` while attached to `speed.exe`.

Plugin version: **5.7.1**.  Total tools: **193** across **14** categories.


## Transports

- **TCP**: `http://127.0.0.1:8089/<path>` — survives Ghidra restarts at the same port.
- **UDS**: `/run/user/1000/ghidra-mcp/ghidra-<pid>.sock` — socket name changes every Ghidra launch.
- Helper: `/tmp/ghr.sh {rename|decomp|search|plate|save|count|info}` wraps the most-used calls.

## Schema/health

- `GET /mcp/schema` — this discovery doc
- `GET /mcp/health` — liveness check
- `GET /check_connection` — handshake
- `GET /get_version` — plugin version

## What's new in v5.7.1 (vs prior v5.6.0 docs)

- **Function tags** (10 endpoints): `/create_function_tag`, `/list_function_tags`, `/add_function_tag`, `/batch_add_function_tags`, `/remove_function_tag`, `/batch_remove_function_tags`, `/get_function_tags`, `/search_functions_by_tag`, `/delete_function_tag`, `/set_function_tag_comment` — organize functions into named buckets queryable via tag.
- **Project management**: `/create_project`, `/open_project`, `/close_project`, `/get_project_info`
- **Program loading**: `/load_program`, `/load_program_from_project`
- **Archive integration**: `/archive_ingest_function`, `/archive_ingest_program`
- **Globals**: `/audit_global`, `/audit_globals_in_function`, `/set_global`
- **Server**: `/server/status`
- **search_functions_enhanced**: now exposes `isThunk` / `isExternal` fields and filters
- **GUI toggle** for function-name enforcement (turn off PascalCase linter warnings)
- Various idempotency / error-message fixes for `set_global`, `rename_or_label`, `set_variables`, etc.

## Parameter source legend

`query` = URL `?key=value`  ·  `body` = JSON POST body  ·  `path` = path segment  ·  `*` = required.

---

## Categories

- [analysis](#analysis) — 18 tool(s) · Completeness analysis, control flow, similarity, crypto detection, memory inspection
- [comment](#comment) — 6 tool(s) · Set/get plate, decompiler, disassembly, repeatable comments
- [datatype](#datatype) — 32 tool(s) · Struct/enum/union CRUD, apply data types, type conflicts, validation
- [debugger](#debugger) — 18 tool(s) · Live debugging: attach, breakpoints, step, registers, memory. Requires a CodeBrowser with Debugger view open.
- [documentation](#documentation) — 14 tool(s) · Function hashing, cross-binary documentation, undocumented function discovery
- [emulation](#emulation) — 2 tool(s) · Targeted function emulation for hash resolution, crypto analysis, and controlled execution of isolated code paths
- [function](#function) — 31 tool(s) · Decompile, rename, prototype, variables, batch rename, create/delete functions
- [listing](#listing) — 20 tool(s) · Enumerate functions, strings, segments, imports, exports, namespaces, classes, data items
- [malware](#malware) — 5 tool(s) · Anti-analysis detection, suspicious instructions, IOC extraction
- [program](#program) — 22 tool(s) · Program management, script execution, memory read, bookmarks, save
- [project](#project) — 2 tool(s) · Program management, script execution, memory read, bookmarks, save
- [symbol](#symbol) — 11 tool(s) · Create/rename/delete labels, rename data, globals, external locations
- [system](#system) — 1 tool(s)
- [xref](#xref) — 11 tool(s) · Cross-references, call graphs, incoming/outgoing calls, data refs

## analysis

_Completeness analysis, control flow, similarity, crypto detection, memory inspection_

| method | path | description |
|--------|------|-------------|
| `GET` | `/analyze_control_flow` | Analyze function control flow complexity |
| `POST` | `/analyze_data_region` | Comprehensive data region analysis. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `GET` | `/analyze_dataflow` | Trace how a value propagates through a function using the decompiler's PCode graph. Direction 'backward' walks producers (Varnode.getDef); 'forward' walks consumers (Varnode.getDescendants). Terminates at constants, parameters, call boundaries, or max_steps. Phi (MULTIEQUAL) nodes are summarized rather than recursed. On programs with multiple address spaces, prefix addresses with the space name (mem:1000). |
| `GET` | `/analyze_for_documentation` | Composite analysis for RE documentation workflow. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `GET` | `/analyze_function_complete` | Comprehensive single-call function analysis. Accepts function name or address. |
| `GET` | `/analyze_function_completeness` | Check function documentation completeness. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `POST` | `/batch_analyze_completeness` | Analyze completeness for multiple functions |
| `POST` | `/detect_array_bounds` | Detect array/table size from context. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `GET` | `/find_code_gaps` | Find gaps of undefined/unanalyzed bytes in executable memory not covered by any function body. Useful for discovering missed functions in firmware and embedded binaries. Reports each contiguous uncovered range with its size, content type, and the nearest functions on each side. |
| `GET` | `/find_dead_code` | Identify unreachable code blocks |
| `GET` | `/find_next_undefined_function` | Find next function needing analysis. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `GET` | `/find_similar_functions` | Find structurally similar functions |
| `POST` | `/get_field_access_context` | Get assembly context for struct field offsets. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `GET` | `/inspect_memory_content` | Inspect memory with string detection. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `GET` | `/list_analyzers` | List available analyzers |
| `POST` | `/run_analysis` | Trigger auto-analysis on program |
| `GET` | `/search_byte_patterns` | Search for byte patterns with masks |
| `GET` | `/search_functions_enhanced` | Advanced function search with filtering |

### `GET /analyze_control_flow`
Analyze function control flow complexity

**Params**
  - `function_name*` (string, query) — Function name
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `POST /analyze_data_region`
Comprehensive data region analysis. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `address*` (string, body) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `max_scan_bytes` (integer, body) = `1024`
  - `include_xref_map` (boolean, body) = `true`
  - `include_assembly_patterns` (boolean, body) = `true`
  - `include_boundary_detection` (boolean, body) = `true`
  - `program` (string, query) = `` — Target program name

### `GET /analyze_dataflow`
Trace how a value propagates through a function using the decompiler's PCode graph. Direction 'backward' walks producers (Varnode.getDef); 'forward' walks consumers (Varnode.getDescendants). Terminates at constants, parameters, call boundaries, or max_steps. Phi (MULTIEQUAL) nodes are summarized rather than recursed. On programs with multiple address spaces, prefix addresses with the space name (mem:1000).

**Params**
  - `address*` (string, query) — Address inside the target function where the value is observed. Accepts 0x<hex> or <space>:<hex>.
  - `variable` (string, query) = `` — Anchor selector. Register name (EAX, RCX), HighVariable name (param_1, local_14, iVar1), or empty to use the PcodeOp output at the address.
  - `direction` (string, query) = `backward` — 'backward' (producers) or 'forward' (consumers).
  - `max_steps` (integer, query) = `20` — Cap on nodes visited. Default 20, max 200.
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `GET /analyze_for_documentation`
Composite analysis for RE documentation workflow. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `function_address*` (string, query) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `GET /analyze_function_complete`
Comprehensive single-call function analysis. Accepts function name or address.

**Params**
  - `name*` (string, query) — Function reference (name or address)
  - `include_xrefs` (boolean, query) = `true`
  - `include_callees` (boolean, query) = `true`
  - `include_callers` (boolean, query) = `true`
  - `include_disasm` (boolean, query) = `true`
  - `include_variables` (boolean, query) = `true`
  - `include_completeness` (boolean, query) = `false` — Include completeness scoring (undefined vars, naming violations, recommendations)
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `GET /analyze_function_completeness`
Check function documentation completeness. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `function_address*` (string, query) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `compact` (boolean, query) = `false` — Compact output
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `POST /batch_analyze_completeness`
Analyze completeness for multiple functions

**Params**
  - `addresses*` (any, body)
  - `program` (string, query) = `` — Target program name

### `POST /detect_array_bounds`
Detect array/table size from context. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `address*` (string, body) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `analyze_loop_bounds` (boolean, body) = `true`
  - `analyze_indexing` (boolean, body) = `true`
  - `max_scan_range` (integer, body) = `2048`
  - `program` (string, query) = `` — Target program name

### `GET /find_code_gaps`
Find gaps of undefined/unanalyzed bytes in executable memory not covered by any function body. Useful for discovering missed functions in firmware and embedded binaries. Reports each contiguous uncovered range with its size, content type, and the nearest functions on each side.

**Params**
  - `min_size` (integer, query) = `1` — Minimum gap size in addressable units to report (increase to filter alignment padding)
  - `offset` (integer, query) = `0`
  - `limit` (integer, query) = `100`
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `GET /find_dead_code`
Identify unreachable code blocks

**Params**
  - `function_name*` (string, query) — Function name
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `GET /find_next_undefined_function`
Find next function needing analysis. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `start_address*` (string, query) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `criteria*` (string, query) — Search criteria
  - `pattern*` (string, query) — Name pattern filter
  - `direction*` (string, query) — Search direction
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `GET /find_similar_functions`
Find structurally similar functions

**Params**
  - `target_function*` (string, query) — Function name
  - `threshold` (number, query) = `0.8` — Similarity threshold
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `POST /get_field_access_context`
Get assembly context for struct field offsets. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `struct_address*` (string, body) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `field_offset` (integer, body) = `0`
  - `num_examples` (integer, body) = `5`
  - `program` (string, query) = `` — Target program name

### `GET /inspect_memory_content`
Inspect memory with string detection. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `address*` (string, query) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `length` (integer, query) = `64` — Bytes to read
  - `detect_strings` (boolean, query) = `true` — Auto-detect strings
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `GET /list_analyzers`
List available analyzers

**Params**
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `POST /run_analysis`
Trigger auto-analysis on program

**Params**
  - `program` (string, query) = ``

### `GET /search_byte_patterns`
Search for byte patterns with masks

**Params**
  - `pattern*` (string, query) — Hex byte pattern
  - `mask` (string, query) = `` — Pattern mask (omit or leave empty for exact match)
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `GET /search_functions_enhanced`
Advanced function search with filtering

**Params**
  - `name_pattern` (string, query) = `` — Name pattern (omit to match all)
  - `min_xrefs` (integer, query) = `` — Minimum xref count filter (omit for no minimum)
  - `max_xrefs` (integer, query) = `` — Maximum xref count filter (omit for no maximum)
  - `calling_convention` (string, query) = `` — Calling convention filter (omit for any)
  - `has_custom_name` (boolean, query) = `` — Filter by whether function has a user-defined name (omit for any)
  - `is_thunk` (boolean, query) = `` — Filter by thunk classification (true=only thunks, false=exclude thunks, omit for any)
  - `is_external` (boolean, query) = `` — Filter by external classification (true=only external, false=exclude external, omit for any)
  - `regex` (boolean, query) = `false` — Use regex matching
  - `sort_by` (string, query) = `address` — Sort field
  - `offset` (integer, query) = `0`
  - `limit` (integer, query) = `100`
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)


## comment

_Set/get plate, decompiler, disassembly, repeatable comments_

| method | path | description |
|--------|------|-------------|
| `POST` | `/batch_set_comments` | Set multiple comments in one operation. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `POST` | `/clear_function_comments` | Clear all comments within a function. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `GET` | `/get_plate_comment` | Get function header/plate comment. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `POST` | `/set_decompiler_comment` | Set decompiler PRE_COMMENT at address. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `POST` | `/set_disassembly_comment` | Set disassembly EOL_COMMENT at address. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `POST` | `/set_plate_comment` | Set function header/plate comment. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |

### `POST /batch_set_comments`
Set multiple comments in one operation. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `address*` (string, body) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `decompiler_comments` (array, body) = `[]`
  - `disassembly_comments` (array, body) = `[]`
  - `plate_comment` (string, body) = `null` — Plate comment text. Omit to leave existing plate untouched. Pass empty string to explicitly clear.
  - `program` (string, query) = `` — Target program name

### `POST /clear_function_comments`
Clear all comments within a function. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `address*` (string, body) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `clear_plate` (boolean, body) = `true`
  - `clear_pre` (boolean, body) = `true`
  - `clear_eol` (boolean, body) = `true`
  - `program` (string, query) = `` — Target program name

### `GET /get_plate_comment`
Get function header/plate comment. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `address*` (string, query) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `POST /set_decompiler_comment`
Set decompiler PRE_COMMENT at address. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `address*` (string, body) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `comment*` (string, body)
  - `program` (string, query) = `` — Target program name

### `POST /set_disassembly_comment`
Set disassembly EOL_COMMENT at address. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `address*` (string, body) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `comment*` (string, body)
  - `program` (string, query) = `` — Target program name

### `POST /set_plate_comment`
Set function header/plate comment. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `address*` (string, body) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `comment*` (string, body)
  - `program` (string, query) = `` — Target program name


## datatype

_Struct/enum/union CRUD, apply data types, type conflicts, validation_

| method | path | description |
|--------|------|-------------|
| `POST` | `/add_struct_field` | Add a field to a structure |
| `POST` | `/analyze_struct_field_usage` | Analyze structure field access patterns. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `POST` | `/apply_data_classification` | Atomic type application with classification. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `POST` | `/apply_data_type` | Apply data type at address. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `GET` | `/audit_global` | Audit a global variable's documentation state. Returns name, type, length, plate comment, xref count, and list of issues. Use this before set_global so you know exactly what's missing. |
| `GET` | `/audit_globals_in_function` | Audit every global variable referenced from within a function in one call. Walks the function's instructions, collects unique data references, and returns the per-global audit (same shape as audit_global) plus a summary of how many are fully documented vs have issues. The killer per-function pre-flight tool — start every doc pass with this when the function has global xrefs. |
| `POST` | `/clone_data_type` | Clone a data type with new name |
| `POST` | `/create_array_type` | Create an array data type |
| `POST` | `/create_data_type_category` | Create a new data type category |
| `POST` | `/create_enum` | Create an enum data type |
| `POST` | `/create_function_signature` | Create a function signature data type |
| `POST` | `/create_pointer_type` | Create a pointer data type |
| `POST` | `/create_struct` | Create a structure data type. Body fields must be a JSON array of objects; each object needs name and type, with optional offset. Example fields: [{"name":"dwId","type":"uint","offset":0},{"name":"pNext","type":"void *","offset":4}]. Type may be any resolvable Ghidra data type or existing struct name. |
| `POST` | `/create_typedef` | Create a typedef alias |
| `POST` | `/create_union` | Create a union data type |
| `POST` | `/delete_data_type` | Delete a data type |
| `GET` | `/get_enum_values` | Get enum member values |
| `GET` | `/get_struct_layout` | Get structure field layout |
| `GET` | `/get_type_size` | Get data type size and info |
| `GET` | `/get_valid_data_types` | List valid Ghidra data type strings |
| `POST` | `/import_data_types` | Import data types from C source |
| `GET` | `/list_data_type_categories` | List all data type categories |
| `GET` | `/list_data_types` | List all data types with optional category filter |
| `POST` | `/modify_struct_field` | Modify a field in a structure. Fields can be identified by name or by offset (for unnamed fields). |
| `POST` | `/move_data_type_to_category` | Move data type to category |
| `POST` | `/remove_struct_field` | Remove a field from a structure |
| `GET` | `/search_data_types` | Search data types by pattern |
| `POST` | `/set_global` | Atomically apply name + type + plate-comment + array length to a global variable. Single-transaction; rejects on validation failure with no partial write. Replaces the 4-tool chain (apply_data_type → rename_data → batch_set_comments → create_label). |
| `POST` | `/suggest_field_names` | AI-assisted field name suggestions. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `GET` | `/validate_data_type` | Validate data type applicability at address. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `GET` | `/validate_data_type_exists` | Check if a data type exists |
| `GET` | `/validate_function_prototype` | Validate prototype before applying. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |

### `POST /add_struct_field`
Add a field to a structure

**Params**
  - `struct_name*` (string, body)
  - `field_name*` (string, body)
  - `field_type*` (string, body)
  - `offset` (integer, body) = `-1`
  - `program` (string, query) = `` — Target program name

### `POST /analyze_struct_field_usage`
Analyze structure field access patterns. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `address*` (string, body) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `struct_name*` (string, body)
  - `max_functions` (integer, body) = `10`
  - `program` (string, query) = `` — Target program name

### `POST /apply_data_classification`
Atomic type application with classification. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `address*` (string, body) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `classification*` (string, body)
  - `name` (string, body) = ``
  - `comment` (string, body) = ``
  - `type_definition*` (any, body)
  - `program` (string, query) = `` — Target program name

### `POST /apply_data_type`
Apply data type at address. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `address*` (string, body) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `type_name*` (string, body)
  - `clear_existing` (boolean, body) = `true`
  - `program` (string, query) = `` — Target program name

### `GET /audit_global`
Audit a global variable's documentation state. Returns name, type, length, plate comment, xref count, and list of issues. Use this before set_global so you know exactly what's missing.

**Params**
  - `address*` (string, query) — Address of the global. Accepts 0x<hex> (default space) or <space>:<hex>.
  - `program` (string, query) = `` — Target program name

### `GET /audit_globals_in_function`
Audit every global variable referenced from within a function in one call. Walks the function's instructions, collects unique data references, and returns the per-global audit (same shape as audit_global) plus a summary of how many are fully documented vs have issues. The killer per-function pre-flight tool — start every doc pass with this when the function has global xrefs.

**Params**
  - `address*` (string, query) — Address of the function (NOT a global address). Accepts 0x<hex> (default space) or <space>:<hex>.
  - `program` (string, query) = `` — Target program name

### `POST /clone_data_type`
Clone a data type with new name

**Params**
  - `source_type*` (string, body)
  - `new_name*` (string, body)
  - `program` (string, query) = `` — Target program name

### `POST /create_array_type`
Create an array data type

**Params**
  - `base_type*` (string, body)
  - `length` (integer, body) = `1`
  - `name` (string, body) = ``
  - `program` (string, query) = `` — Target program name

### `POST /create_data_type_category`
Create a new data type category

**Params**
  - `category_path*` (string, body)
  - `program` (string, query) = `` — Target program name

### `POST /create_enum`
Create an enum data type

**Params**
  - `name*` (string, body)
  - `values*` (json, body)
  - `size` (integer, body) = `4`
  - `program` (string, query) = `` — Target program name

### `POST /create_function_signature`
Create a function signature data type

**Params**
  - `name*` (string, body)
  - `return_type*` (string, body)
  - `parameters*` (string, body)
  - `program` (string, query) = `` — Target program name

### `POST /create_pointer_type`
Create a pointer data type

**Params**
  - `base_type*` (string, body)
  - `name` (string, body) = ``
  - `program` (string, query) = `` — Target program name

### `POST /create_struct`
Create a structure data type. Body fields must be a JSON array of objects; each object needs name and type, with optional offset. Example fields: [{"name":"dwId","type":"uint","offset":0},{"name":"pNext","type":"void *","offset":4}]. Type may be any resolvable Ghidra data type or existing struct name.

**Params**
  - `name*` (string, body) — New structure type name, for example UnitAny or SkillTableEntry
  - `fields*` (json, body) — JSON array of field objects. Required keys: name, type. Optional key: offset as a decimal byte offset. Alternate keys are accepted: field_name/fieldName, field_type/fieldType/data_type/dataType, field_offset/fieldOffset/off. Example: [{"name":"dwId","type":"uint","offset":0},{"name":"pNext","type":"void *","offset":4}]
  - `program` (string, query) = `` — Target program name

### `POST /create_typedef`
Create a typedef alias

**Params**
  - `name*` (string, body)
  - `base_type*` (string, body)
  - `program` (string, query) = `` — Target program name

### `POST /create_union`
Create a union data type

**Params**
  - `name*` (string, body)
  - `fields*` (json, body)
  - `program` (string, query) = `` — Target program name

### `POST /delete_data_type`
Delete a data type

**Params**
  - `type_name*` (string, body)
  - `program` (string, query) = `` — Target program name

### `GET /get_enum_values`
Get enum member values

**Params**
  - `enum_name*` (string, query) — Enum name
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `GET /get_struct_layout`
Get structure field layout

**Params**
  - `struct_name*` (string, query) — Structure name
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `GET /get_type_size`
Get data type size and info

**Params**
  - `type_name*` (string, query) — Data type name
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `GET /get_valid_data_types`
List valid Ghidra data type strings

**Params**
  - `category*` (string, query) — Category filter
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `POST /import_data_types`
Import data types from C source

**Params**
  - `source*` (string, body)
  - `format` (string, body) = `c`

### `GET /list_data_type_categories`
List all data type categories

**Params**
  - `offset` (integer, query) = `0`
  - `limit` (integer, query) = `100`
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `GET /list_data_types`
List all data types with optional category filter

**Params**
  - `category*` (string, query) — Category filter
  - `offset` (integer, query) = `0`
  - `limit` (integer, query) = `100`
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `POST /modify_struct_field`
Modify a field in a structure. Fields can be identified by name or by offset (for unnamed fields).

**Params**
  - `struct_name*` (string, body)
  - `field_name` (string, body) = `` — Field name to modify. For unnamed fields, use 'offset:N' (e.g., 'offset:16') to identify by byte offset.
  - `new_type` (string, body) = ``
  - `new_name` (string, body) = ``
  - `program` (string, query) = `` — Target program name

### `POST /move_data_type_to_category`
Move data type to category

**Params**
  - `type_name*` (string, body)
  - `category_path*` (string, body)
  - `program` (string, query) = `` — Target program name

### `POST /remove_struct_field`
Remove a field from a structure

**Params**
  - `struct_name*` (string, body)
  - `field_name*` (string, body)
  - `program` (string, query) = `` — Target program name

### `GET /search_data_types`
Search data types by pattern

**Params**
  - `pattern*` (string, query) — Search pattern
  - `offset` (integer, query) = `0`
  - `limit` (integer, query) = `100`
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `POST /set_global`
Atomically apply name + type + plate-comment + array length to a global variable. Single-transaction; rejects on validation failure with no partial write. Replaces the 4-tool chain (apply_data_type → rename_data → batch_set_comments → create_label).

**Params**
  - `address*` (string, body) — Address of the global. Accepts 0x<hex> (default space) or <space>:<hex>.
  - `name*` (string, body) — New name. Must follow g_ + Hungarian + descriptor convention (e.g., g_dwActiveQuestState, g_pUnitList).
  - `type_name*` (string, body) — Ghidra data type to apply (e.g., uint, byte, UnitAny *, char *, MyStruct). Use create_struct/create_array_type first if the type doesn't exist. Pass empty to leave type unchanged.
  - `array_length` (integer, body) = `0` — If >0, applied as an array of array_length elements of type_name. Required when documenting an array of fixed length (e.g., a 100-entry data table).
  - `plate_comment*` (string, body) — Plate comment for the address. First line must be a meaningful one-line summary (≥4 words). Optional sectioned details (Used by:, Layout:, Source:, Bitfield:) follow when applicable. Pass empty to leave plate comment unchanged.
  - `program` (string, query) = `` — Target program name

### `POST /suggest_field_names`
AI-assisted field name suggestions. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `struct_address*` (string, body) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `struct_size` (integer, body) = `0`
  - `program` (string, query) = `` — Target program name

### `GET /validate_data_type`
Validate data type applicability at address. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `address*` (string, query) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `type_name*` (string, query) — Data type name
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `GET /validate_data_type_exists`
Check if a data type exists

**Params**
  - `type_name*` (string, query) — Data type name
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `GET /validate_function_prototype`
Validate prototype before applying. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `function_address*` (string, query) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `prototype*` (string, query) — Function prototype
  - `calling_convention*` (string, query) — Calling convention
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)


## debugger

_Live debugging: attach, breakpoints, step, registers, memory. Requires a CodeBrowser with Debugger view open._

| method | path | description |
|--------|------|-------------|
| `GET` | `/debugger/dynamic_to_static` | Translate a runtime dynamic address from the current trace back to a static Ghidra program address |
| `POST` | `/debugger/interrupt` | Interrupt (break into) the running target |
| `POST` | `/debugger/launch` | Launch an executable through Ghidra's Trace RMI debugger launcher |
| `GET` | `/debugger/launch_offers` | List available debugger launch/attach options for the current program |
| `GET` | `/debugger/list_breakpoints` | List all breakpoints in the current trace |
| `GET` | `/debugger/modules` | List modules (DLLs/EXEs) loaded in the debugged process |
| `GET` | `/debugger/read_memory` | Read memory from the debugged process. Returns hex dump and DWORD interpretation. |
| `GET` | `/debugger/registers` | Read CPU registers from the current debug trace snapshot. Shows general-purpose registers (EAX-EDI, EIP, ESP, EFLAGS for x86) |
| `POST` | `/debugger/remove_breakpoint` | Remove a breakpoint at an address |
| `POST` | `/debugger/resume` | Resume execution of the debugged process |
| `POST` | `/debugger/set_breakpoint` | Set a software execution breakpoint at an address in the trace |
| `GET` | `/debugger/stack_trace` | Get the call stack backtrace for the current thread |
| `GET` | `/debugger/static_to_dynamic` | Translate a static Ghidra program address to a runtime dynamic address in the current trace |
| `GET` | `/debugger/status` | Get debugger status: active trace, thread, execution state, module count |
| `POST` | `/debugger/step_into` | Single-step into the next instruction (follows calls) |
| `POST` | `/debugger/step_out` | Step out of the current function (run to return) |
| `POST` | `/debugger/step_over` | Step over the next instruction (does not follow calls) |
| `GET` | `/debugger/traces` | List all open debug traces |

### `GET /debugger/dynamic_to_static`
Translate a runtime dynamic address from the current trace back to a static Ghidra program address

**Params**
  - `address*` (string, query) — Dynamic address from the trace

### `POST /debugger/interrupt`
Interrupt (break into) the running target

_(no params)_

### `POST /debugger/launch`
Launch an executable through Ghidra's Trace RMI debugger launcher

**Params**
  - `executable_path*` (string, body) — Absolute path to the executable to launch
  - `args` (string, body) = `` — Command-line arguments to pass to the executable
  - `cwd` (string, body) = `` — Working directory hint for launchers that expose one
  - `timeout_seconds` (integer, body) = `60` — Maximum seconds to wait for the debugger trace
  - `program` (string, body) = `` — Program path/name to use for static mapping
  - `offer` (string, body) = `` — Optional launcher title or config name, e.g. dbgeng
  - `python_executable` (string, body) = `` — Optional Python executable for Python-backed debugger launchers

### `GET /debugger/launch_offers`
List available debugger launch/attach options for the current program

**Params**
  - `program` (string, query) = `` — Program to get offers for

### `GET /debugger/list_breakpoints`
List all breakpoints in the current trace

_(no params)_

### `GET /debugger/modules`
List modules (DLLs/EXEs) loaded in the debugged process

_(no params)_

### `GET /debugger/read_memory`
Read memory from the debugged process. Returns hex dump and DWORD interpretation.

**Params**
  - `address*` (string, query) — Start address to read from
  - `size` (integer, query) = `64` — Number of bytes to read (max 4096)

### `GET /debugger/registers`
Read CPU registers from the current debug trace snapshot. Shows general-purpose registers (EAX-EDI, EIP, ESP, EFLAGS for x86)

_(no params)_

### `POST /debugger/remove_breakpoint`
Remove a breakpoint at an address

**Params**
  - `address*` (string, query) — Address of breakpoint to remove

### `POST /debugger/resume`
Resume execution of the debugged process

_(no params)_

### `POST /debugger/set_breakpoint`
Set a software execution breakpoint at an address in the trace

**Params**
  - `address*` (string, query) — Address to break at (in trace address space)

### `GET /debugger/stack_trace`
Get the call stack backtrace for the current thread

**Params**
  - `depth` (integer, query) = `20` — Maximum stack frames to return

### `GET /debugger/static_to_dynamic`
Translate a static Ghidra program address to a runtime dynamic address in the current trace

**Params**
  - `address*` (string, query) — Static address from a Ghidra program
  - `program` (string, query) = `` — Program name for context

### `GET /debugger/status`
Get debugger status: active trace, thread, execution state, module count

_(no params)_

### `POST /debugger/step_into`
Single-step into the next instruction (follows calls)

_(no params)_

### `POST /debugger/step_out`
Step out of the current function (run to return)

_(no params)_

### `POST /debugger/step_over`
Step over the next instruction (does not follow calls)

_(no params)_

### `GET /debugger/traces`
List all open debug traces

_(no params)_


## documentation

_Function hashing, cross-binary documentation, undocumented function discovery_

| method | path | description |
|--------|------|-------------|
| `POST` | `/apply_function_documentation` | Import documentation to a target function. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `POST` | `/archive_ingest_function` | Ingest a single function's documentation into the cross-version archive (re_kb.functions on bsim Postgres). Idempotent; field-level merge resolution happens on the archive side. Use archive_ingest_program for bulk. |
| `POST` | `/archive_ingest_program` | Bulk-ingest every function in a program into the cross-version documentation archive. Posts each to /v1/doc_archive/upsert. Returns per-binary counts (created / updated / conflicts_enqueued / errors). |
| `GET` | `/batch_string_anchor_report` | Report of source file strings and their FUN_* functions |
| `GET` | `/bulk_fuzzy_match` | Bulk cross-binary function matching |
| `GET` | `/compare_programs_documentation` | Compare documented vs undocumented counts |
| `GET` | `/diff_functions` | Compute structured diff between two functions. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `GET` | `/find_similar_functions_fuzzy` | Cross-binary fuzzy function matching. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `GET` | `/find_undocumented_by_string` | Find FUN_* functions referencing a string. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `GET` | `/get_bulk_function_hashes` | Get hashes for multiple or all functions |
| `GET` | `/get_function_documentation` | Export all documentation for a function. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `GET` | `/get_function_hash` | Compute normalized opcode hash for function. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `GET` | `/get_function_signature` | Get function signature for cross-binary comparison. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `POST` | `/merge_program_documentation` | Bulk merge: copy ALL RE documentation from one program to another at matching addresses, in a single server-side transaction. Categories: function names + signatures + plate comments + locals + calling convention + no-return + tags; standalone data types; data definitions (typed globals); plate comments at any address; comments at all 4 types (EOL/PRE/POST/REPEATABLE) on instructions AND data; labels & globals (with namespace preservation); external locations (ordinal renames); bookmarks; equates. Designed for the orphan-rescue workflow: source is typically '<name>_recovered', target is the original '<name>.dll'. Idempotent — re-running on an already-merged target only fills gaps. Set dry_run=true to count without writing. |

### `POST /apply_function_documentation`
Import documentation to a target function. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `json_body*` (string, body)
  - `program` (string, query) = `` — Target program name

### `POST /archive_ingest_function`
Ingest a single function's documentation into the cross-version archive (re_kb.functions on bsim Postgres). Idempotent; field-level merge resolution happens on the archive side. Use archive_ingest_program for bulk.

**Params**
  - `address*` (string, query) — Function entry-point address (Ghidra hex form)
  - `program` (string, query) = `` — Target program path/name
  - `version_override` (string, query) = `` — Override the auto-extracted version (e.g. 'PD2-S12')
  - `dry_run` (boolean, query) = `false` — Build payload but skip the POST

### `POST /archive_ingest_program`
Bulk-ingest every function in a program into the cross-version documentation archive. Posts each to /v1/doc_archive/upsert. Returns per-binary counts (created / updated / conflicts_enqueued / errors).

**Params**
  - `program` (string, query) = `` — Target program path/name
  - `version_override` (string, query) = `` — Override the auto-extracted version (e.g. 'PD2-S12')
  - `limit` (integer, query) = `0` — Stop after N functions (0 = no limit)
  - `skip_default_named` (boolean, query) = `true` — Skip functions whose name is FUN_/LAB_/etc. (default-named)
  - `dry_run` (boolean, query) = `false` — Build all payloads but skip the POSTs

### `GET /batch_string_anchor_report`
Report of source file strings and their FUN_* functions

**Params**
  - `pattern` (string, query) = `.cpp` — File pattern (e.g. .cpp)
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `GET /bulk_fuzzy_match`
Bulk cross-binary function matching

**Params**
  - `source_program*` (string, query) — Source program name
  - `target_program*` (string, query) — Target program name
  - `threshold` (number, query) = `0.7` — Similarity threshold
  - `offset` (integer, query) = `0`
  - `limit` (integer, query) = `50`
  - `filter*` (string, query) — Name filter

### `GET /compare_programs_documentation`
Compare documented vs undocumented counts

**Params**
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `GET /diff_functions`
Compute structured diff between two functions. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `address_a*` (string, query) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `address_b*` (string, query) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `program_a*` (string, query) — First program name
  - `program_b*` (string, query) — Second program name

### `GET /find_similar_functions_fuzzy`
Cross-binary fuzzy function matching. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `address*` (string, query) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `source_program*` (string, query) — Source program name
  - `target_program*` (string, query) — Target program name
  - `threshold` (number, query) = `0.7` — Similarity threshold
  - `limit` (integer, query) = `20`

### `GET /find_undocumented_by_string`
Find FUN_* functions referencing a string. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `address*` (string, query) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `GET /get_bulk_function_hashes`
Get hashes for multiple or all functions

**Params**
  - `offset` (integer, query) = `0`
  - `limit` (integer, query) = `100`
  - `filter*` (string, query) — Name filter
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `GET /get_function_documentation`
Export all documentation for a function. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `address*` (string, query) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `GET /get_function_hash`
Compute normalized opcode hash for function. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `address*` (string, query) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `GET /get_function_signature`
Get function signature for cross-binary comparison. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `address*` (string, query) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `POST /merge_program_documentation`
Bulk merge: copy ALL RE documentation from one program to another at matching addresses, in a single server-side transaction. Categories: function names + signatures + plate comments + locals + calling convention + no-return + tags; standalone data types; data definitions (typed globals); plate comments at any address; comments at all 4 types (EOL/PRE/POST/REPEATABLE) on instructions AND data; labels & globals (with namespace preservation); external locations (ordinal renames); bookmarks; equates. Designed for the orphan-rescue workflow: source is typically '<name>_recovered', target is the original '<name>.dll'. Idempotent — re-running on an already-merged target only fills gaps. Set dry_run=true to count without writing.

**Params**
  - `source*` (string, body) — Source program path or name (read-only — the rescued copy)
  - `target*` (string, body) — Target program path or name (writes go here — the original .dll)
  - `dry_run` (boolean, body) = `false` — If true, count what would be merged without writing


## emulation

_Targeted function emulation for hash resolution, crypto analysis, and controlled execution of isolated code paths_

| method | path | description |
|--------|------|-------------|
| `POST` | `/emulate_function` | Emulate a single function with controlled register/memory inputs. Returns final register state after execution. Ideal for understanding hash functions, crypto routines, or any pure-computation code path. |
| `POST` | `/emulate_hash_batch` | Brute-force API hash resolution. Emulates a hash function with each candidate API name and returns the one that produces the target hash. Ideal for resolving ROR13, CRC32, djb2, FNV, and custom hash algorithms. |

### `POST /emulate_function`
Emulate a single function with controlled register/memory inputs. Returns final register state after execution. Ideal for understanding hash functions, crypto routines, or any pure-computation code path.

**Params**
  - `address*` (string, body) — Entry point address of the function to emulate
  - `registers*` (json, body) — Initial register values as JSON: {"EAX": "0x1234", "ECX": "0x7FFE0000"}
  - `memory*` (json, body) — Memory regions to pre-populate as JSON array: [{"address": "0x7FFE0000", "data": "base64..."}] or [{"address": "0x7FFE0000", "string": "CreateProcessW\u0000"}]
  - `max_steps` (integer, body) = `10000` — Maximum P-code steps before timeout
  - `return_registers` (string, body) = `` — Comma-separated register names to return (empty = all general-purpose)
  - `program` (string, query) = ``

### `POST /emulate_hash_batch`
Brute-force API hash resolution. Emulates a hash function with each candidate API name and returns the one that produces the target hash. Ideal for resolving ROR13, CRC32, djb2, FNV, and custom hash algorithms.

**Params**
  - `hash_function_address*` (string, body) — Address of the hash computation function
  - `string_register*` (string, body) — Register that receives the pointer to the API name string (e.g., ECX, RCX, EDI)
  - `result_register` (string, body) = `EAX` — Register that contains the computed hash after emulation (e.g., EAX, RAX)
  - `target_hash*` (string, body) — Target hash value to match (hex string like 0x7C0DFCAA)
  - `candidates*` (json, body) — JSON array of candidate API name strings: ["CreateProcessW", "VirtualAlloc", ...]
  - `initial_registers` (json, body) = `` — Additional register values to set before each emulation (JSON object)
  - `wide_string` (boolean, body) = `false` — Write candidate strings as UTF-16LE (wide) instead of ASCII
  - `program` (string, query) = ``


## function

_Decompile, rename, prototype, variables, batch rename, create/delete functions_

| method | path | description |
|--------|------|-------------|
| `POST` | `/add_function_tag` | Attach one or more tags to a function. Tags are comma-separated and will be auto-created if they do not already exist. |
| `POST` | `/batch_add_function_tags` | Attach tags to many functions in one transaction. Body: [{"function":"0x140200ae6","tags":"syscall,lpe-surface"}, ...]. Tags auto-create. |
| `GET` | `/batch_decompile` | Decompile multiple functions at once. Accepts comma-separated function names or addresses. |
| `POST` | `/batch_remove_function_tags` | Detach tags from many functions in one transaction. Body shape matches /batch_add_function_tags. |
| `POST` | `/batch_rename_function_components` | Rename function and components atomically. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `POST` | `/clear_instruction_flow_override` | Clear flow override at address. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `POST` | `/create_function` | Create function at address. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `POST` | `/create_function_tag` | Create a program-wide function tag definition with an optional comment. Use add_function_tag to attach it to functions. |
| `GET` | `/decompile_function` | Decompile function at address to pseudocode. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `POST` | `/delete_function` | Delete function at address. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `POST` | `/delete_function_tag` | Delete a program-wide function tag definition. This detaches the tag from every function that had it. |
| `POST` | `/disassemble_bytes` | Disassemble a range of bytes. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `GET` | `/disassemble_function` | Get assembly listing of function. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `GET` | `/force_decompile` | Force decompiler cache refresh for function. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `GET` | `/get_function_by_address` | Get function info at a specific address. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `GET` | `/get_function_tags` | List all tags assigned to a specific function. Accepts either a function address or a function name. |
| `GET` | `/get_function_variables` | List all variables in a function. Accepts function_name (by name) or address (by address). If both are given, address takes precedence. Useful when the function was recently renamed — use address to avoid name-lookup race conditions. |
| `GET` | `/list_function_tags` | List all program-wide function tag definitions with their use counts. |
| `POST` | `/remove_function_tag` | Detach one or more tags from a function. Does not delete the program-wide tag definition — use delete_function_tag for that. |
| `POST` | `/rename_function` | Rename function by old and new name |
| `POST` | `/rename_function_by_address` | Rename function at specific address. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `POST` | `/rename_variable` | Rename a variable in a function. Accepts functionName or function_address; address is more stable after recent renames. |
| `POST` | `/rename_variables` | Rename multiple variables atomically. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `GET` | `/search_functions_by_tag` | List all functions that have a specified tag attached. Returns name + entry address. |
| `POST` | `/set_function_no_return` | Mark function as no-return. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `POST` | `/set_function_prototype` | Set function prototype (return type, parameter types, calling convention) by address. NOTE: the function name in the prototype string is used only for parsing — it does NOT rename the function. To rename, call rename_function_by_address separately. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `POST` | `/set_function_tag_comment` | Update the comment/description on an existing program-wide function tag. |
| `POST` | `/set_local_variable_type` | Set the data type of a local variable. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `POST` | `/set_parameter_type` | Set the data type of a function parameter. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `POST` | `/set_variable_storage` | Set variable storage location. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `POST` | `/set_variables` | Set types and names for multiple variables atomically. Types are applied first, then renames, in a single transaction. Hungarian prefix validation is enforced: the new name's prefix must match the type. On programs with multiple address spaces, prefix addresses with the space name. |

### `POST /add_function_tag`
Attach one or more tags to a function. Tags are comma-separated and will be auto-created if they do not already exist.

**Params**
  - `function*` (string, body) — Function address or function name
  - `tags*` (string, body) — Comma-separated tag names to attach (e.g. "syscall,lpe-surface")
  - `program` (string, query) = ``

### `POST /batch_add_function_tags`
Attach tags to many functions in one transaction. Body: [{"function":"0x140200ae6","tags":"syscall,lpe-surface"}, ...]. Tags auto-create.

**Params**
  - `assignments*` (array, body) — Array of {function, tags} objects. `function` may be an address or name; `tags` is a comma-separated list.
  - `program` (string, query) = ``

### `GET /batch_decompile`
Decompile multiple functions at once. Accepts comma-separated function names or addresses.

**Params**
  - `functions*` (string, query) — Comma-separated function references (names or addresses)
  - `program` (string, query) = ``

### `POST /batch_remove_function_tags`
Detach tags from many functions in one transaction. Body shape matches /batch_add_function_tags.

**Params**
  - `assignments*` (array, body) — Array of {function, tags} objects.
  - `program` (string, query) = ``

### `POST /batch_rename_function_components`
Rename function and components atomically. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `function_address*` (string, body) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `function_name` (string, body) = ``
  - `parameter_renames*` (object, body)
  - `local_renames*` (object, body)
  - `return_type` (string, body) = ``
  - `program` (string, query) = ``

### `POST /clear_instruction_flow_override`
Clear flow override at address. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `address*` (string, body) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `program` (string, query) = ``

### `POST /create_function`
Create function at address. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `address*` (string, body) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `name` (string, body) = ``
  - `disassemble_first` (boolean, body) = `true`
  - `program` (string, query) = ``

### `POST /create_function_tag`
Create a program-wide function tag definition with an optional comment. Use add_function_tag to attach it to functions.

**Params**
  - `name*` (string, body) — Tag name (case-sensitive; Ghidra treats whitespace-trimmed names as unique)
  - `comment` (string, body) = `` — Optional description for the tag
  - `program` (string, query) = ``

### `GET /decompile_function`
Decompile function at address to pseudocode. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `address*` (string, query) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)
  - `timeout` (integer, query) = `60` — Decompile timeout in seconds

### `POST /delete_function`
Delete function at address. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `address*` (string, body) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `program` (string, query) = ``

### `POST /delete_function_tag`
Delete a program-wide function tag definition. This detaches the tag from every function that had it.

**Params**
  - `name*` (string, body) — Tag name to delete program-wide
  - `program` (string, query) = ``

### `POST /disassemble_bytes`
Disassemble a range of bytes. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `start_address*` (string, body) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `end_address` (string, body) = `` — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `length` (integer, body) = `0`
  - `restrict_to_execute_memory` (boolean, body) = `true`
  - `program` (string, query) = ``

### `GET /disassemble_function`
Get assembly listing of function. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `address*` (string, query) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `program` (string, query) = ``

### `GET /force_decompile`
Force decompiler cache refresh for function. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `address*` (string, query) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `program` (string, query) = ``

### `GET /get_function_by_address`
Get function info at a specific address. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `address*` (string, query) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `GET /get_function_tags`
List all tags assigned to a specific function. Accepts either a function address or a function name.

**Params**
  - `function*` (string, query) — Function address (0x<hex> or <space>:<hex>) or function name
  - `program` (string, query) = ``

### `GET /get_function_variables`
List all variables in a function. Accepts function_name (by name) or address (by address). If both are given, address takes precedence. Useful when the function was recently renamed — use address to avoid name-lookup race conditions.

**Params**
  - `function_name` (string, query) = `` — Function name (ignored if address is provided)
  - `address` (string, query) = `` — Function address (hex, e.g. 6fc583f0). If provided, overrides function_name lookup.
  - `program` (string, query) = ``
  - `limit` (string, query) = `200` — Max local variables to return (default 200, 0 = unlimited)
  - `filter` (string, query) = `all` — Filter locals: 'all' (default), 'needs_work' (only needs_type or needs_rename), 'named' (only non-generic names)

### `GET /list_function_tags`
List all program-wide function tag definitions with their use counts.

**Params**
  - `offset` (integer, query) = `0`
  - `limit` (integer, query) = `500` — Maximum number of tags to return (default 500, which covers most programs in full)
  - `program` (string, query) = ``

### `POST /remove_function_tag`
Detach one or more tags from a function. Does not delete the program-wide tag definition — use delete_function_tag for that.

**Params**
  - `function*` (string, body) — Function address or function name
  - `tags*` (string, body) — Comma-separated tag names to detach
  - `program` (string, query) = ``

### `POST /rename_function`
Rename function by old and new name

**Params**
  - `oldName*` (string, body)
  - `newName*` (string, body)
  - `program` (string, query) = ``

### `POST /rename_function_by_address`
Rename function at specific address. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `function_address*` (string, body) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `new_name*` (string, body)
  - `program` (string, query) = ``

### `POST /rename_variable`
Rename a variable in a function. Accepts functionName or function_address; address is more stable after recent renames.

**Params**
  - `functionName` (string, body) = ``
  - `function_address` (string, body) = ``
  - `oldName*` (string, body)
  - `newName*` (string, body)
  - `program` (string, query) = ``

### `POST /rename_variables`
Rename multiple variables atomically. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `function_address*` (string, body) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `variable_renames*` (object, body)
  - `force_individual` (boolean, body) = `false`
  - `program` (string, query) = ``

### `GET /search_functions_by_tag`
List all functions that have a specified tag attached. Returns name + entry address.

**Params**
  - `tag*` (string, query) — Tag name to search for
  - `offset` (integer, query) = `0`
  - `limit` (integer, query) = `1000`
  - `program` (string, query) = ``

### `POST /set_function_no_return`
Mark function as no-return. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `function_address*` (string, body) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `no_return*` (boolean, body)
  - `program` (string, query) = ``

### `POST /set_function_prototype`
Set function prototype (return type, parameter types, calling convention) by address. NOTE: the function name in the prototype string is used only for parsing — it does NOT rename the function. To rename, call rename_function_by_address separately. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `function_address*` (string, body) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `prototype*` (string, body)
  - `calling_convention` (string, body) = ``
  - `program` (string, query) = `` — Target program name

### `POST /set_function_tag_comment`
Update the comment/description on an existing program-wide function tag.

**Params**
  - `name*` (string, body) — Tag name
  - `comment*` (string, body) — New comment text (pass an empty string to clear)
  - `program` (string, query) = ``

### `POST /set_local_variable_type`
Set the data type of a local variable. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `function_address*` (string, body) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `variable_name*` (string, body)
  - `new_type*` (string, body)
  - `program` (string, query) = ``

### `POST /set_parameter_type`
Set the data type of a function parameter. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `function_address*` (string, body) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `parameter_name*` (string, body)
  - `new_type*` (string, body)
  - `program` (string, query) = `` — Target program name

### `POST /set_variable_storage`
Set variable storage location. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `function_address*` (string, body) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `variable_name*` (string, body)
  - `storage*` (string, body)
  - `program` (string, query) = ``

### `POST /set_variables`
Set types and names for multiple variables atomically. Types are applied first, then renames, in a single transaction. Hungarian prefix validation is enforced: the new name's prefix must match the type. On programs with multiple address spaces, prefix addresses with the space name.

**Params**
  - `function_address*` (string, body) — Function entry point address
  - `variables*` (string, body) — JSON object mapping old variable names to {name, type} objects. Both fields optional: omit 'type' to rename only, omit 'name' to retype only. Example: {"local_8": {"name": "dwFlags", "type": "uint"}, "local_c": {"type": "int"}}
  - `program*` (string, query)


## listing

_Enumerate functions, strings, segments, imports, exports, namespaces, classes, data items_

| method | path | description |
|--------|------|-------------|
| `GET` | `/convert_number` | Convert number between hex/decimal/binary formats |
| `GET` | `/get_entry_points` | Get program entry points |
| `GET` | `/get_external_location` | Get external location details by address or DLL name |
| `GET` | `/get_function_count` | Get total function count |
| `GET` | `/list_calling_conventions` | List available calling conventions |
| `GET` | `/list_classes` | List class and namespace names with pagination |
| `GET` | `/list_data_items` | List defined data items |
| `GET` | `/list_data_items_by_xrefs` | List data items sorted by xref count (descending). By default returns only defined data items. `filter` and `type_filter` (each: all/defined/undefined) compose orthogonally to also include unnamed/untyped addresses — `filter=all,type_filter=all` returns the full data surface (named + DAT_*-style autogen + raw undefined-with-xrefs). `min_xrefs` (default 1) suppresses zero-xref noise on undefined items. |
| `GET` | `/list_exports` | List exported entry points |
| `GET` | `/list_external_locations` | List external symbol locations |
| `GET` | `/list_functions` | List all functions (no pagination) |
| `GET` | `/list_functions_enhanced` | List functions with thunk/external flags as JSON |
| `GET` | `/list_globals` | List global DATA symbols. By default returns every global in the program (named + unnamed-but-xrefed undefined addresses). `filter` and `type_filter` (each: all/defined/undefined) compose orthogonally to scope the result — e.g., `filter=named, type_filter=undefined` returns the cleanup backlog (placeholders awaiting real types). `min_xrefs` (default 1) suppresses zero-xref noise when including undefined items. Code labels (branch targets, error handlers) are still excluded — they're not data globals. Each line ends with `xrefs=N` for prioritization. |
| `GET` | `/list_imports` | List external/imported symbols |
| `GET` | `/list_methods` | List all function names with pagination |
| `GET` | `/list_namespaces` | List namespace hierarchy |
| `GET` | `/list_segments` | List memory blocks/segments |
| `GET` | `/list_strings` | List defined strings with optional filter |
| `GET` | `/search_functions` | Search functions by name pattern. Omit name_pattern to list all functions. |
| `GET` | `/search_strings` | Search strings by regex pattern. |

### `GET /convert_number`
Convert number between hex/decimal/binary formats

**Params**
  - `text*` (string, query) — Number to convert
  - `size` (integer, query) = `4` — Size in bytes

### `GET /get_entry_points`
Get program entry points

**Params**
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `GET /get_external_location`
Get external location details by address or DLL name

**Params**
  - `address*` (string, query)
  - `dll_name*` (string, query)
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `GET /get_function_count`
Get total function count

**Params**
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `GET /list_calling_conventions`
List available calling conventions

**Params**
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `GET /list_classes`
List class and namespace names with pagination

**Params**
  - `offset` (integer, query) = `0`
  - `limit` (integer, query) = `100`
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `GET /list_data_items`
List defined data items

**Params**
  - `offset` (integer, query) = `0`
  - `limit` (integer, query) = `100`
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `GET /list_data_items_by_xrefs`
List data items sorted by xref count (descending). By default returns only defined data items. `filter` and `type_filter` (each: all/defined/undefined) compose orthogonally to also include unnamed/untyped addresses — `filter=all,type_filter=all` returns the full data surface (named + DAT_*-style autogen + raw undefined-with-xrefs). `min_xrefs` (default 1) suppresses zero-xref noise on undefined items.

**Params**
  - `offset` (integer, query) = `0`
  - `limit` (integer, query) = `100`
  - `format` (string, query) = `text` — Output format (text or json)
  - `filter` (string, query) = `defined` — Symbol-naming axis: `all`, `defined` (default — only named symbols, preserves legacy behavior), `undefined` (only DAT_*-style and raw unnamed addresses).
  - `type_filter` (string, query) = `all` — Type-assignment axis: `all` (default), `defined` (only items with a real type), `undefined` (only items with `undefined*` types or no type).
  - `min_xrefs` (integer, query) = `1` — When undefined items are included, only return addresses with at least this many xrefs. Default 1 suppresses padding/alignment noise; set to 0 for the firehose.
  - `include_all_sections` (boolean, query) = `false` — By default only data sections are scanned. Pass true to include every memory section.
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `GET /list_exports`
List exported entry points

**Params**
  - `offset` (integer, query) = `0`
  - `limit` (integer, query) = `100`
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `GET /list_external_locations`
List external symbol locations

**Params**
  - `offset` (integer, query) = `0`
  - `limit` (integer, query) = `100`
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `GET /list_functions`
List all functions (no pagination)

**Params**
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `GET /list_functions_enhanced`
List functions with thunk/external flags as JSON

**Params**
  - `offset` (integer, query) = `0`
  - `limit` (integer, query) = `10000`
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `GET /list_globals`
List global DATA symbols. By default returns every global in the program (named + unnamed-but-xrefed undefined addresses). `filter` and `type_filter` (each: all/defined/undefined) compose orthogonally to scope the result — e.g., `filter=named, type_filter=undefined` returns the cleanup backlog (placeholders awaiting real types). `min_xrefs` (default 1) suppresses zero-xref noise when including undefined items. Code labels (branch targets, error handlers) are still excluded — they're not data globals. Each line ends with `xrefs=N` for prioritization.

**Params**
  - `offset` (integer, query) = `0`
  - `limit` (integer, query) = `100`
  - `filter` (string, query) = `all` — Symbol-naming axis: `all` (default), `defined` (only named symbols), `undefined` (only unnamed addresses, e.g. DAT_*-style and raw undefined data with xrefs).
  - `type_filter` (string, query) = `all` — Type-assignment axis: `all` (default), `defined` (only items with a real type), `undefined` (only items with no defined type or `undefined*` types).
  - `min_xrefs` (integer, query) = `1` — When undefined items are included, only return addresses with at least this many xrefs. Default 1 suppresses padding/alignment noise; set to 0 for the firehose.
  - `include_all_sections` (boolean, query) = `false` — By default only data sections (.data/.rdata/.bss and similar) are scanned. Pass true to include every memory section (rare — picks up .text gaps which are usually padding).
  - `name_substring` (string, query) = `` — Optional substring match against the symbol's display line (case-insensitive). Empty = no substring filter.
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `GET /list_imports`
List external/imported symbols

**Params**
  - `offset` (integer, query) = `0`
  - `limit` (integer, query) = `100`
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `GET /list_methods`
List all function names with pagination

**Params**
  - `offset` (integer, query) = `0`
  - `limit` (integer, query) = `100`
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `GET /list_namespaces`
List namespace hierarchy

**Params**
  - `offset` (integer, query) = `0`
  - `limit` (integer, query) = `100`
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `GET /list_segments`
List memory blocks/segments

**Params**
  - `offset` (integer, query) = `0`
  - `limit` (integer, query) = `100`
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `GET /list_strings`
List defined strings with optional filter

**Params**
  - `offset` (integer, query) = `0`
  - `limit` (integer, query) = `100`
  - `filter` (string, query) = `` — Substring filter
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `GET /search_functions`
Search functions by name pattern. Omit name_pattern to list all functions.

**Params**
  - `name_pattern` (string, query) = `` — Substring to match against function names (omit or leave empty to return all functions)
  - `offset` (integer, query) = `0`
  - `limit` (integer, query) = `100`
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `GET /search_strings`
Search strings by regex pattern.

**Params**
  - `search_term*` (string, query) — Regex search pattern
  - `min_length` (integer, query) = `4`
  - `encoding` (string, query) = `` — String encoding filter (omit for all encodings)
  - `offset` (integer, query) = `0`
  - `limit` (integer, query) = `100`
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)


## malware

_Anti-analysis detection, suspicious instructions, IOC extraction_

| method | path | description |
|--------|------|-------------|
| `GET` | `/analyze_api_call_chains` | Detect suspicious API call patterns |
| `GET` | `/detect_crypto_constants` | Detect crypto algorithm constants |
| `GET` | `/detect_malware_behaviors` | Detect common malware behaviors |
| `GET` | `/extract_iocs_with_context` | Enhanced IOC extraction with context |
| `GET` | `/find_anti_analysis_techniques` | Detect anti-analysis and anti-debug techniques |

### `GET /analyze_api_call_chains`
Detect suspicious API call patterns

**Params**
  - `program` (string, query) = ``

### `GET /detect_crypto_constants`
Detect crypto algorithm constants

**Params**
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `GET /detect_malware_behaviors`
Detect common malware behaviors

**Params**
  - `program` (string, query) = ``

### `GET /extract_iocs_with_context`
Enhanced IOC extraction with context

**Params**
  - `program` (string, query) = ``

### `GET /find_anti_analysis_techniques`
Detect anti-analysis and anti-debug techniques

**Params**
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)


## program

_Program management, script execution, memory read, bookmarks, save_

| method | path | description |
|--------|------|-------------|
| `GET` | `/analysis_status` | Get auto-analysis status for open programs |
| `POST` | `/close_program` | Close an open program by project path or name |
| `POST` | `/create_memory_block` | Create a new memory block. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `POST` | `/delete_bookmark` | Delete a bookmark. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `GET` | `/get_address_spaces` | List all physical address spaces in the program. On programs with multiple address spaces (e.g., embedded targets), use the returned space names to prefix addresses (e.g., mem:1000, code:ff00) for unambiguous resolution. Also check addressable_unit_size: a value > 1 means the space is word-addressed (e.g., AVR code space uses 2-byte words). MCP tools and Ghidra both use word addresses natively for such spaces — code:001478 is word 0x1478, not byte 0x1478. Do NOT multiply or divide addresses seen in Ghidra output; use them as-is. |
| `GET` | `/get_current_program_info` | Get detailed info about the active program. When multiple programs are open, call this first to confirm which program will receive tool calls that omit the program argument. |
| `GET` | `/get_metadata` | Get program metadata |
| `POST` | `/import_file` | Import a binary file from disk into the current Ghidra project and open it. For raw firmware binaries, specify language (e.g. 'ARM:LE:32:Cortex') and optionally compiler_spec (e.g. 'default'). |
| `GET` | `/list_bookmarks` | List bookmarks with optional filter. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `GET` | `/list_open_programs` | List all open programs. If more than one program is listed, always pass the program name explicitly in subsequent tool calls — omitting it will silently target the active program, which may not be the intended one. |
| `GET` | `/list_project_files` | List files in the current project |
| `GET` | `/list_scripts` | List available Ghidra scripts |
| `GET` | `/open_program` | Open a program from the current project |
| `GET` | `/read_memory` | Read raw memory bytes. Always pass the 'program' argument to target the correct binary — especially when multiple programs are open. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `POST` | `/reanalyze` | Trigger full auto-analysis on a program |
| `POST` | `/run_ghidra_script` | Execute script with output capture and timeout. Gated by GHIDRA_MCP_ALLOW_SCRIPTS=1 (v5.4.1+). |
| `POST` | `/run_script_inline` | Execute inline Ghidra script code. Pass the full Java source as the 'code' body parameter. Gated by GHIDRA_MCP_ALLOW_SCRIPTS=1 (v5.4.1+). |
| `GET` | `/save_all_programs` | Save all open programs |
| `GET` | `/save_program` | Save current program |
| `POST` | `/set_bookmark` | Create or update a bookmark. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `POST` | `/set_image_base` | Set the base address of the program (rebases all addresses) |
| `GET` | `/switch_program` | Switch MCP context to a different program |

### `GET /analysis_status`
Get auto-analysis status for open programs

**Params**
  - `program*` (string, query) — Program name (omit for all open programs)

### `POST /close_program`
Close an open program by project path or name

**Params**
  - `name*` (string, body) — Program name or project path

### `POST /create_memory_block`
Create a new memory block. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `name*` (string, body)
  - `address*` (string, body) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `size` (integer, body) = `0`
  - `read` (boolean, body) = `true`
  - `write` (boolean, body) = `true`
  - `execute` (boolean, body) = `false`
  - `volatile` (boolean, body) = `false`
  - `comment` (string, body) = ``
  - `program` (string, query) = `` — Target program name

### `POST /delete_bookmark`
Delete a bookmark. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `address*` (string, body) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `category` (string, body) = ``
  - `program` (string, query) = `` — Target program name

### `GET /get_address_spaces`
List all physical address spaces in the program. On programs with multiple address spaces (e.g., embedded targets), use the returned space names to prefix addresses (e.g., mem:1000, code:ff00) for unambiguous resolution. Also check addressable_unit_size: a value > 1 means the space is word-addressed (e.g., AVR code space uses 2-byte words). MCP tools and Ghidra both use word addresses natively for such spaces — code:001478 is word 0x1478, not byte 0x1478. Do NOT multiply or divide addresses seen in Ghidra output; use them as-is.

**Params**
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `GET /get_current_program_info`
Get detailed info about the active program. When multiple programs are open, call this first to confirm which program will receive tool calls that omit the program argument.

**Params**
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `GET /get_metadata`
Get program metadata

**Params**
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `POST /import_file`
Import a binary file from disk into the current Ghidra project and open it. For raw firmware binaries, specify language (e.g. 'ARM:LE:32:Cortex') and optionally compiler_spec (e.g. 'default').

**Params**
  - `file_path*` (string, body) — Absolute path to the binary file on disk
  - `project_folder` (string, body) = `/` — Destination folder in the Ghidra project
  - `language` (string, body) = `` — Language ID for raw binaries (e.g. 'ARM:LE:32:Cortex', 'x86:LE:64:default'). If omitted, auto-detect.
  - `compiler_spec` (string, body) = `` — Compiler spec ID (e.g. 'default', 'gcc', 'windows'). If omitted, uses language default.
  - `auto_analyze` (boolean, body) = `true` — Start auto-analysis after import

### `GET /list_bookmarks`
List bookmarks with optional filter. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `category` (string, query) = `` — Category filter (omit to return all categories)
  - `address` (string, query) = `` — Address filter (omit to return all addresses). Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `GET /list_open_programs`
List all open programs. If more than one program is listed, always pass the program name explicitly in subsequent tool calls — omitting it will silently target the active program, which may not be the intended one.

_(no params)_

### `GET /list_project_files`
List files in the current project

**Params**
  - `folder*` (string, query) — Project folder path

### `GET /list_scripts`
List available Ghidra scripts

**Params**
  - `filter` (string, query) = `` — Script name filter

### `GET /open_program`
Open a program from the current project

**Params**
  - `path*` (string, query) — Program path in project
  - `auto_analyze` (boolean, query) = `false` — Run auto-analysis

### `GET /read_memory`
Read raw memory bytes. Always pass the 'program' argument to target the correct binary — especially when multiple programs are open. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `address*` (string, query) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `length` (integer, query) = `16` — Number of bytes
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `POST /reanalyze`
Trigger full auto-analysis on a program

**Params**
  - `program` (string, query) = `` — Program name (default: current program)

### `POST /run_ghidra_script`
Execute script with output capture and timeout. Gated by GHIDRA_MCP_ALLOW_SCRIPTS=1 (v5.4.1+).

**Params**
  - `script_name*` (string, body)
  - `args` (string, body) = ``
  - `timeout_seconds` (integer, body) = `300`
  - `capture_output` (boolean, body) = `true`
  - `program` (string, query) = `` — Target program name

### `POST /run_script_inline`
Execute inline Ghidra script code. Pass the full Java source as the 'code' body parameter. Gated by GHIDRA_MCP_ALLOW_SCRIPTS=1 (v5.4.1+).

**Params**
  - `code*` (string, body)
  - `args` (string, body) = ``
  - `program` (string, query) = `` — Target program name

### `GET /save_all_programs`
Save all open programs

_(no params)_

### `GET /save_program`
Save current program

**Params**
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)

### `POST /set_bookmark`
Create or update a bookmark. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `address*` (string, body) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `category` (string, body) = ``
  - `comment` (string, body) = ``
  - `program` (string, query) = `` — Target program name

### `POST /set_image_base`
Set the base address of the program (rebases all addresses)

**Params**
  - `address*` (string, body) — New base address (e.g. 0x08000000)
  - `program` (string, query) = ``

### `GET /switch_program`
Switch MCP context to a different program

**Params**
  - `program*` (string, query) — Program name to switch to


## project

_Program management, script execution, memory read, bookmarks, save_

| method | path | description |
|--------|------|-------------|
| `POST` | `/create_folder` | Create a folder in the project |
| `POST` | `/delete_file` | Delete a file from the project |

### `POST /create_folder`
Create a folder in the project

**Params**
  - `path*` (string, body) — Project folder path to create
  - `program` (string, query) = `` — Target program name

### `POST /delete_file`
Delete a file from the project

**Params**
  - `filePath*` (string, body) — Project file path to delete


## symbol

_Create/rename/delete labels, rename data, globals, external locations_

| method | path | description |
|--------|------|-------------|
| `POST` | `/batch_create_labels` | Create multiple labels at once |
| `POST` | `/batch_delete_labels` | Delete multiple labels at once |
| `GET` | `/can_rename_at_address` | Check if address supports rename. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `POST` | `/create_label` | Create a label at address. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `POST` | `/delete_label` | Delete a label at address. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `GET` | `/get_function_labels` | Get labels within a function body. Requires the function name — if you only have an address, call get_function_by_address first to retrieve the name. |
| `POST` | `/rename_data` | Rename data at address. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `POST` | `/rename_external_location` | Rename external location. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `POST` | `/rename_global_variable` | Rename a global variable |
| `POST` | `/rename_label` | Rename a label at address. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `POST` | `/rename_or_label` | Rename or create label at address. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |

### `POST /batch_create_labels`
Create multiple labels at once

**Params**
  - `labels*` (array, body)
  - `program` (string, query) = ``

### `POST /batch_delete_labels`
Delete multiple labels at once

**Params**
  - `labels*` (array, body)
  - `program` (string, query) = ``

### `GET /can_rename_at_address`
Check if address supports rename. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `address*` (string, query) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `program` (string, query) = ``

### `POST /create_label`
Create a label at address. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `address*` (string, body) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `name*` (string, body)
  - `program` (string, query) = ``

### `POST /delete_label`
Delete a label at address. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `address*` (string, body) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `name*` (string, body)
  - `program` (string, query) = ``

### `GET /get_function_labels`
Get labels within a function body. Requires the function name — if you only have an address, call get_function_by_address first to retrieve the name.

**Params**
  - `name*` (string, query) — Function name (not an address — use get_function_by_address to resolve an address to a name first)
  - `offset` (integer, query) = `0`
  - `limit` (integer, query) = `20`
  - `program` (string, query) = ``

### `POST /rename_data`
Rename data at address. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `address*` (string, body) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `newName*` (string, body)
  - `program` (string, query) = ``

### `POST /rename_external_location`
Rename external location. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `address*` (string, body) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `new_name*` (string, body)
  - `program` (string, query) = ``

### `POST /rename_global_variable`
Rename a global variable

**Params**
  - `old_name*` (string, body)
  - `new_name*` (string, body)
  - `program` (string, query) = ``

### `POST /rename_label`
Rename a label at address. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `address*` (string, body) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `old_name*` (string, body)
  - `new_name*` (string, body)
  - `program` (string, query) = ``

### `POST /rename_or_label`
Rename or create label at address. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `address*` (string, body) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `name*` (string, body)
  - `program` (string, query) = ``


## system

| method | path | description |
|--------|------|-------------|
| `POST` | `/prompt_policy` | Temporarily enable, disable, or query scoped automation prompt handling |

### `POST /prompt_policy`
Temporarily enable, disable, or query scoped automation prompt handling

**Params**
  - `action` (string, body) = `status` — One of: enable, disable, status
  - `reason` (string, body) = `automation` — Short reason recorded in prompt-policy logs
  - `seconds` (integer, body) = `120` — How long to keep the prompt policy active


## xref

_Cross-references, call graphs, incoming/outgoing calls, data refs_

| method | path | description |
|--------|------|-------------|
| `GET` | `/analyze_call_graph` | Analyze call graph paths between functions |
| `POST` | `/get_assembly_context` | Get assembly pattern context for xref sources |
| `POST` | `/get_bulk_xrefs` | Batch cross-reference retrieval |
| `GET` | `/get_full_call_graph` | Get entire program call graph |
| `GET` | `/get_function_call_graph` | Traverse call graph from a function. Accepts function name or address. |
| `GET` | `/get_function_callees` | Get functions called by a function. Accepts function name or address. |
| `GET` | `/get_function_callers` | Get functions calling a function. Accepts function name or address. |
| `GET` | `/get_function_jump_targets` | Get jump targets within a function. Accepts function name or address. |
| `GET` | `/get_function_xrefs` | Get cross-references to a function. Accepts function name or address (pass address as 'address' param, or as 'name'). |
| `GET` | `/get_xrefs_from` | Get cross-references from an address. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |
| `GET` | `/get_xrefs_to` | Get cross-references to an address. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution. |

### `GET /analyze_call_graph`
Analyze call graph paths between functions

**Params**
  - `start_function*` (string, query) — Start function name
  - `end_function*` (string, query) — End function name
  - `analysis_type` (string, query) = `summary` — Analysis type (summary/paths/cycles)
  - `program` (string, query) = ``

### `POST /get_assembly_context`
Get assembly pattern context for xref sources

**Params**
  - `xref_sources*` (any, body)
  - `context_instructions` (integer, body) = `5`
  - `include_patterns*` (any, body)
  - `program` (string, query) = ``

### `POST /get_bulk_xrefs`
Batch cross-reference retrieval

**Params**
  - `addresses*` (any, body)
  - `program` (string, query) = ``

### `GET /get_full_call_graph`
Get entire program call graph

**Params**
  - `format` (string, query) = `edges` — Output format: edges (text), adjacency, dot, mermaid, json_edges (address-based JSON for automation)
  - `limit` (integer, query) = `1000` — Max edges to return. 0 = unlimited.
  - `program` (string, query) = ``

### `GET /get_function_call_graph`
Traverse call graph from a function. Accepts function name or address.

**Params**
  - `name` (string, query) = `` — Function name
  - `address` (string, query) = `` — Function entry-point address (hex) — alternative to name
  - `depth` (integer, query) = `2` — Traversal depth
  - `direction` (string, query) = `both` — Traversal direction (both/callers/callees)
  - `program` (string, query) = ``

### `GET /get_function_callees`
Get functions called by a function. Accepts function name or address.

**Params**
  - `name` (string, query) = `` — Function name
  - `address` (string, query) = `` — Function entry-point address (hex) — alternative to name
  - `offset` (integer, query) = `0`
  - `limit` (integer, query) = `100`
  - `program` (string, query) = ``

### `GET /get_function_callers`
Get functions calling a function. Accepts function name or address.

**Params**
  - `name` (string, query) = `` — Function name
  - `address` (string, query) = `` — Function entry-point address (hex) — alternative to name
  - `offset` (integer, query) = `0`
  - `limit` (integer, query) = `100`
  - `program` (string, query) = ``

### `GET /get_function_jump_targets`
Get jump targets within a function. Accepts function name or address.

**Params**
  - `name` (string, query) = `` — Function name
  - `address` (string, query) = `` — Function entry-point address (hex) — alternative to name
  - `offset` (integer, query) = `0`
  - `limit` (integer, query) = `100`
  - `program` (string, query) = ``

### `GET /get_function_xrefs`
Get cross-references to a function. Accepts function name or address (pass address as 'address' param, or as 'name').

**Params**
  - `name` (string, query) = `` — Function name
  - `address` (string, query) = `` — Function entry-point address (hex) — alternative to name
  - `offset` (integer, query) = `0`
  - `limit` (integer, query) = `100`
  - `program` (string, query) = ``

### `GET /get_xrefs_from`
Get cross-references from an address. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `address*` (string, query) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `offset` (integer, query) = `0`
  - `limit` (integer, query) = `100`
  - `program` (string, query) = ``

### `GET /get_xrefs_to`
Get cross-references to an address. On programs with multiple address spaces (e.g., embedded targets), prefix addresses with the space name (mem:1000) to avoid ambiguous resolution.

**Params**
  - `address*` (string, query) — Address in the program. Accepts 0x<hex> (default space) or <space>:<hex> (e.g., mem:1000, code:ff00). Note: some programs — particularly embedded/microcontroller targets — are not address-space-agnostic; use get_address_spaces to discover spaces before assuming a plain hex address is unambiguous.
  - `offset` (integer, query) = `0`
  - `limit` (integer, query) = `100`
  - `program` (string, query) = `` — Target program name (omit to use the active program — always specify when multiple programs are open)
