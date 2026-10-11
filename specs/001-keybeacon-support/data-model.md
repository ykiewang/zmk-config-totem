# Phase 1 Data Model: Totem KeyBeacon Support

**Feature**: 001-keybeacon-support | **Date**: 2026-10-11

This feature is a firmware configuration change, not a data-centric application. The "entities" below are configuration constructs and the runtime report payload, described at the conceptual level (no database, no app schema).

## Entity: Module Dependency Entry

Represents the declaration in `config/west.yml` that tells West where to fetch zmk-keybeacon.

| Field | Value / Rule | Notes |
|-------|--------------|-------|
| remote name | `ykiewang` | New remote; `url-base: https://github.com/ykiewang` |
| project name | `zmk-keybeacon` | Must match the module repo name |
| revision | `main` | Per FR-002; may later be a tag (FR-011) without other edits |
| path/import | none | No `import:`; module self-registers via `zephyr/module.yml` |

**Validation rules**:
- The existing `zmk` project (remote `zmkfirmware`, `revision: main`, `import: app/west.yml`) and `self: { path: config }` MUST remain unchanged (FR-003).
- Exactly one new remote and one new project are added.
- YAML MUST remain valid so `west update` can parse it (SC-002).

**Relationships**: Consumed by West during `west update`; enables the Central Target Configuration to find `CONFIG_ZMK_KEYBEACON`.

## Entity: Central Target Configuration

Represents the Kconfig state governing the central (left) build target.

| Field | Value / Rule | Notes |
|-------|--------------|-------|
| config file | `config/boards/shields/totem/totem_left.conf` | Central half's conf (FR-004) |
| symbol | `CONFIG_ZMK_KEYBEACON=y` | Enables the feature |
| preconditions | `CONFIG_ZMK_BLE=y` (auto via board) + `CONFIG_ZMK_SPLIT_ROLE_CENTRAL=y` (left via `Kconfig.defconfig`) | Both already true |

**Validation rules**:
- Symbol is present only in the central conf; right (peripheral) and settings_reset targets MUST NOT have the feature active (FR-005).
- No edits to `Kconfig.defconfig`, `Kconfig.shield`, or any shield `CMakeLists.txt` (FR-008).

**State transitions**: `disabled` (symbol absent) → `enabled` (symbol = y). Reversible by removing the line.

## Entity: Layer/Modifier Snapshot (runtime report payload)

Represents the state the central half broadcasts to the connected host.

| Field | Meaning | Source |
|-------|---------|--------|
| active layer name | Human-readable label of the highest active layer | Keymap `label` (BASE/NAVI/SYM/ADJ) |
| active layer index | Numeric index of the active layer | ZMK layer state |
| modifier state | Which modifiers are currently held | ZMK HID modifier state |

**Validation rules**:
- Changes to any field produce an updated report (FR-006).
- Unchanged snapshots MUST be suppressed (no redundant notifications while idle) (FR-007).
- Layer name MUST be the keymap label, not a generic `L0/L1` fallback (FR-010, SC-005).

**State transitions**: On each ZMK layer/modifier change → compute snapshot → if different from last sent, notify host; else suppress.

**Relationships**: Produced by the central target only; consumed by the macOS companion/probe over the host BLE link.

## Non-entities (explicitly out of model)

- No persistent storage, settings, or files are added to the keyboard.
- No changes to keymap, DTSI/overlays, or board definitions.
- The macOS companion app internals are out of scope (verification tool only).
