# Quickstart Validation: BLE Keyboard Status Widget

Runnable scenarios that prove the feature works end to end. Contract details live
in `contracts/status-snapshot.md`; entity shapes in `data-model.md`.

## Prerequisites

- TOTEM keyboard with a SEEED XIAO BLE central (left) half, flashed with firmware
  built from this branch.
- macOS host with Bluetooth enabled and the widget app built.
- The reworked probe script (`tools/probe.py`) for firmware-side checks.

## Build & flash (firmware)

1. Ensure `config/totem.conf` enables the feature symbol and the shield
   `Kconfig` gates it on `ZMK_BLE` + central role.
2. Push the branch; let GitHub Actions build. Confirm all `build.yaml` targets
   compile — `totem_left`, `totem_right`, `settings_reset`.
3. Download the artifact; flash `totem_left`. Flash `totem_right` and confirm it
   still works (feature must be absent there).

**Expected**: all three targets build; the peripheral half behaves exactly as
before.

## Verify firmware on device

Run the reworked probe (`tools/probe.py`), which subscribes to the custom
characteristic and prints `[idx][mods][name]`.

| Step | Action | Expected |
|------|--------|----------|
| 1 | Connect probe to the keyboard | Initial READ snapshot printed |
| 2 | Toggle each layer | `layer_index` and `layer_name` match the physical layer |
| 3 | Hold then release each of the 8 modifier keys | `mods` bitmask sets and clears the matching bit |
| 4 | Do nothing for 1 minute | No further notifications printed |

## Build & run (host)

1. Build the app; launch it.
2. Confirm no Dock icon appears and a menu-bar item is present
   (`LSUIElement`).

## End-to-end scenarios

| # | Scenario | Expected |
|---|----------|----------|
| 1 | Keyboard on base layer | Panel shows `BASE` |
| 2 | Activate NAVI / SYM / ADJ | Panel name updates within ~1s |
| 3 | Hold either Shift | Single Shift indicator highlights; release clears it |
| 4 | Hold left Shift and right Shift | Same single indicator highlights (merged) |
| 5 | Drag the panel (unlocked) to a new spot, restart app | Position restored |
| 6 | Toggle menu-bar lock on | Clicks pass through to the window beneath |
| 7 | Restart app while locked | Lock state restored |
| 8 | Switch spaces / enter full-screen | Panel stays visible, does not take focus |
| 9 | Power off the keyboard | Panel shows not-connected; menu bar reflects it |
| 10 | Power keyboard back on | Panel reconnects and resumes live updates with no user action |
| 11 | Turn Bluetooth off, then on | Menu bar indicates the problem; app does not crash; recovers |
| 12 | Feed a 1-byte payload (test harness) | Packet discarded, no bad data shown |
| 13 | Trigger an unnamed/undecodable layer name | Panel shows `L{index}` fallback |

## Automated tests (host)

- Run the XCTest suite for `KeyboardStatus.parse` covering: normal packet, empty
  layer name, undersized packet, invalid UTF-8, each modifier bit, and merged
  halves.

## Success checks

- SC-001: measure lag between physical change and panel update across a session.
- SC-002: 1-hour idle → zero notifications (probe log).
- SC-004: disconnect/reconnect → live state within 10s, no manual action.
- SC-005: 20 Bluetooth toggle + reconnect cycles → no crashes.
- SC-006: repeated restarts preserve position/lock; position always on-screen.
