# Phase 1 Data Model: BLE Keyboard Status Widget

## Entity: Status Snapshot

The single unit of state the keyboard reports to the host; the frozen interface
contract (see `contracts/status-snapshot.md`).

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `layer_index` | uint8 | `zmk_keymap_highest_layer_active()` | Debug/fallback; host primarily shows the name |
| `mods` | uint8 | `zmk_hid_get_explicit_mods()` | Standard HID modifier bitmask |
| `layer_name` | UTF-8 string (0..N bytes) | `zmk_keymap_layer_name(id)` | No trailing NUL; length = payload length − 2 |

**Modifier bitmask layout** (canonical HID):

| Bit | Mask | Modifier |
|-----|------|----------|
| 0 | 0x01 | Left Control |
| 1 | 0x02 | Left Shift |
| 2 | 0x04 | Left Alt (Option) |
| 3 | 0x08 | Left Gui (Command) |
| 4 | 0x10 | Right Control |
| 5 | 0x20 | Right Shift |
| 6 | 0x40 | Right Alt (Option) |
| 7 | 0x80 | Right Gui (Command) |

**Validation rules**:
- Payload length MUST be ≥ 2; shorter payloads are discarded (FR-014).
- `layer_name` MAY be empty; empty or undecodable names fall back to `L{index}`.
- Reserved trailing capacity MAY be added later without changing existing byte
  positions (Principle IV).

## Entity: Layer

A named keyboard layer.

| Field | Type | Notes |
|-------|------|-------|
| `index` | int | Position returned by `highest_layer_active()` |
| `id` | int | `zmk_keymap_layer_index_to_id(index)`; equals index unless reordering is on |
| `name` | string \| absent | Devicetree-derived label; may be `NULL`/`""` |

**Known instances**: `BASE`, `NAVI`, `SYM`, `ADJ` (0–3). All named today.

## Entity: Modifier Set

Four logical modifiers, each the merged sum of its left/right physical keys.

| Logical | Merge mask (either half active ⇒ active) |
|---------|------------------------------------------|
| Shift | `MOD_LSFT | MOD_RSFT` |
| Control | `MOD_LCTL | MOD_RCTL` |
| Option | `MOD_LALT | MOD_RALT` |
| Command | `MOD_LGUI | MOD_RGUI` |

**State**: `active` (highlighted) or `inactive` (dimmed). Slots are fixed; the
layout never reflows (FR-004).

## Entity: Floating Panel

The always-on-top desktop window.

| Field | Type | Storage | Rules |
|-------|------|---------|-------|
| `position` | screen frame origin | `UserDefaults`, keyed per screen identity | Persisted; restored on launch; clamped to visible bounds |
| `locked` | bool | `UserDefaults` | `false` = draggable/intercepting (default); `true` = click-through |
| `visible` | bool | runtime | Stays visible across spaces and full-screen apps |

**State transitions (lock)**:
- `unlocked --(toggle)--> locked`: panel becomes click-through, no longer draggable.
- `locked --(toggle)--> unlocked`: panel becomes draggable, may intercept clicks.
- Both states persist across restarts.

## Entity: Connection State

| State | Trigger | Panel behavior | Menu-bar |
|-------|---------|----------------|----------|
| `connecting` | launch / retry tick | show last known or empty | in-progress |
| `connected` | characteristic subscribed | live updates | connected |
| `not_connected` | disconnect / not found | show "not connected" | disconnected, offers reconnect |
| `unavailable` | Bluetooth off / no permission | show "not connected" | indicates problem, no crash |

**Transitions**: `connected → not_connected` on disconnect; `not_connected →
connected` automatically when the keyboard reappears; `* → unavailable` when
Bluetooth powers off; `unavailable → not_connected` on retry cadence.

## State flow (end to end)

```text
physical key / layer change
  → ZMK event (layer_state_changed | keycode_state_changed)
  → firmware recomputes Status Snapshot → compare cache → notify if changed
  → host BLEClient receives → KeyboardStatus.parse → {layer_name, mods} }
  → FloatingPanel renders layer name + merged modifier highlights
```
