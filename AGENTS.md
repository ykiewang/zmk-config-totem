# AGENTS.md

This file provides guidance to codeflicker when working with code in this repository.

## WHY: Purpose and Goals

A ZMK firmware configuration for the **TOTEM**, a 38-key column-staggered split
keyboard (SEEED XIAO BLE / RP2040). It defines the shield hardware description
(matrix transform, GPIO wiring) and the user's keymap/layers. Firmware is built
in CI and flashed as `.uf2` files.

## WHAT: Technical Stack

- **Firmware**: ZMK (Zephyr RTOS based), devicetree (`.dtsi`/`.overlay`) + Kconfig
- **Config files**: `.keymap` (layers/behaviors), `.conf` (Kconfig overrides), `build.yaml` (CI matrix)
- **Shield**: `config/boards/shields/totem/` — definitions shared by both halves
- **Targets**: `xiao_ble//zmk` board, shields `totem_left` / `totem_right` / `settings_reset`
- **Build**: GitHub Actions → `zmkfirmware/zmk/.github/workflows/build-user-config.yml@main`
- **Upstream**: [GEIGEIGEIST/totem](https://github.com/GEIGEIGEIST/totem) (hardware), `zmkfirmware/zmk` (`main`)

## HOW: Core Development Workflow

```bash
# Edit the keymap (the main thing you'll change)
$EDITOR config/totem.keymap

# Build firmware: push and download the Artifacts from GitHub Actions,
# or build locally with west (see docs/agent/development_commands.md)

# Flash: double-reset each half, drag the matching .uf2 onto the USB drive
```

## Progressive Disclosure

For detailed information, consult these documents as needed:

- `docs/agent/development_commands.md` - CI and local build/flash commands
- `docs/agent/architecture.md` - Shield structure, matrix transform, layers, split roles

**When working on a task, first determine which documentation is relevant, then read only those files.**
