# HUD Subsystem — Complete Reference

Consolidated reference for the NFSMW in-race HUD. Covers the CHudWidgetArray container, its 24 widget slots, the per-frame walker (`CHudWidgetArray_Tick @ 0x58ca30`), the event-bus dispatch chain that drives the non-walker widgets, per-widget field offsets, common scene-state hashes, and modding hooks.

Pulls together discoveries from waves 8 through 17.

---

## 1. Overview — Two Update Mechanisms

NFSMW's HUD is implemented as a CFEManager screen-stack rendered through the standard FNG (FrontEnd Graphics) pipeline. The HUD logic does **not** all live on a single per-frame call list. Instead, two distinct update mechanisms coexist:

### Mechanism A — Per-frame walker (10 widgets)

A C++ object called **CHudWidgetArray** owns the entire HUD. Its vtable slot [1] is the per-frame entry point `CHudWidgetArray_Tick @ 0x58ca30`. The walker iterates a fixed list of 11 widget slot offsets (`+0x2dc, +0x2e0, +0x2e8, +0x2ec, +0x2f0, +0x310, +0x314, +0x318, +0x31c, +0x328, +0x32c`) on `this`, and for each non-NULL widget pointer calls the widget's own vt[1] (Update). A mode-filter check using widget fields [6]..[9] gates whether each widget actually ticks this frame.

These walker-ticked widgets are typically those with timers, animations, or counters that need per-frame advancement — countdowns, fading messages, animating turbo bars, scrolling radar arrows, etc.

### Mechanism B — FNG event bus (14 widgets)

Widgets that respond to discrete state changes — Speedometer (vehicle physics speed change), HeatMeter (cop pursuit heat tick), PursuitBoard (cop dispatch event), etc. — are **not** walker-ticked. Instead they register with a **type-registry** under a UI tag, and gameplay code pushes events via:

```
PostUIEventToNamedNode @ 0x516c90
   → DispatchUIEventToNamedNode @ 0x516be0
       → ScheduleUIDeferredEvent @ 0x5b7780
            → enqueues a 0x20-byte event into the FE/UI doubly-linked queue
               (head at this+0x4118, tail at this+0x411c, count at this+0x4114)
```

Each per-frame FE tick, `FE_PerFrameTick_DrainQueueAndUpdateChildren @ 0x5c53c0` calls `DrainUIDeferredEventQueue_PerFrame @ 0x5c1460`, which pops events off the queue and dispatches them to the registered widget handlers via either direct subscriber dispatch or type-registry dispatch.

This is a **push** model — widgets only Update when the underlying state changes, rather than every frame.

### Why two mechanisms?

The walker is cheap for widgets that need continuous animation. The event-bus avoids redundant per-frame recomputation for widgets bound to data that only changes occasionally (speed every physics tick, but no need to redraw if the value is the same).

---

## 2. CHudWidgetArray

### 2.1 Class layout

CHudWidgetArray is the singleton HUD container. It is constructed by **CHudWidgetArray_Ctor @ 0x5a6600** (master init), which:
1. Writes its vtable pointer (`PTR_FUN_008a2538`) to `this+0x00`.
2. Allocates and constructs each individual widget (Speedometer, Tachometer, etc.), storing the resulting pointers at fixed offsets on `this` (range `+0x2c0..+0x32c`).
3. Gates construction of certain widgets by race mode (`this+0x20`):
   - mode 1 = full HUD
   - mode 2/5/6 = drag-race subset
   - mode 3 = split-screen co-op
   - mode 4/6 = drag split
4. Optionally constructs a 0x38-byte container when `CheckMissionEntryActive(0x9b0fa0)` is true (pause overlay).

The destructor (`DestructCHudWidgetArray @ 0x5a6e00`, vt[0]) walks the same slot offsets in reverse and tears each widget down. The 29 SEH unwind funclets at `0x873790..0x873990` map state IDs back to widget destructors and the widget-name strings.

### 2.2 vtable @ 0x008a2538 (12 slots)

| Slot   | Address     | Name                                                  |
|--------|-------------|-------------------------------------------------------|
| vt[0]  | `0x005a6e00`| `DestructCHudWidgetArray`                             |
| **vt[1]**  | **`0x0058ca30`** | **`CHudWidgetArray_Tick`** — the per-frame walker |
| vt[2]  | `0x005a0c10`| `CHudWidgetArray_DestroyMaybe`                        |
| vt[3]  | `0x005a0c50`| (short fn — unnamed)                                  |
| vt[4]  | `0x00569570`| `CHudWidgetArray_SetActive` (posts ACTIVATE/DEACTIVATE) |
| vt[5]  | `0x00569680`| `CHudWidgetArray_CheckGameState` (bool predicate)     |
| vt[6]  | `0x005a0c20`| (unnamed)                                             |
| vt[7]  | `0x005695e0`| `CHudWidgetArray_SetFlag700`                          |
| vt[8]  | `0x005a0c40`| (unnamed)                                             |
| vt[9]  | `0x00569640`| (unnamed)                                             |
| vt[10] | `0x00569610`| (unnamed)                                             |
| vt[11] | `0x00595d30`| (unnamed)                                             |

---

## 3. Per-frame walker — `CHudWidgetArray_Tick @ 0x58ca30`

The single entry point that fires the HUD on every frame. Pseudocode:

```c
void CHudWidgetArray_Tick(this, param_2) {
    /* Snapshot frame state */
    uVar5 = FUN_0057ca60(this, param_2);

    /* If frame state changed, refresh widget-array's cached state */
    if (uVar5 != *(this+0x18) || uVar4 != *(this+0x1c))
        FUN_0057cdb0(this, lo, hi);

    /* Race-mode active check */
    bVar2 = FUN_00626dd0(this + 0x30);
    if (bVar2 && DAT_00925e90 != 4 && DAT_00925e90 != 5
              && DAT_0091cf28 == 0 && DAT_009885c8 == 0) {
        if (FE_IsGameStateRendering()) {
            /* Fire event 0x014035fb = "HUD render-ready" */
            event = BumpFastmemArenaCursor(0xc);
            FUN_00621e80(event, 0x014035fb);
        }
    }

    /* Visibility flip (HUD on/off based on game-master flag) */
    CHudWidgetArray_FlipVisibilityOnGameMasterChange(this);  /* 0x005696c0 */

    /* === The widget walker (inline loop unrolled in retail) === */
    for each offset in [0x2dc, 0x2e0, 0x2e8, 0x2ec, 0x2f0, 0x310, 0x314,
                        0x318, 0x31c, 0x328, 0x32c]:
        widget = *(int**)(this + offset);
        if (widget != NULL) {
            /* Mode-filter check */
            if ((widget[8] & widget[6]) != 0 || (widget[9] & widget[7]) != 0)
                (**(code **)(*widget + 4))(widget);   /* vt[1] = Update */
        }

    /* Special: +0x314 is called WITHOUT mode-filter (always on) */

    /* Mission-active overlay */
    if (*(char*)(DAT_0091cb20 + 0x1f) != 0)
        *(char*)(DAT_0091cb20 + 0x2a) = 1;

    /* Input + frame-end */
    ProcessFEngHudActionInput(this, param_1);
}
```

Key points:

- The 11 slot offsets are **hard-coded** as an unrolled list inside the function body (no real loop over an array — each slot's load + check + call is emitted inline).
- Each widget has at offsets `+0x18..+0x24` (the vt[6]..vt[9] in the code above) four 32-bit mask fields:
  - `widget[6]` = primary mode-mask A
  - `widget[7]` = primary mode-mask B
  - `widget[8]` = current game-mode mask A
  - `widget[9]` = current game-mode mask B
- A widget Updates iff `(A_curr & A_primary) != 0 OR (B_curr & B_primary) != 0`.
- The `+0x314` slot is the **only one** called unconditionally — no mode-filter check is emitted for it. NULL-check is still performed.
- The walker also broadcasts event `0x014035fb` (HUD render-ready) when the HUD is gated active, which other listeners can subscribe to (anim triggers / audio cues).

---

## 4. Widget storage map — 24 widgets at +0x2c0..+0x32c

Definitive cross-reference between `CHudWidgetArray_Ctor @ 0x5a6600` (storage offsets) and `CHudWidgetArray_Tick @ 0x58ca30` (walker offsets).

### 4.1 Full 24-widget table

| Offset    | Widget                  | Object size | Ctor          | Update         | Walker-ticked? |
|-----------|-------------------------|-------------|---------------|----------------|----------------|
| `+0x2c0`  | Speedometer             | (TBD)       | `0x59e7f0`    | `0x57a540`     | no             |
| `+0x2c4`  | Tachometer              | (TBD)       | `0x59e9d0`    | `0x57a6e0`     | no             |
| `+0x2c8`  | DragTachometer          | (TBD)       | `0x5a0ef0`    | `0x57d130`     | no             |
| `+0x2cc`  | ShiftUpdater            | (TBD)       | `0x5a0c60`    | `0x569780`     | no             |
| `+0x2d0`  | CostToState             | 0xd8        | `0x59d0c0`    | `0x5668f0`     | no             |
| `+0x2d4`  | Reputation              | (TBD)       | `0x59d2a0`    | `0x5669b0`     | no             |
| `+0x2d8`  | HeatMeterInRace         | 0x50        | `0x59cec0`    | `0x5666a0`     | no             |
| **`+0x2dc`** | **TurboMeter**       | 0x98        | `0x5a0380`    | `0x57bb40`     | **YES**        |
| **`+0x2e0`** | **EngineTempGauge**  | (TBD)       | `0x59e620`    | `0x5685e0`     | **YES**        |
| `+0x2e4`  | NitrousGauge            | 0x40        | `0x59e260`    | `0x568330`     | no             |
| **`+0x2e8`** | **SpeedBreakerMeter**| 0x48        | `0x59e420`    | (TBD)          | **YES**        |
| **`+0x2ec`** | **RaceOverMessage**  | 0x40        | `0x59e0f0`    | `0x57a4b0`     | **YES**        |
| **`+0x2f0`** | **GenericMessage**   | (TBD)       | `0x59dee0`    | `0x567f80`     | **YES**        |
| `+0x2fc`  | LeaderBoard             | (TBD)       | `0x59f0e0`    | `0x568950`     | no             |
| `+0x300`  | PursuitBoardInRace      | (TBD)       | `0x59fc80`    | `0x57aee0`     | no             |
| `+0x304`  | MilestoneBoard          | (TBD)       | `0x59f440`    | `0x57ae30`     | no             |
| `+0x308`  | BustedMeter             | (TBD)       | `0x5a01d0`    | `0x568eb0` (no-op) | no         |
| `+0x30c`  | TimeExtension           | (TBD)       | `0x5a0060`    | `0x57b780`     | no             |
| **`+0x310`** | **WrongWayIndi**     | 0x48        | `0x59ec70`    | `0x568800`     | **YES**        |
| **`+0x314`** | **(empty/always-on)** | n/a       | n/a           | n/a            | **YES** (no filter) |
| **`+0x318`** | **Countdown**        | 0x70        | `0x59dd30`    | `0x5679b0`     | **YES**        |
| **`+0x31c`** | **RadarDetector**    | 0x70        | `0x59cc30`    | `0x566170`     | **YES**        |
| `+0x324`  | GetAwayMeter            | 0x48        | `0x59ca80`    | `0x565b10` (stub) | no          |
| **`+0x328`** | **MenuZoneTrigger**  | 0x50        | `0x5a0530`    | `0x57bbc0`     | **YES**        |
| **`+0x32c`** | **Infractions**      | 0xd8        | `0x5a1380`    | `0x569a50`     | **YES**        |

Total: 24 distinct widget slot offsets, plus the `+0x314` reserved/always-on slot. The "28 widgets" string-table count from wave-8 includes a few sub-screens not tied to walker slots.

### 4.2 The `+0x314` mystery slot

`CHudWidgetArray_Tick` calls `(*(this+0x314) + 4)()` **without** the mode-filter check applied to every other slot. NULL-check is still performed. However, no `ConstructHud_*` ctor invocation in the master init writes to `+0x314`. Three possibilities:

1. Reserved / unused in retail
2. Populated by a non-ctor path (plugin / asi hook / script)
3. The master-init's own self-pointer (CHudWidgetArray as a widget of itself)

This is a **clean hook point for asi mods** — you can place a custom Update at `+0x314` and it will be called every frame with no mode gating.

---

## 5. Per-widget vtable pattern

Each individual HUD widget is a small C++ class with its **own 2-slot vtable**:

| Slot   | Role                                          |
|--------|-----------------------------------------------|
| vt[0]  | Destructor (scalar-deleting)                  |
| vt[1]  | **Update** (per-frame or per-event entry)     |

The vtable is written into the widget's `*this` field as the last `*this = &PTR_FUN_008a<XXXX>;` assignment in its constructor. Some widgets also write a *base* vtable to `this+0x0c` before the derived vtable overwrite — this is the inherited base-class vtable holding shared methods like `IGenericMessage_GetIHandle` thunks.

### 5.1 Per-widget object layout (standard)

| Offset       | Common purpose                              | Notes                                              |
|--------------|---------------------------------------------|----------------------------------------------------|
| `+0x00`      | derived vtable pointer                      | slot[0]=dtor, slot[1]=Update                       |
| `+0x0c`      | base vtable pointer                         | inherited base-class methods                       |
| `+0x10`      | FNG asset ptr (param_2 to ctor)             | `FEObject_GetObject(this+0x10, hash)` calls go here|
| `+0x18..+0x24` | mode-filter masks [6]..[9]                | walker uses these                                  |
| `+0x38..+0x4c` | cached FEObject handles                   | Resolved at ctor via DJB hash lookups              |
| `+0x50+`     | per-widget state (timers, values, ptrs)     | widget-specific                                    |

---

## 6. Walker-ticked vs event-driven widgets

### 6.1 The 10 walker-ticked widgets (mechanism A)

These have animations / counters / timers that need per-frame advancement:

| Slot      | Widget              | Update      | Role                                                |
|-----------|---------------------|-------------|-----------------------------------------------------|
| `+0x2dc`  | TurboMeter          | `0x57bb40`  | TURBO_GROUP / 3rdperson_TurboDial / TURBO_LINES anim |
| `+0x2e0`  | EngineTempGauge     | `0x5685e0`  | OVERHEAT_PULSE / ACTIVATE swap on heat-icon group   |
| `+0x2e8`  | SpeedBreakerMeter   | (TBD)       | speed-breaker meter fill                            |
| `+0x2ec`  | RaceOverMessage     | `0x57a4b0`  | one-shot finish message + anim                      |
| `+0x2f0`  | GenericMessage      | `0x567f80`  | text-prompt anim chain                              |
| `+0x310`  | WrongWayIndi        | `0x568800`  | poll global frame counter, toggle WRONGWAYIMAGE     |
| `+0x314`  | (always-on slot)    | n/a         | reserved hook point                                 |
| `+0x318`  | Countdown           | `0x5679b0`  | 321_GO_GROUP / 321_GO / 321_GO_SHADOW               |
| `+0x31c`  | RadarDetector       | `0x566170`  | Radar_DirectionArrow / Radar_Icon                   |
| `+0x328`  | MenuZoneTrigger     | `0x57bbc0`  | Engage_Mechanic prompt fade                         |
| `+0x32c`  | Infractions         | `0x569a50`  | 4-row state poller + auto-hide                      |

### 6.2 The 14 event-driven widgets (mechanism B)

These update only when underlying data changes — driven via `PostUIEventToNamedNode`:

| Slot      | Widget              | Update      | Data source                                          |
|-----------|---------------------|-------------|------------------------------------------------------|
| `+0x2c0`  | Speedometer         | `0x57a540`  | MPH/KPH attrib → SPEED_DIGIT_1/2/3 + 3rdPersonSpeedUnits |
| `+0x2c4`  | Tachometer          | `0x57a6e0`  | RPM → 3rdPersonNeedle rotation + RPM_REDLINE         |
| `+0x2c8`  | DragTachometer      | `0x57d130`  | RPM_fill + needle Rotation Z + Drag_Turbo_Backing    |
| `+0x2cc`  | ShiftUpdater        | `0x569780`  | shift state → PulseBlue/Green/Red + Shift_light      |
| `+0x2d0`  | CostToState         | `0x5668f0`  | bounty cost → CTS_GROUP APPEAR/LEAVE anim            |
| `+0x2d4`  | Reputation          | `0x5669b0`  | rep delta → in-race reputation group                 |
| `+0x2d8`  | HeatMeterInRace     | `0x5666a0`  | heat float → 10 HEAT_BASE_LED_%d toggles + HEAT_X    |
| `+0x2e4`  | NitrousGauge        | `0x568330`  | nitrous level → fill bar                             |
| `+0x2fc`  | LeaderBoard         | `0x568950`  | 4-entry table LBData_%d / LeaderText_%d              |
| `+0x300`  | PursuitBoardInRace  | `0x57aee0`  | cop count → 4+ pane reveal                           |
| `+0x304`  | MilestoneBoard      | `0x57ae30`  | per-icon value setter                                |
| `+0x308`  | BustedMeter         | `0x568eb0` (no-op) | passive — external writer pokes FNG node directly |
| `+0x30c`  | TimeExtension       | `0x57b780`  | tollbooth bonus award                                |
| `+0x324`  | GetAwayMeter        | `0x565b10` (stub) | passive — cop-distance written externally       |

Note: BustedMeter and GetAwayMeter have **no-op or stub** Update functions. These widgets are purely passive — their FNG nodes are written directly by external systems (cop-AI tick, pursuit handler). The widget cannot be modded by hooking its Update; the external writer must be patched.

---

## 7. Per-widget field offsets and FNG hashes (deep map)

Verified field offsets and node hashes for each widget. Use these for modding hooks.

### 7.1 Common scene-state hashes

These appear across multiple widgets, used in `CheckActiveSceneChildIdEquals` + `RemoveSceneNodeByName`:

| Hash         | Likely state               |
|--------------|----------------------------|
| `0x5079c8f8` | HIDDEN / OFF               |
| `0x033113ac` | VISIBLE / SHOW             |
| `0x001744b3` | OFF (alternate)            |
| `0x0016a259` | IDLE / INACTIVE            |
| `0x41e1fedc` | HeatMeter low state        |
| `0x77031c70` | HeatMeter mid state        |
| `0xda600155` | HeatMeter high state       |
| `0x13f51124` | PursuitBoard state         |
| `0x0280164f` | MenuZoneTrigger alt state  |

### 7.2 Common anim-state hashes (FNG named animations)

| Hash         | Likely anim name                                  |
|--------------|---------------------------------------------------|
| `0x8ab83edb` | "FADE_IN" / "APPEAR_BIG" (TimeExtension, RaceOverMessage) |
| `0x4f79cba2` | "HOLD" (TimeExtension mid)                        |
| `0x821e6378` | "FADE_OUT" (TimeExtension late)                   |
| `0x609f6b15` | TimeExtension secondary anim                      |
| `"APPEAR"` (DJB) | CostToState show                              |
| `"LEAVE"` (DJB)  | CostToState hide                              |

### 7.3 Common timing globals

| Address           | Role                                          |
|-------------------|-----------------------------------------------|
| `DAT_00925ae8`    | global frame counter (read by every Update)   |
| `_DAT_00890984`   | frame-to-seconds (typically 1/30.0)           |
| `_DAT_00890968`   | near-zero threshold                           |
| `_DAT_00890d3c`   | animation duration constant                   |
| `_DAT_00890bf8`   | animation mid-point                           |
| `_DAT_0089f274`   | MenuZoneTrigger fade-delay                    |
| `_DAT_0089f298`   | TimeExtension intermediate state threshold    |
| `_DAT_008933d4`   | HeatMeter LED-pulse half-life                 |

### 7.4 Per-widget internal layouts

#### RaceOverMessage @ 0x57a4b0

- Trigger: `this+0x39` set AND `player_entity_slot_array_head[iVar2*0x1c][2] == 1`. One-shot (resets `+0x39 = 0`).
- Builds UI message via `IGenericMessage_GetIHandle`:
  - `BinarySearchUIStringTable(0x4ba0d22f)` primary OR `0x9bb9ccc3` fallback
  - Anim hash `0x8ab83edb`, stack depth 5
- Mod hook: set `this+0x39 = 1` while player state == 1.

#### TimeExtension @ 0x57b780

- Trigger: TOLLBOOTH race mode only (`GetEventRaceModeId == 4`), active event at `GRaceStatus+0x1968`.
- Phase A (bonus award): `+0x40` > threshold → show TIMER_ICON, format `"%s\n+%s"` at state `0x8ab83edb`, record frame in `+0x48`.
- Phase B (fade out): time since `+0x48` > duration → animate through `0x4f79cba2` → `0x821e6378` → 0.
- UI string hashes used: `0x171471b4`, `0x862a0519`, `0x9bb9ccc3`, `0x1c074e14`.
- Calls `FUN_005fe090(g_pGRaceStatus)` (`ProcessAwardBonusTime` clear).
- Mod hook: set `this+0x40 = bonus_seconds_float` to force display.

#### Reputation @ 0x5669b0

- Trigger: `this+0x40 != 0` (data source bound).
- Counting (`+0x3c > 0`): decrement, `SetUILeafNodeIntValue(this+0x44, 0x7d0171e4)`, `ResolveUIDataValue(this+0x40, DAT_0089c2d0)`. Un-hides parent if HIDDEN.
- Done (`+0x3c <= 0`): re-hide parent if HIDDEN.
- Fields: `+0x40` = rep data ptr, `+0x3c` = countdown frames, `+0x44` = text node, `+0x48` = parent group.
- Mod hook: set `this+0x40 = rep_ptr; this+0x3c = N_frames`.

#### HeatMeterInRace @ 0x5666a0

- Trigger: always-on (no gate).
- Reads `this+0x40` (raw heat), `this+0x3c` (display heat). Clamp/lerp → `local_4`.
- `RoundFloat10ToInt64` → bucket. Compute pulse amplitudes from `local_4 - bucket`.
- Calls `FUN_00514fb0(this+0x50, ...)` and `FUN_00514fb0(this+0x54, ...)` — 2 LED-bar fill renderers.
- `SceneNode_SetFormattedTextProperty(this+0x10, 0x7f91da62, &_DAT_008a04a0)` — heat-text node `0x7f91da62`.
- Tri-state visibility:
  - `+0x44` (bar): `0x1744b3` (low) / `0x41e1fedc` (mid)
  - `+0x48` (text): `0x1744b3` / `0x77031c70` / `0xda600155`
- Mod hook: set `this+0x40 = 4.0f` to force max heat display.

#### CostToState @ 0x5668f0

- Trigger: `this+0x48 != 0`.
- Counting (`+0x44 > 0`): decrement, `SetUILeafNodeIntValue(this+0x4c, 0x3dd874c5)`, `ResolveUIDataValue(this+0x48, &DAT_0089c2d0)`. Trigger APPEAR if not already showing.
- Done (`+0x44 <= 0`): trigger LEAVE if was active (`+0x38`).
- Anim names: literal strings "APPEAR" / "LEAVE" (DJB-hashed at runtime).
- Fields: `+0x38` = was-shown, `+0x44` = countdown, `+0x48` = data, `+0x4c` = text leaf.
- Mod hook: set `this+0x48 = cost_ptr; this+0x44 = N_frames`.

#### PursuitBoardInRace @ 0x57aee0 (largest — 238 lines)

- Multi-pane (panes at `+0x70, +0x74, +0x78, +0x7c, +0x80`).
- Off (`this+0x38 == 0`): hide every pane (state `0x5079c8f8` check + remove). Early return.
- On: progressively reveal panes from float at `+0x40` (active-cop count vs `_DAT_00890da8`). State hashes `0x33113ac`, `0x13f51124`, `0x16a259`, `0x5079c8f8`.
- Data resolve: `ResolveUIDataValue(this+0x88, ...)`, `(this+0x9c, ...)`.
- Mod hook: `this+0x38 = 1; this+0x40 = N` fakes N active cops.

#### BustedMeter @ 0x568eb0

- Update is literally a no-op (11-byte `ret;` function).
- Widget is shown by FNG itself based on data poked externally (cop-AI / pursuit handler).
- Mod hook: must hook the EXTERNAL writer — Update interception will not work.

#### MenuZoneTrigger @ 0x57bbc0

- Trigger: `this+0x4c` (show flag) or active timer at `+0x50`.
- Show: clear flag, record start-frame, hide old prompt (`+0x40` group), show new prompt (node `0xa206a0b4`).
- Hide (after `_DAT_0089f274` frames): hide current, cleanup `FUN_00569190`, show alt (node `0xa729b1b`).
- Audio: `EntityRouter_DispatchByIdRange(g_pNFSMixMaster, 0x13)`.
- Fields: `+0x4c` show, `+0x4d` visible mirror, `+0x50` start frame, `+0x3c`/`+0x40` old/new pane.
- Mod hook: set `this+0x4c = 1` to force a prompt.

#### Infractions @ 0x569a50

- 4-row state poller. Iterates 4 dword ptrs at `this+0x3c..+0x48`.
- Each checked for IDLE state (`0x16a259`). If any non-IDLE → early-return.
- All IDLE: if parent at `+0x38` is HIDDEN (`0x5079c8f8`) or `0x3826a28` → hide via `RemoveSceneNodeByName(0x33113ac)`.
- Net: auto-hide infractions panel when all 4 slots idle.
- Entries are WRITTEN externally (cop-AI infraction events).
- Mod hook: patch external infraction-writer for custom entries.

#### RadarDetector @ 0x566170 (181 lines)

- Reads master state: `*(int *)(DAT_0091cf90 + 0x10) + 0x39` (active player pursuit flag).
- Two-pane: `+0x38` cop-direction, `+0x4c`/`+0x50` indicator panes.
- Pursuit active + state != 2 → cone display (state `0x1744b3`).
- Pursuit active + state == 2 → alert state (`0x16a259`).
- Visibility flags `+0x64`/`+0x65` gate everything.
- Plays "Snd" event via stringhash32 on transitions.
- Fields: `+0x38` cone, `+0x4c`/`+0x50` indicators, `+0x64`/`+0x65` visibility, `+0x68` state-change frame.
- Mod hook: override `+0x64`/`+0x65` to force-show / hide.

---

## 8. Universal patterns

### 8.1 Hash families used

NFSMW HUD code uses TWO hash algorithms:

- **CalculateDjbStringHashCaseInsensitive** — for FNG anim names ("APPEAR", "LEAVE") and most node IDs.
- **stringhash32** — for event hashes ("Snd"), likely a DJB variant.
- Pre-computed FNG node hashes (`0x5079c8f8`, `0x33113ac`, etc.) are DJB hashes of FNG element names.

These are **NOT** bChunk (Jenkins mix3) hashes — that's the asset-bundle hash family, separate from FE/UI.

### 8.2 Common ctor pattern

```c
CHudFoo_Ctor(this, asset_ptr, controller, ...) {
    /* Zero this+0x10..+0x80 */
    *(void **)(this+0x10) = asset_ptr;
    
    /* Resolve FNG handles via DJB hash */
    *(void **)(this+0x38) = FEObject_GetObject(asset_ptr, 0xXXXXXXXX);
    *(void **)(this+0x3c) = FEObject_GetObject(asset_ptr, 0xYYYYYYYY);
    /* ... more handles ... */
    
    /* Write base vtable then derived vtable */
    *(void **)(this+0x0c) = &PTR_BASE_VTABLE;
    *(void **)(this+0x00) = &PTR_DERIVED_VTABLE;
    
    /* For event-bus widgets: register with type-registry */
    InsertOrAssignTypeRegistry(controller, &type_tag_lambda, this);
    
    return this;
}
```

### 8.3 Common Update pattern

```c
CHudFoo_Update(this, param_1) {
    /* Gate check */
    if (this->state_flag == 0) return;
    
    /* Read data source */
    val = ResolveUIDataValue(this+0x40, ...);
    
    /* Timer advance using global frame counter */
    frames_elapsed = DAT_00925ae8 - this->start_frame;
    
    /* Drive FNG sub-elements */
    SceneNode_SetFormattedTextProperty(this+0x10, NODE_HASH, &fmt_args);
    /* OR */
    if (CheckActiveSceneChildIdEquals(this+0x10, 0x5079c8f8))
        RemoveSceneNodeByName(this+0x10, 0x33113ac);
}
```

---

## 9. FNG event-bus full chain

The complete dispatch path from "gameplay state change" to "widget redraw" for the 14 non-walker widgets.

### 9.1 End-to-end flow diagram

```
[gameplay/system code]
   |
   v
PostUIEventToNamedNode @ 0x516c90
   |
   v
DispatchUIEventToNamedNode @ 0x516be0
   |--- if name==NULL --> fan out via subscriber list at (*this+0xe0)
   |
   `-- if name!=NULL --> FindSceneNodeByName(name) -->
                          ScheduleUIDeferredEvent @ 0x5b7780
                             |
                             |-- if (this+0x524e): synchronous dispatch
                             |       via (*this+0x108+0x54)()
                             |
                             `-- enqueue 0x20-byte event into doubly-linked
                                 list at:
                                   this+0x4118 = head ptr
                                   this+0x411c = tail ptr
                                   this+0x4114 = count
                                 vtable PTR_FUN_008a2c90, fence 0xABADCAFE x2

[per-frame tick]
   |
   v
FE_PerFrameTick_DrainQueueAndUpdateChildren @ 0x5c53c0
   |
   |-- if (this+0x524e): dispatch sync queue via (*this+0x108+0x5c)()
   |-- iterate (this+0xd0) child handlers, call FUN_005ae960 per slot
   |-- iterate (this+0xe0) subscriber list (full per-handler tick)
   |
   `-- DrainUIDeferredEventQueue_PerFrame @ 0x5c1460
         For each event in queue (this+0x4118 -> ... -> null):
           UnlinkSceneNodeChild(this+0x4110, event)
           Read event[4] = target marker:
             0xfffffffc --> broadcast to all subscribers (this+0xe0)
             0xfffffffa --> alt-broadcast
             NULL       --> type-registry broadcast
             ptr        --> direct call into target node's handler
           Dispatch via:
             DispatchUIEvent_ToSubscriberHandler @ 0x5bbc00 (direct)
             DispatchUIEvent_ToTypeRegistrySubscribers @ 0x5beaa0 (type-registry)
```

### 9.2 Queue owner field layout

The FE/UI context (typically `g_pUIRootContext @ 0x91cadc` or a child screen) is the queue owner:

| Offset    | Field                              | Notes                                            |
|-----------|------------------------------------|--------------------------------------------------|
| `+0x0e0`  | Subscriber list head               | Registered handlers                              |
| `+0x0d0`  | Child handler count                | Slots in handler array                           |
| `+0x108`  | Sync-dispatch vtable               | `*+0x54` sync schedule, `*+0x5c` sync drain      |
| `+0x4110` | Queue-node root vtable             | `PTR_LAB_008a2c18` for UnlinkSceneNodeChild      |
| **`+0x4114`** | **Event count**                | Incremented on Schedule                          |
| **`+0x4118`** | **Queue head ptr**             | First event to drain                             |
| **`+0x411c`** | **Queue tail ptr**             | Last event                                       |
| `+0x524e` | Sync-dispatch enable flag          | If set: dispatch immediately AND queue           |

### 9.3 Event object layout (0x20 bytes)

| Offset | Field                                                       |
|--------|-------------------------------------------------------------|
| `+0x00`| vtable `PTR_FUN_008a2c90`                                   |
| `+0x04`| prev ptr (debug fence: `0xABADCAFE` initial)                |
| `+0x08`| next ptr (debug fence: `0xABADCAFE` initial)                |
| `+0x0c`| param_2 caller payload                                      |
| `+0x10`| event hash                                                  |
| `+0x14`| event command/value (param_1 in Post)                       |
| `+0x18`| target node ptr or sentinel (`0xfffffffc/0xfffffffa/NULL`)  |
| `+0x1c`| priority                                                    |

### 9.4 How a non-walker widget gets its Update

Concrete example for Speedometer:

1. Ctor calls `InsertOrAssignTypeRegistry(controller, &LAB_00565120, &widget_data)` — registers the widget under a TYPE tag.
2. Gameplay code (`pvehicle_AggregatePhysicsState @ 0x694160`) eventually calls `PostUIEventToNamedNode(ui_root, event_hash, "SPEED_DIGIT_1", ...)` when speed changes.
3. Event is enqueued at `ui_root+0x4118`.
4. Next FE tick: `FE_PerFrameTick_DrainQueueAndUpdateChildren` calls the drainer.
5. Drainer finds the target node (`"SPEED_DIGIT_1"`) and calls `DispatchUIEvent_ToTypeRegistrySubscribers`.
6. Type-registry lookup → Speedometer's registered handler → `CHudSpeedometer_Update @ 0x57a540` is invoked with the new speed value.

So non-walker widgets are **event-driven (push)**, not tick-driven (pull). More efficient for sparse updates than the walker.

The 10 walker-ticked widgets are walker-ticked specifically because they have **animations or counters** that need to advance constantly (countdown timers, fading prompts, animating turbo bars).

---

## 10. Type-registry system

Used by the event-bus to bind a widget's Update to a UI tag without going through a named node lookup. Pattern:

### 10.1 Binding (in widget ctor)

```c
InsertOrAssignTypeRegistry(controller, &type_tag_lambda, widget_this);
```

- `controller` — the UI context / screen-stack object
- `type_tag_lambda` — a static `LAB_*` address that acts as a unique tag (the address-as-key idiom)
- `widget_this` — the widget instance to bind

### 10.2 Dispatch (in drainer)

When `DispatchUIEvent_ToTypeRegistrySubscribers @ 0x5beaa0` receives an event with target marker NULL, it looks up all widgets registered under the event's tag, then calls each widget's Update with the event payload.

### 10.3 The 7 type-registry functions

Six additional helper functions in the registry family (slot insert, lookup, iterate, remove). Internal field mapping still partial — wave-17 left the layout open. Sufficient for modding via interception of the entry points listed above.

---

## 11. Modding hooks — comprehensive list

Organized by goal.

### 11.1 Intercept all HUD updates at once

Hook **`CHudWidgetArray_Tick @ 0x58ca30`** (vt[1] of CHudWidgetArray vtable @ `0x008a2538`). Every per-frame HUD pass goes through this — log, modify, or skip the walker entirely.

Alternative: replace `vt[1]` at `0x008a2538+4` to redirect to your function.

### 11.2 Add a custom always-on widget

The **`+0x314` slot** on CHudWidgetArray is called every frame without mode-filtering. Allocate a small widget object with at least a vtable pointer, set vt[1] = your Update function, and write the pointer into `*(CHudWidgetArray+0x314)`. The walker will call you every frame.

### 11.3 Force-tick a normally-gated widget

Each walker-ticked widget has mode-filter masks at `widget[6..9]`. Setting all four to `0xFFFFFFFF` (`widget[6] = widget[7] = -1` and `widget[8] = widget[9] = -1`) makes the mask intersection always non-zero → widget Updates every frame regardless of game mode.

### 11.4 Skip a widget

Zero the mode-filter masks: `widget[6] = widget[7] = widget[8] = widget[9] = 0`. Walker calls won't fire.

### 11.5 Replace a widget's Update

Patch the widget's vtable slot[1]:
1. Find widget pointer at `CHudWidgetArray + offset` (see section 4.1 table).
2. Read `*widget` = vtable pointer.
3. Patch `*(vtable + 4)` to your Update.

### 11.6 Force a one-shot widget to fire

Per widget — set the appropriate trigger field (section 7.4 mod-hook entries):
- RaceOverMessage: `this+0x39 = 1`
- TimeExtension: `this+0x40 = bonus_seconds`
- Reputation: `this+0x40 = rep_ptr; this+0x3c = N`
- CostToState: `this+0x48 = ptr; this+0x44 = N`
- MenuZoneTrigger: `this+0x4c = 1`
- HeatMeter: `this+0x40 = 4.0f`
- PursuitBoard: `this+0x38 = 1; this+0x40 = N`

### 11.7 Intercept event-bus dispatch

| Goal                                       | Hook point                                       |
|--------------------------------------------|--------------------------------------------------|
| Intercept ALL FNG events being posted      | `PostUIEventToNamedNode @ 0x516c90`              |
| Block events for a specific node           | `DispatchUIEventToNamedNode @ 0x516be0`, filter by node hash |
| Block one event hash globally              | `ScheduleUIDeferredEvent @ 0x5b7780`, filter by hash |
| Drain queue manually (force flush)         | Call `DrainUIDeferredEventQueue_PerFrame @ 0x5c1460` |
| Inject a fake event                        | Construct 0x20-byte event (vtable=`0x8a2c90`, fence=`0xABADCAFE`), link into list at +0x4118 |
| Subscribe to HUD render-ready signal       | Listen for event hash `0x014035fb` (fired by walker) |

### 11.8 Override scene-state visibility

Use the common state hashes from section 7.1 to drive any FNG scene node:
- `RemoveSceneNodeByName(node, 0x33113ac)` → show (transition to VISIBLE state)
- `RemoveSceneNodeByName(node, 0x5079c8f8)` → hide
- `CheckActiveSceneChildIdEquals(node, hash)` → query current state

### 11.9 Replace HUD layout entirely

Replace one of the HUD FNG bundle files:
- `HUD_SingleRace.fng` — default in-race
- `HUD_Drag.fng` — drag-race
- `HUD_Player1.fng` / `HUD_Player2.fng` — split-screen
- `HUD_Drag_Player1.fng` / `HUD_Drag_Player2.fng` — split-screen drag
- `CustomHUD.fng` / `CustomHUDColor.fng` — paint-preview

The C++ widget code looks up element handles by DJB hash. As long as the new FNG bundle preserves the element names (or you patch the hashes used in ctors), the new layout will be picked up.

### 11.10 Selector override

`HUDFNGSelector_GetActiveScreenName @ 0x005694e0` returns which HUD FNG to display. Hook it to force a specific HUD variant regardless of race mode.

### 11.11 Hooking the BustedMeter / GetAwayMeter (passive widgets)

These widgets have no-op or stub Updates. Their data is poked by external systems:
- BustedMeter — fed by cop-AI tick / pursuit handler (TBD)
- GetAwayMeter — fed by cop-distance calc (TBD)

To mod: identify the external writer (memory-breakpoint on the FNG node fields or on the widget's `this+0x40`-ish data field), then hook there.

---

## Appendix A — Key globals

| Address          | Role                                                        |
|------------------|-------------------------------------------------------------|
| `DAT_0091cf90`   | CFEManager root (HUD/screen flag bits at +0x12c/+0x300)     |
| `DAT_0091cadc`   | UI root context (FNG scene-graph head)                      |
| `DAT_00925ae8`   | global frame counter                                        |
| `g_pGRaceStatus + 0x1968` | active event handle (race-mode selector)           |
| `g_pGRaceStatus + 0x1964` | race-mode index (drag/split-screen gate)           |
| `DAT_0091e0d0`   | audio command queue (NFSMixMaster)                          |
| `DAT_00925e90`   | game-state enum (4/5 = paused/menu)                         |
| `DAT_0091cf28`   | modal overlay flag                                          |
| `DAT_009885c8`   | secondary modal flag                                        |
| `DAT_0091cb20`   | mission state context                                       |

## Appendix B — Key code addresses (quick index)

| Address     | Function                                                          |
|-------------|-------------------------------------------------------------------|
| `0x516be0`  | `DispatchUIEventToNamedNode`                                      |
| `0x516c90`  | `PostUIEventToNamedNode`                                          |
| `0x569570`  | `CHudWidgetArray_SetActive` (vt[4])                               |
| `0x569680`  | `CHudWidgetArray_CheckGameState` (vt[5])                          |
| `0x5694e0`  | `HUDFNGSelector_GetActiveScreenName`                              |
| `0x5695e0`  | `CHudWidgetArray_SetFlag700` (vt[7])                              |
| `0x5696c0`  | `CHudWidgetArray_FlipVisibilityOnGameMasterChange`                |
| `0x58ca30`  | `CHudWidgetArray_Tick` (vt[1]) — the walker                       |
| `0x595d40`  | `CheckShouldShowPauseOrMovieDuringHud`                            |
| `0x5a6600`  | `CHudWidgetArray_Ctor` — master widget init                       |
| `0x5a6e00`  | `DestructCHudWidgetArray` (vt[0])                                 |
| `0x5b7780`  | `ScheduleUIDeferredEvent`                                         |
| `0x5bbc00`  | `DispatchUIEvent_ToSubscriberHandler`                             |
| `0x5beaa0`  | `DispatchUIEvent_ToTypeRegistrySubscribers`                       |
| `0x5c12f0`  | `ConstructUIDeferredQueueOwner`                                   |
| `0x5c1460`  | `DrainUIDeferredEventQueue_PerFrame`                              |
| `0x5c20a0`  | `FE_AlternateUpdate_DrainQueue`                                   |
| `0x5c53c0`  | `FE_PerFrameTick_DrainQueueAndUpdateChildren`                     |
| `0x648590`  | `RegisterPursuitBountyEventListeners` (audio listeners, NOT HUD)  |
| `0x6e7220`  | `D3D9_PerFrame_RenderAndPresent` — main render entry              |
| `0x694160`  | `pvehicle_AggregatePhysicsState` — speedo/tach data source        |

## Appendix C — Vtable anchors

| Address       | Vtable owner                                  |
|---------------|-----------------------------------------------|
| `0x008a2538`  | CHudWidgetArray vtable (12 slots)             |
| `0x008a21cc`  | CHudSpeedometer base                          |
| `0x008a21d4`  | CHudSpeedometer derived                       |
| `0x008a2168`  | CHudEngineTempGauge base                      |
| `0x008a2248`  | CHudTachometer base                           |
| `0x008a2260`  | CHudTachometer derived                        |
| `0x008a2618`  | CHudDragTachometer base                       |
| `0x008a1ee0`  | CHudGetAwayMeter base                         |
| `0x008a1ee8`  | CHudGetAwayMeter derived                      |
| `0x008a2278`  | CHudWrongWayIndi base                         |
| `0x008a2280`  | CHudWrongWayIndi derived                      |
| `0x008a23f8`  | CHudMilestoneBoard base                       |
| `0x008a2420`  | CHudMilestoneBoard derived                    |
| `0x008a234c`  | CHudLeaderBoard base                          |
| `0x008a237c`  | CHudLeaderBoard derived                       |
| `0x008a2040`  | CHudMinimap (single vtable)                   |
| `0x008a25b8`  | CHudShiftUpdater base                         |
| `0x008a25c8`  | CHudShiftUpdater derived                      |
| `0x008a20bc`  | CHudNitrousGauge base                         |
| `0x008a20c4`  | CHudNitrousGauge derived                      |
| `0x008a20ac`  | CHudRaceOverMessage base                      |
| `0x008a20a4`  | CHudRaceOverMessage derived                   |
| `0x008a2088`  | CHudGenericMessage base                       |
| `0x008a209c`  | CHudGenericMessage derived                    |
| `0x008a24c0`  | CHudTurboMeter base                           |
| `0x008a24c8`  | CHudTurboMeter derived                        |
| `0x008a2070`  | CHudCountdown base                            |
| `0x008a2080`  | CHudCountdown derived                         |
| `0x008a2470`  | CHudTimeExtension base                        |
| `0x008a247c`  | CHudTimeExtension derived                     |
| `0x008a1f6c`  | CHudReputation base                           |
| `0x008a1f78`  | CHudReputation derived                        |
| `0x008a1f44`  | CHudHeatMeter_InRace base                     |
| `0x008a1f50`  | CHudHeatMeter_InRace derived                  |
| `0x008a1f58`  | CHudCostToState base                          |
| `0x008a1f64`  | CHudCostToState derived                       |
| `0x008a2428`  | CHudPursuitBoard_InRace base                  |
| `0x008a2468`  | CHudPursuitBoard_InRace derived               |
| `0x008a248c`  | CHudBustedMeter base                          |
| `0x008a2484`  | CHudBustedMeter derived                       |
| `0x008a24f8`  | CHudMenuZoneTrigger base                      |
| `0x008a2524`  | CHudMenuZoneTrigger derived                   |
| `0x008a2684`  | CHudInfractions base                          |
| `0x008a268c`  | CHudInfractions derived                       |
| `0x008a1f2c`  | CHudRadarDetector base                        |
| `0x008a1f3c`  | CHudRadarDetector derived                     |
| `0x008a2c18`  | UI deferred queue-node root vtable (LAB)      |
| `0x008a2c90`  | UI deferred event vtable                      |

## Appendix D — Event hashes of interest

| Hash         | Meaning                                                       |
|--------------|---------------------------------------------------------------|
| `0x014035fb` | HUD render-ready / new HUD frame begin (fired by Tick)        |
| `0x20d60dbf` | PursuitBountyAwarded (NOT HUD — 65 audio listeners only)      |
| `0x4ba0d22f` | RaceOverMessage primary string                                |
| `0x9bb9ccc3` | RaceOverMessage / TimeExtension fallback string               |
| `0x171471b4` | TimeExtension UI string                                       |
| `0x862a0519` | TimeExtension UI string                                       |
| `0x1c074e14` | TimeExtension UI string                                       |
| `0x3dd874c5` | CostToState text leaf hash                                    |
| `0x7d0171e4` | Reputation text node hash                                     |
| `0x7f91da62` | HeatMeter heat-text node                                      |
| `0xa206a0b4` | MenuZoneTrigger show prompt                                   |
| `0x0a729b1b` | MenuZoneTrigger hide / alt prompt                             |
| `0x8ab83edb` | "FADE_IN" / "APPEAR_BIG" anim                                 |
| `0x4f79cba2` | "HOLD" anim                                                   |
| `0x821e6378` | "FADE_OUT" anim                                               |
| `0x609f6b15` | TimeExtension secondary anim                                  |

---

End of HUD subsystem reference.
