---
name: GhidraMCP v5.7.1 features and conventions
description: How to use the new function-tag, set_global, and audit endpoints in bethington/ghidra-mcp v5.7.1
type: feedback
originSessionId: c4edf485-e85f-4e2f-ac31-e021ba66e8d6
---
The bethington/ghidra-mcp plugin upgraded from v5.6.0 → v5.7.1 (177 → 193 live tools, +23 endpoints). Key new features and the conventions they enforce:

## Function tags (10 endpoints)

The `Render / Streamer / Input / Physics / AI / Engine / Hash / Boot` tags are already created on the speed.exe project — query any subset with:

```
GET /search_functions_by_tag?tag=Render&limit=100
```

Add new tags via `POST /create_function_tag {name, comment}`. Apply via single `POST /add_function_tag {function, tags}` or batch:

```
POST /batch_add_function_tags
{ "assignments": [
    {"function":"D3D9_CreateDeviceAndFirstPresent","tags":"Render"},
    {"function":"D3D9_BuildPresentParameters","tags":"Render"}
  ]
}
```

The batch form returns `{status, functions_touched, tags_added, results: [...]}` and is **much** faster than looping single calls.

## set_global enforces Hungarian convention

`POST /set_global` is the new atomic 4-in-1 (rename + type + plate-comment + array-length). It rejects names that don't follow the project convention:

- Must start with `g_`
- Must have a recognized Hungarian prefix after `g_`: `dw` (DWORD), `n`/`int`, `p`/`ptr` (pointer), `sz` (char*/string), `ab` (byte[]), `pfn` (function ptr), `uint`
- `type_name` and `plate_comment` are required body params

Examples that worked: `g_pIDirect3D9Factory`, `g_pIDirect3DDevice9`, `g_dwD3DPresentParametersBlock`, `g_dwRenderInitStartedFlag`. Examples rejected: `render_init_started_flag` (no `g_`), `g_hwndGameFrame` (`hwnd` isn't on the prefix whitelist — use `p` instead).

The plugin returns helpful suggestions on rejection. Use `create_label` instead of `set_global` for labels that don't fit the Hungarian rules; the new endpoint is for *fully-documented* globals only.

## audit_global / audit_globals_in_function

`GET /audit_global?address=0xNNNN` returns the global's name, type, length, plate-comment, xref count, and a list of issues with severity buckets (hard/medium/soft). Issues include `generic_name`, `untyped`, `missing_plate_comment`, `name_missing_g_prefix`, `xref_summary_missing`.

`GET /audit_globals_in_function?address=0xNNNN` walks every instruction in a function and audits each unique data-ref. Returns the same shape per global. Use to prioritize: ignore softs, fix hards. RenderAndWindow_Initialize has 52 globals; only ~2 are fully documented even after careful renaming.

## search_functions_enhanced now has isThunk/isExternal

```
GET /search_functions_enhanced?name_pattern=^FUN_&regex=true
   &is_thunk=false&is_external=false
   &min_xrefs=200&sort_by=xref_count&limit=15
```

Filters out import thunks and external symbols — directly surfaces real internal functions sorted by xref count. Useful for "find me the most-called unnamed code".

## When to call switch_program

The plugin's "current program" defaults to whichever was last touched. After Ghidra restart, it may default to the wrong binary in a multi-program session. Always confirm with `GET /get_metadata` first; if wrong:

```
POST /switch_program
{ "program": "speed.exe" }
```

The endpoint returns `{"error":"Program name is required"}` even on success — that response is misleading; check `/get_metadata` to verify.

## Rebuild + restart

To upgrade the plugin: pull the source repo (`git -C ~/tools/ghidra-mcp pull`), download the prebuilt ZIP from the GitHub release, extract over `~/.config/ghidra/ghidra_12.0.4_DEV/Extensions/GhidraMCP/`, **delete the old JAR** in `lib/` (the new one ships alongside it otherwise Ghidra picks the wrong one), then close + restart Ghidra. The HTTP server resumes on the same port.
