# Quickstart: Totem KeyBeacon Support

**Feature**: 001-keybeacon-support | **Date**: 2026-10-11

This guide validates the feature end-to-end. It references [data-model.md](./data-model.md) and the contracts in [contracts/](./contracts/) rather than duplicating them.

## Prerequisites

- This repo (fork) with write access to push and trigger GitHub Actions, OR a local ZMK/West build environment (`west`, Zephyr SDK).
- A Totem split keyboard with SEEED XIAO BLE controllers (left = central, right = peripheral).
- A Mac for verification, with either:
  - the `BleWidget.dmg` app from the zmk-keybeacon Releases page, or
  - Python 3 + a virtualenv for a `bleak`-based probe (the module repo does **not** ship `tools/probe.py`; write one locally from `GETTING-STARTED.md`).

## The two changes under test

1. `config/west.yml` — add `ykiewang` remote + `zmk-keybeacon` project (`revision: v1.1.3`). See data-model "Module Dependency Entry".
2. `config/boards/shields/totem/totem_left.conf` — add `CONFIG_ZMK_KEYBEACON=y`. See data-model "Central Target Configuration".

## Step 1 — Build (satisfies contracts/build-artifacts.md)

**Via CI (recommended):**
1. Commit and push the two changes.
2. Open the repo's **Actions** tab; wait for the build workflow to finish.
3. Download the `firmware` artifact archive.

**Expected**: workflow succeeds (B1) and the archive contains `totem_left`, `totem_right`, and `settings_reset` UF2 files (B2–B4).

**Via local build (alternative):**
```
west update        # fetches zmk AND the newly declared zmk-keybeacon
west build -d build/left  -b xiao_ble//zmk -- -DSHIELD=totem_left
west build -d build/right -b xiao_ble//zmk -- -DSHIELD=totem_right
```
**Expected**: both builds succeed; `keybeacon.c` compiles in the left build (B5) but not the right (B6).

### Build acceptance checks
- [ ] Workflow/local build succeeds (B1)
- [ ] Left, right, settings_reset artifacts present (B2–B4)
- [ ] `keybeacon.c` compiled for left only (B5–B6)
- [ ] `git diff` touches only the two config files (B7 / SC-004)

## Step 2 — Flash

1. Connect the left half, double-press reset to enter the bootloader (mass-storage volume appears).
2. Drag the `totem_left …-zmk.uf2` onto the volume.
3. Repeat with the right half and the `totem_right …-zmk.uf2`.

## Step 3 — Verify runtime behavior (satisfies contracts/keybeacon-report.md)

1. Connect the keyboard to the Mac over BLE.
2. Start the consumer:
   - **App**: launch BleWidget; the floating panel should show the active layer + modifier indicators, OR
   - **Probe**: in a venv, `pip install bleak`, run your local probe script; it prints the keyboard name, layer index/name, and modifier state per change.
3. Operate the keyboard and observe.

### Runtime acceptance checks
- [ ] On BASE layer, consumer shows `BASE` (not `L0`) (K1 / SC-005)
- [ ] BASE → NAVI reflected within ~1 s (K2 / SC-001)
- [ ] Holding/releasing a modifier updates state (K3)
- [ ] Idle keyboard produces no continuous update stream (K4 / FR-007)
- [ ] Device discovered among connected peripherals, not by scanning (K5)
- [ ] No KeyBeacon output from right/settings_reset (K6 / SC-003)

## Step 4 — (Optional) Change the pinned module version (FR-011)

- The module is pinned at `revision: v1.1.3`, so `west update` fetches identical code every time (reproducible). To move to a newer release, change the single `revision:` line in `config/west.yml` to the new tag and re-run `west update && west build` — no other edits.

## Success = all acceptance checks above pass

Maps to Success Criteria SC-001..SC-005 in [spec.md](./spec.md).
