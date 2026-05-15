---
name: hud-per-frame-walker-discovered-wave-13
description: "CHudWidgetArray_Tick @ 0x58ca30 is the per-frame HUD walker. Widget slots are inline at fixed offsets (0x2dc..0x32c on CHudWidgetArray). Each widget calls (*widget->vt[1])() if mode-filter bits match current game mode. Closes wave-9 open question."
metadata: 
  node_type: memory
  type: project
  originSessionId: c4edf485-e85f-4e2f-ac31-e021ba66e8d6
---

## CHudWidgetArray vtable @ 0x008a2538 (12 slots)

| Slot | Address | Name |
|---|---|---|
| vt[0] | `0x005a6e00` | `DestructCHudWidgetArray` |
| **vt[1]** | **`0x0058ca30`** | **`CHudWidgetArray_Tick`** ← THE PER-FRAME WALKER |
| vt[2] | `0x005a0c10` | `CHudWidgetArray_DestroyMaybe` |
| vt[3] | `0x005a0c50` | (un-named — short fn) |
| vt[4] | `0x00569570` | `CHudWidgetArray_SetActive` (posts ACTIVATE/DEACTIVATE UI events) |
| vt[5] | `0x00569680` | `CHudWidgetArray_CheckGameState` (bool: this widget array active for current game state?) |
| vt[6] | `0x005a0c20` | (un-named) |
| vt[7] | `0x005695e0` | `CHudWidgetArray_SetFlag700` (sets char at this+700) |
| vt[8] | `0x005a0c40` | (un-named) |
| vt[9] | `0x00569640` | (un-named) |
| vt[10] | `0x00569610` | (un-named) |
| vt[11] | `0x00595d30` | (un-named) |

## CHudWidgetArray_Tick @ 0x0058ca30

```c
void CHudWidgetArray_Tick(this, param_2) {
  // Snapshot frame state
  uVar5 = FUN_0057ca60(this, param_2);

  // If frame-state changed, update widget-array's cached state
  if (uVar5 != this+0x18 || uVar4 != this+0x1c)
    FUN_0057cdb0(this, lo, hi);

  // Race-mode active check
  bVar2 = FUN_00626dd0(this + 0x30);
  if (bVar2 && DAT_00925e90 != 4 && DAT_00925e90 != 5
            && DAT_0091cf28 == 0 && DAT_009885c8 == 0) {
    if (FE_IsGameStateRendering()) {
      // Fire event 0x014035fb (HUD render-ready)
      this_event = BumpFastmemArenaCursor(0xc);
      FUN_00621e80(this_event, 0x014035fb);
    }
  }

  // === Visibility flip (HUD on/off based on game-master flag) ===
  CHudWidgetArray_FlipVisibilityOnGameMasterChange(this);  // 0x005696c0

  // === THE WIDGET WALKER (inline) ===
  for each slot in [0x2dc, 0x2e0, 0x2e8, 0x2ec, 0x2f0, 0x310, 0x314,
                    0x318, 0x31c, 0x328, 0x32c]:
      widget = *(int**)(this + offset);
      if (widget != NULL) {
          // Mode-filter check: (widget[8] & widget[6]) != 0 OR (widget[9] & widget[7]) != 0
          // These are the active-state bitmasks for the current game mode
          if ((widget[8] & widget[6]) != 0 || (widget[9] & widget[7]) != 0)
              (**(code **)(*widget + 4))();  // call vt[1] = Update
      }

  // Mission-active overlay
  if (*(char*)(DAT_0091cb20 + 0x1f) != 0)
      *(char*)(DAT_0091cb20 + 0x2a) = 1;

  // Input + frame-end
  ProcessFEngHudActionInput(this, param_1);
}
```

## Widget storage offsets within CHudWidgetArray

The widgets are stored at FIXED OFFSETS on the array object — not a contiguous loop:

| Offset | Likely widget (TBD by cross-ref with master init) |
|---|---|
| `+0x2dc` | (slot 0) |
| `+0x2e0` | (slot 1) |
| `+0x2e8` | (slot 2) |
| `+0x2ec` | (slot 3) |
| `+0x2f0` | (slot 4) |
| `+0x310` | (slot 5) |
| `+0x314` | (slot 6 — NO mode-filter check, always called) |
| `+0x318` | (slot 7) |
| `+0x31c` | (slot 8) |
| `+0x328` | (slot 9) |
| `+0x32c` | (slot 10) |

11 slots total. Note that `+0x314` is the only one WITHOUT a mode-filter — it's called unconditionally. Likely a global "always-on" widget like fade-screen overlay.

Master init at `CHudWidgetArray_Ctor @ 0x5a6600` populates these slots in race-mode-gated order (wave-9 mapping). Need to cross-reference master-init's state→slot writes against this Tick's slot→Update reads to get a definitive widget-slot map.

## Widget mode-filter object layout

Each widget has at vt+0x18..+0x24 (slots [6]..[9]):
- `widget[6]` = "primary mode mask A"
- `widget[7]` = "primary mode mask B"
- `widget[8]` = "current game mode mask A"
- `widget[9]` = "current game mode mask B"

A widget is ticked iff EITHER mask intersects (`A&A` OR `B&B` is nonzero).

## Why this matters

Wave-9 left this open: "the per-frame walker that calls slot[1] on each widget is still unmapped." Wave-13 closes it. Modders can now:

1. **Hook the walker** at `CHudWidgetArray_Tick @ 0x58ca30` to intercept ALL HUD updates at once.
2. **Force-tick a widget** by clearing its mode-filter masks (set widget[6..9] = -1) — that widget always updates regardless of game mode.
3. **Skip a widget** by zeroing its mode-filter masks — the walker calls won't fire for it.
4. **Add a custom widget** by setting one of the `+0x2dc..+0x32c` slots to a custom widget object with vt[1]=your-Update.

## Event hash discovered

`0x014035fb` — broadcast by Tick when HUD render is gated active. Plays "HUD ready / new race frame begin" semantic. Likely audio cue or HUD-anim trigger.

## Renames applied this session

- `0x0058ca30` → `CHudWidgetArray_Tick` (was FUN, now created + named + plated)
- `0x005696c0` → `CHudWidgetArray_FlipVisibilityOnGameMasterChange` (was FUN)
- `0x005a6e00` → `DestructCHudWidgetArray` (vt[0])
- `0x005a0c10` → `CHudWidgetArray_DestroyMaybe` (vt[2])
- `0x00569570` → `CHudWidgetArray_SetActive` (vt[4])
- `0x00569680` → `CHudWidgetArray_CheckGameState` (vt[5])
- `0x005695e0` → `CHudWidgetArray_SetFlag700` (vt[7])
- + 4 more vt slots (vt[3], vt[6], vt[8..11]) created as `CHudWidgetArray_vtN` (functions registered for future rename)

## Outstanding

- vt[3], vt[6], vt[8..11] still need semantic naming
- Master-init slot map: cross-reference `CHudWidgetArray_Ctor @ 0x5a6600` writes to `+0x2dc..+0x32c` with this walker's reads to get a definitive widget-name → slot-offset table
- Event hash `0x014035fb` — find the registered listeners
