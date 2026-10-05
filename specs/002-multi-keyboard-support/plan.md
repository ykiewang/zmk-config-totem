# Implementation Plan: Multi-Keyboard Support (Decouple App & Firmware from Totem)

**Branch**: `002-multi-keyboard-support` | **Date**: 2026-10-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-multi-keyboard-support/spec.md`

## Summary

Remove the Totem-specific coupling from both halves so **KeyBeacon** works with any
ZMK keyboard that implements the interface contract. On the **host**, drop the hardcoded
`"TOTEM"` name match and identify a keyboard purely by the custom status service UUID;
show the keyboard's **own name** (its BLE GAP device name — no new characteristic, no host
registry); when several compatible keyboards are connected, let the user pick one from the
menu bar and remember that choice across launches; de-brand persisted settings with a
one-time migration. On the **firmware**, repackage the already-generic shared logic
(`gatt_status.c` → `keybeacon.c`) as a
self-contained, shield-scoped **KeyBeacon kit** behind a generic Kconfig symbol, with the Totem
shield as the reference consumer and a porting guide so another keyboard is enabled by
copying the kit + wiring two lines + enabling one symbol — without editing the shared logic.
The on-device probe is genericized the same way (service-UUID discovery, not name).

The feature, its protocol, and the macOS app are named **KeyBeacon** (Kconfig symbol
`CONFIG_ZMK_KEYBEACON`; the GATT service is the KeyBeacon service).

Payload layout is unchanged; the only contract movement is a **clarification** (identity =
service UUID, display name = GAP name), folded into the status-snapshot contract.

## Technical Context

**Language/Version**: Firmware: C (ZMK on Zephyr RTOS). Host: Swift 5.9+ (macOS). Tooling:
Python 3.13 (on-device probe).

**Primary Dependencies**: Firmware: ZMK `app` APIs (`zmk/keymap.h`, `zmk/hid.h`,
`zmk/events/*`), Zephyr Bluetooth GATT. Host: CoreBluetooth, AppKit, Foundation. Probe:
PyObjC CoreBluetooth.

**Storage**: Host: `UserDefaults` — existing panel position (per-screen) and lock state
(de-branded keys + migration), plus a NEW persisted *selected keyboard identifier*. Firmware:
in-RAM snapshot cache only.

**Testing**: Host: XCTest over `BleWidgetCore` (snapshot parsing, name fallback,
compatible-keyboard selection, settings migration — all pure logic, no AppKit). Firmware: no
in-tree unit harness — GitHub Actions build of all `build.yaml` targets + on-device probe.

**Target Platform**: Firmware: SEEED XIAO BLE (nRF52840), central (left) half; portable to
other ZMK central-role keyboards via the kit. Host: macOS.

**Project Type**: Hybrid — embedded firmware (shield-scoped kit) + native desktop app + CLI
probe.

**Performance Goals**: Preserve feature 001: layer/modifier change reflected ≤ 1 s for ≥ 95%
of changes; zero redundant notifications when idle. Multi-keyboard: auto-connect to the sole
or remembered keyboard, and reconnect after restart, within a few seconds.

**Constraints**: Firmware feature compiles only on the central role and only when the generic
symbol is enabled (peripheral / `settings_reset` excluded). No added on-air traffic: the name
is the GAP name (free at discovery), so there is no per-change name traffic and no new
characteristic. No host-side registry/whitelist. Existing users' saved panel settings must
survive de-branding.

**Scale/Scope**: A handful of keyboards per user; one status panel at a time; 4 logical
modifiers; small codebase. Shared firmware logic is a single ~100-line C file.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|-----------|------|--------|
| I. Interface Contract First | Identity/discovery and the keyboard-name source are specified as a contract clarification (service UUID identifies; GAP name = display name) before code; payload layout unchanged; change folded into the versioned status-snapshot contract. | PASS |
| II. Keyboard as Source of Truth | Display name comes from the keyboard's own GAP name; layer/mods still from authoritative ZMK APIs; the host adds no inference and keeps no model list. | PASS |
| III. Shield-Scoped, Minimal Footprint | Status kit stays shield-scoped (R1: `app`-private headers reachable only from shield scope), gated by a generic Kconfig symbol + `ZMK_BLE` + central role; `default n`; no new on-air traffic. | PASS |
| IV. MVP Discipline (YAGNI) | Bounded scope with explicit non-goals; the dedicated-name-characteristic and multi-panel ideas are reserved, not built; name reuses existing GAP name (zero porting burden). | PASS |
| V. Hardware-Verified by CI | Kit refactor must still build all `build.yaml` targets with Totem behavior unchanged (no regression); probe genericized for on-device check; new host logic covered by XCTest. | PASS |

**Platform/workflow constraints**: host + probe depend only on the contract (not firmware
internals); contract/spec remain under version control; design precedes implementation.

No violations. **Complexity Tracking not required.**

**Post-Phase-1 re-check**: Re-evaluated after `research.md`, `data-model.md`,
`contracts/discovery-and-identity.md`, and `quickstart.md`. No new violations — the design adds
no new on-air traffic (name = GAP name, no characteristic), keeps the kit shield-scoped and
central-gated, introduces no host registry, and folds the identity/name rules into the versioned
contract as a backward-compatible clarification. Gate remains **PASS**.

## Project Structure

### Documentation (this feature)

```text
specs/002-multi-keyboard-support/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── discovery-and-identity.md   # Phase 1 output (amends status-snapshot contract)
├── checklists/
│   └── requirements.md  # (from /speckit-specify)
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
config/
├── keybeacon_kit/                     # NEW: self-contained, keyboard-independent firmware kit
│   ├── keybeacon.c                 # shared logic (renamed from gatt_status.c); never edited to port
│   ├── keybeacon.cmake            # NEW: guarded zephyr_library snippet (symbol + BLE + central)
│   ├── Kconfig.keybeacon          # NEW: generic symbol CONFIG_ZMK_KEYBEACON
│   └── README.md                   # NEW: the porting guide (copy + wire 2 lines + enable 1 symbol)
├── boards/shields/totem/
│   ├── CMakeLists.txt              # EDITED: include ../../keybeacon_kit/keybeacon.cmake (reference consumer)
│   ├── Kconfig.defconfig           # EDITED: source Kconfig.keybeacon; drop Totem-named symbol
│   └── (gatt_status.c removed — its logic now lives in the kit as keybeacon.c)
└── totem.conf                      # EDITED: CONFIG_ZMK_KEYBEACON=y (was ZMK_TOTEM_GATT_STATUS)

host/macos/
├── Sources/
│   ├── BleWidgetCore/              # pure logic (unit-testable)
│   │   ├── BLEClient.swift         # EDITED: identify by service UUID; remove "TOTEM" match
│   │   ├── KeyboardStatus.swift    # unchanged payload parse
│   │   ├── CompatibleKeyboard.swift# NEW: {identifier, name, state}; candidate discovery/verify
│   │   └── AppSettings.swift       # NEW: de-branded keys + selected-keyboard id + migration
│   └── BleWidget/                  # AppKit executable
│       ├── AppDelegate.swift       # EDITED: menu-bar "Keyboard ▸" chooser; selection wiring
│       └── FloatingPanel.swift     # EDITED: de-branded UserDefaults keys (migrated)
└── Tests/BleWidgetTests/
    ├── KeyboardStatusTests.swift   # existing
    ├── KeyboardIdentityTests.swift # NEW: name fallback, service-UUID identity, selection
    └── MigrationTests.swift        # NEW: totem* → generic keys migration

tools/
└── probe.py                        # EDITED: discover by custom service UUID, not "TOTEM" name

specs/001-ble-status-widget/contracts/
└── status-snapshot.md              # EDITED (impl phase): fold in identity/name clarification
```

**Structure Decision**: Keep the firmware feature **shield-scoped** (Principle III / research
R1 — ZMK `app`-private headers are only reachable from shield build scope), but factor the
shared pieces into a repo-level `config/keybeacon_kit/` directory that the Totem shield consumes
as the reference. Porting to another keyboard copies that directory into (or references it
from) the target shield and adds two wire-up lines plus one `=y`, never touching
`keybeacon.c`. The host keeps the existing `BleWidgetCore` (pure logic) / `BleWidget`
(AppKit) split so the new identity, selection, and migration logic is unit-testable without
AppKit. The probe mirrors the host's service-UUID discovery so both consumers follow the same
contract.
