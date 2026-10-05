# Implementation Plan: BLE Keyboard Status Widget

**Branch**: `001-ble-status-widget` | **Date**: 2026-10-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-ble-status-widget/spec.md`

## Summary

Expose the split keyboard's live active layer and modifier state over a custom
GATT characteristic from the keyboard's central half, and render that state in an
always-on-top, draggable, optionally click-through desktop panel on macOS.

Two independently built halves talk through one frozen interface contract (the
status snapshot: layer index + modifier bitmask + layer name). Firmware is
shield-scoped C inside the ZMK build; the host is a Swift/AppKit menu-bar app
using CoreBluetooth. Firmware is validated by CI build plus on-device probe;
host parsing is covered by XCTest.

## Technical Context

**Language/Version**: Firmware: C (ZMK / Zephyr RTOS); Host: Swift 5.9+

**Primary Dependencies**: Firmware: ZMK `app` APIs (`zmk/keymap.h`, `zmk/hid.h`,
`zmk/events/*`), Zephyr Bluetooth GATT; Host: CoreBluetooth, AppKit, Foundation

**Storage**: Host: `UserDefaults` for panel position (keyed per screen) and
lock/click-through state. Firmware: in-RAM snapshot cache only.

**Testing**: Host: XCTest for `KeyboardStatus` payload parsing (boundaries:
empty layer name, undersized packet, bad UTF-8). Firmware: no unit framework —
GitHub Actions build (all `build.yaml` targets) + real-hardware verification via
a reworked probe script.

**Target Platform**: Firmware: SEEED XIAO BLE (nRF52840), central (left) half
only. Host: macOS.

**Project Type**: Hybrid — embedded firmware (shield-scoped) + native desktop app.

**Performance Goals**: Layer/modifier change reflected in the panel within 1s for
≥95% of changes; zero redundant notifications during idle.

**Constraints**: Firmware feature compiled only on the central role; peripheral
and `settings_reset` builds excluded via Kconfig `depends on ZMK_BLE` + role
guard. No on-air traffic when state is unchanged.

**Scale/Scope**: Single keyboard, 4 layers, 8 physical modifier keys merged to 4
indicators. One host app, one panel window, one menu-bar item. Explicit non-goals:
battery, WPM, BLE profile, HID lock indicators, animation, autostart, settings UI.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|-----------|------|--------|
| I. Interface Contract First | Status snapshot (UUIDs + byte layout) frozen in design doc before implementation; both sides built against it | PASS |
| II. Keyboard as Source of Truth | All reported state from authoritative ZMK APIs; host adds no inference; only PC-unreachable state is sent | PASS |
| III. Shield-Scoped, Minimal Footprint | Feature in shield scope, gated by Kconfig symbol with `depends on ZMK_BLE` + central role guard; notify only on change | PASS |
| IV. MVP Discipline (YAGNI) | Explicit non-goals; extensibility via reserved payload bytes, not prebuilt features | PASS |
| V. Hardware-Verified by CI | CI builds all targets in `build.yaml`; firmware validated on device via probe | PASS |

No violations. Complexity Tracking not required.

## Project Structure

### Documentation (this feature)

```text
specs/001-ble-status-widget/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── status-snapshot.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
config/boards/shields/totem/
├── gatt_status.c        # NEW: GATT service, state read, change-detect, notify
├── CMakeLists.txt       # NEW: shield-scoped build guarded by symbol + central role
├── Kconfig              # NEW/adjusted: CONFIG_ZMK_TOTEM_GATT_STATUS (depends on ZMK_BLE)
├── totem.conf           # EDITED: enable CONFIG_ZMK_TOTEM_GATT_STATUS=y
├── totem.dtsi           # existing (unchanged)
├── totem_left.overlay   # existing (unchanged)
└── totem_right.overlay  # existing (unchanged)

config/
└── totem.conf           # EDITED (keyboard-level enable)

host/macos/
├── BleWidget.xcodeproj/  (or Package.swift)
├── Sources/
│   ├── main.swift
│   ├── AppDelegate.swift         # menu-bar item + app lifecycle
│   ├── BLEClient.swift           # CoreBluetooth connect/subscribe/reconnect
│   ├── KeyboardStatus.swift      # snapshot parse → {layerName, mods, connected}
│   ├── FloatingPanel.swift       # borderless always-on-top window, drag/lock
│   └── Info.plist                # LSUIElement = true
└── Tests/
    └── KeyboardStatusTests.swift  # XCTest parse boundaries

tools/
└── probe.py             # reworked from feature/gatt-layer-probe for [idx][mods][name]
```

**Structure Decision**: Firmware changes stay inside the existing TOTEM shield
directory per Principle III — shield scope grants the needed header access
(`CMAKE_SOURCE_DIR/include`) and per-role build gating without a separate module.
The host is a new standalone app under `host/macos/`, coupled to firmware only
through the status-snapshot contract (Principle I).
