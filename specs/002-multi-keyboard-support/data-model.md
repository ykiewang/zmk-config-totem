# Phase 1 Data Model: Multi-Keyboard Support

Entities are host-side (the firmware remains the feature-001 producer; its only change is
packaging, not data). Payload entities are unchanged from feature 001 — see
`specs/001-ble-status-widget/data-model.md` and `contracts/status-snapshot.md`.

## Entity: Compatible Keyboard

A BLE device recognized as a KeyBeacon keyboard **by the custom service contract alone**
(research MR2).

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `identifier` | UUID (string) | `CBPeripheral.identifier` | Stable per Mac+device; the disambiguator and reconnect key (MR4) |
| `name` | string \| absent | `CBPeripheral.name` (GAP / `CONFIG_ZMK_KEYBOARD_NAME`) | Self-reported display name (MR1); may be nil/empty |
| `displayName` | string | derived | `name` if non-empty, else generic fallback (e.g. `Keyboard <short-id>`) |
| `state` | enum | runtime | `connecting` / `connected` / `notConnected` / `unavailable` (feature 001) |
| `isCompatible` | bool | derived on connect | true once the custom service is confirmed via GATT discovery |

**Validation rules**:
- A device is listed as a Compatible Keyboard only after the custom service is confirmed, or
  provisionally while verifying; a device lacking the custom service MUST be dropped (FR-003).
- `displayName` MUST never be blank: empty/undecodable `name` → generic fallback (FR-006).
- `name` is read at most once per connection (it is the GAP name, obtained at discovery); it is
  never re-fetched on status changes (FR-007).

## Entity: Selected Keyboard (persisted)

The single keyboard the user has chosen to display.

| Field | Type | Storage | Rules |
|-------|------|---------|-------|
| `selectedKeyboardIdentifier` | UUID (string) \| absent | `UserDefaults` | Remembered across launches (FR-015); set on explicit selection or on sole-candidate auto-connect |

**Selection rules**:
- Exactly one compatible keyboard present → auto-select & connect (FR-013).
- Remembered identifier present among candidates → auto-select & connect it (FR-015).
- ≥ 2 candidates and none remembered → no auto-connect; await explicit choice (FR-014).
- At most one Selected Keyboard at a time; one panel tracks it (FR-016).

## Entity: Panel Settings (persisted, de-branded + migrated)

| Field | Type | Storage key (new) | Legacy key (migrated from) | Rules |
|-------|------|-------------------|----------------------------|-------|
| `position` | screen-frame origin | `panelFrame.<screenId>` | `totemPanelFrame.<screenId>` | Per-screen; restored on launch; clamped to visible bounds (feature 001) |
| `locked` | bool | `panelLocked` | `totemPanelLocked` | `false`=draggable/intercepting (default); `true`=click-through |
| `settingsMigratedV2` | bool | `settingsMigratedV2` | — | Guards the one-time copy-forward (MR5) |

**Migration (one-time, on launch)**: if `settingsMigratedV2` is unset, then for each new key
that is absent while its legacy `totem*` counterpart exists, copy legacy → new; finally set
`settingsMigratedV2 = true`. Never overwrite an existing new value; never reset (FR-004 + the
"existing Totem users" edge case).

## Entity: KeyBeacon Kit (Firmware; packaging, not runtime data)

The portable unit that makes firmware support reproducible (research MR3).

| Part | File | Role | Edited when porting? |
|------|------|------|----------------------|
| Shared logic | `config/keybeacon_kit/keybeacon.c` | GATT service, state read, change-detect, notify | **No** |
| Build snippet | `config/keybeacon_kit/keybeacon.cmake` | Guarded `zephyr_library` (symbol + `ZMK_BLE` + central role) | No |
| Config symbol | `config/keybeacon_kit/Kconfig.keybeacon` | `CONFIG_ZMK_KEYBEACON` (generic, `default n`) | No |
| Porting guide | `config/keybeacon_kit/README.md` | Steps, prerequisites (central BLE role), R1 note | No |

**Per-keyboard enablement (the only changes to port)**:
1. Make the kit available to the target shield (copy the directory, or reference it).
2. `include(<kit>/keybeacon.cmake)` in the shield `CMakeLists.txt`.
3. `source`/`rsource` `<kit>/Kconfig.keybeacon` from the shield Kconfig.
4. `CONFIG_ZMK_KEYBEACON=y` in the keyboard `.conf`.

**Invariant**: the feature compiles only for the central role and only when the symbol is set;
peripheral and `settings_reset` builds exclude it (FR-010, Principle III).

## State flow (host, end to end)

```text
launch / Bluetooth powered on
  → enumerate connected peripherals (custom + HID service)   [MR2]
  → verify custom service on connect → build Compatible Keyboard list
  → selection:
       1 candidate        → auto-connect
       remembered present → auto-connect remembered           [MR4]
       ≥2 and none remembered → populate "Keyboard ▸", await choice
  → on connect: read snapshot + subscribe (feature 001 flow)
  → panel renders displayName + layer name + merged modifiers
  → user picks another keyboard → switch single connection, persist identifier
```

Connection-state transitions (`connecting`/`connected`/`notConnected`/`unavailable`) and the
status-render pipeline are unchanged from feature 001's data model.
