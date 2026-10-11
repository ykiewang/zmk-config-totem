# Implementation Plan: Totem KeyBeacon Support

**Branch**: `001-keybeacon-support` | **Date**: 2026-10-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-keybeacon-support/spec.md`

## Summary

Enable zmk-keybeacon on the Totem split keyboard so the central (left) half reports its active layer name, layer index, and modifier state over its host BLE connection, consumable by a macOS companion app or BLE probe. The integration is deliberately minimal: declare the `zmk-keybeacon` module in `config/west.yml` (adding the `ykiewang` remote + project, tracked at `main` per explicit user request) and enable `CONFIG_ZMK_KEYBEACON=y` in the central half's conf (`config/boards/shields/totem/totem_left.conf`). The module auto-registers its CMake/Kconfig via `zephyr/module.yml`, and an internal cmake guard (`CONFIG_ZMK_KEYBEACON AND CONFIG_ZMK_BLE AND CONFIG_ZMK_SPLIT_ROLE_CENTRAL`) compiles the feature out of the peripheral (right) and settings_reset targets automatically. No module source edits, no shield CMakeLists/Kconfig edits, and no keymap changes are required (Totem's layers already carry labels).

## Technical Context

**Language/Version**: ZMK firmware configuration — Kconfig fragments (`.conf`), West manifest (YAML); no application source language. Built on ZMK + Zephyr RTOS.

**Primary Dependencies**:
- `zmk` (remote `zmkfirmware`, revision `main`, `import: app/west.yml`) — already present.
- `zmk-keybeacon` (remote `ykiewang`, revision `main`) — **to be added**. Zephyr module exposing `CONFIG_ZMK_KEYBEACON`; auto-registered through `zephyr/module.yml`.

**Storage**: N/A (firmware; no persistent app data introduced by this feature).

**Testing**: Existing GitHub Actions workflow `zmkfirmware/zmk/.github/workflows/build-user-config.yml@main` (runs `west update` + builds all `build.yaml` targets). Local `west build` as an alternative. Functional verification via a BLE probe (`bleak`) or the `BleWidget` macOS app.

**Target Platform**: SEEED XIAO BLE (`board: xiao_ble//zmk`, nRF52840), ZMK split keyboard, host-facing BLE (`CONFIG_ZMK_BLE=y` provided automatically by the BLE board).

**Project Type**: ZMK user-config repository (firmware config), not a conventional app/library. Standard structure already in place under `config/`.

**Performance Goals**: Layer/modifier change reflected on the host within ~1 s; redundant notifications suppressed when the snapshot is unchanged (idle keyboard produces no update stream).

**Constraints**:
- KeyBeacon active on the central (left) target only; peripheral (right) and settings_reset must compile out silently and keep building.
- No edits to module source, nor to shield `CMakeLists.txt` / `Kconfig*`.
- At most two configuration files changed (`config/west.yml`, `config/boards/shields/totem/totem_left.conf`).
- Existing ZMK dependency and all three build targets remain intact.

**Scale/Scope**: One keyboard, two halves + a settings_reset target, four keymap layers (BASE, NAVI, SYM, ADJ).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The project constitution (`.specify/memory/constitution.md`) is an unpopulated template with no ratified principles, so there are no explicit gates to enforce. Applying general good-practice principles that the (empty) constitution would reasonably imply:

| Principle (implied) | Status | Notes |
|---------------------|--------|-------|
| Minimal footprint / simplicity | PASS | Two-file change; one west entry + one Kconfig symbol, exactly as the upstream guide intends. |
| Reproducibility | DEVIATION (justified) | Tracking the module at `main` instead of a pinned tag reduces build reproducibility. Explicitly requested by the user; recorded in spec FR-002 and Complexity Tracking below. |
| No invasive changes to upstream/vendored code | PASS | Module source untouched; integration is manifest + conf only. |
| Preserve existing behavior | PASS | Existing ZMK dependency, build targets, and CI flow unchanged. |

**Gate result**: PASS (one justified deviation, tracked). No blocking violations. Re-evaluated after Phase 1 — still PASS.

## Project Structure

### Documentation (this feature)

```text
specs/001-keybeacon-support/
├── plan.md              # This file (/speckit-plan command output)
├── spec.md              # Feature specification (/speckit-specify)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   ├── build-artifacts.md
│   └── keybeacon-report.md
├── checklists/
│   └── requirements.md  # Spec quality checklist (/speckit-specify)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created here)
```

### Source Code (repository root)

This is a ZMK user-config repository, not a src/tests application. The relevant existing layout and the files this feature touches:

```text
config/
├── west.yml                              # CHANGE: add ykiewang remote + zmk-keybeacon project (revision: main)
├── totem.conf                            # unchanged (applies to all totem targets)
├── totem.keymap                          # unchanged (layers already labeled BASE/NAVI/SYM/ADJ)
└── boards/
    └── shields/
        └── totem/
            ├── Kconfig.defconfig         # unchanged (left = CONFIG_ZMK_SPLIT_ROLE_CENTRAL=y)
            ├── Kconfig.shield            # unchanged
            ├── totem_left.conf           # CHANGE: add CONFIG_ZMK_KEYBEACON=y (central-only)
            ├── totem_right.conf          # unchanged (peripheral)
            ├── totem.dtsi / *.overlay    # unchanged
            └── totem.zmk.yml             # unchanged

.github/workflows/build.yml               # unchanged (build-user-config.yml runs west update)
build.yaml                                # unchanged (left / right / settings_reset targets)
```

**Structure Decision**: Keep the standard zmk-config structure untouched. Apply exactly two edits — the West manifest (`config/west.yml`) and the central half's shield conf (`config/boards/shields/totem/totem_left.conf`). `totem_left.conf` is chosen over `config/totem.conf` because the upstream guide specifies the central half's conf only; it is currently empty and exists specifically to hold left-half config. The cmake guard means the symbol would be harmless in the shared conf too, but the central-only placement is the precise, guide-recommended spot.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Module revision pinned to `main` instead of a released tag (`v1.0.0`) | User explicitly requested pulling the latest from `main` (spec FR-002). | Pinning a tag (the upstream-recommended, more reproducible option) was rejected only because it contradicts the explicit user instruction. Mitigation: `west.yml` keeps a single-line revision that can later be changed to a tag with no other edits (FR-011). |
