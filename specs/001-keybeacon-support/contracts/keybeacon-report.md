# Contract: KeyBeacon Report (runtime)

**Feature**: 001-keybeacon-support | **Type**: Runtime behavior contract (host-facing)

This defines the observable behavior the central half must exhibit to a connected host (macOS app or BLE probe). It is the "interface" between the firmware and the consumer.

## Preconditions

- A Totem flashed with firmware built from this repo (left = central, right = peripheral).
- The keyboard is connected to a Mac over BLE.
- A consumer (BleWidget app or a `bleak`-based probe) is running on the Mac.

## Behavior (all MUST hold)

| # | Given | When | Then | Maps to |
|---|-------|------|------|---------|
| K1 | Keyboard connected | On the BASE layer | Consumer reports active layer name `BASE` (not `L0`) | FR-006, FR-010, SC-005 |
| K2 | Keyboard connected | User switches BASE → NAVI | Consumer reports `NAVI` within ~1 s | FR-006, SC-001 |
| K3 | Keyboard connected | User holds a modifier (e.g., Shift) | Consumer reports that modifier active; inactive on release | FR-006, SC-001 |
| K4 | Keyboard connected, idle | No keys pressed, snapshot unchanged | Consumer receives no continuous stream of updates | FR-007 |
| K5 | Keyboard connected | Consumer looks for the device | Device is found among already-connected peripherals (it is not advertising while connected) | Edge case |
| K6 | Firmware for right/settings_reset | Inspected at runtime | No KeyBeacon reporting originates from these targets | FR-005, SC-003 |

## Report payload (conceptual)

A snapshot carrying: active layer name (string label), active layer index (integer), modifier state (set of held modifiers). Delivered via BLE notification on the host connection only when the snapshot changes.

## Verification

- K1–K4: watch consumer output while operating the keyboard; a `bleak` probe prints name + layer index/name + modifier state per change (note: the module repo ships no `tools/probe.py`, so the probe is written locally from the guide), or use the BleWidget floating panel.
- K5: confirm discovery works via connected-peripheral enumeration, not scanning.
- K6: only the left half holds the central role; right/reset carry no host link and emit nothing.
