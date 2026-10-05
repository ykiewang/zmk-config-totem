# Quickstart & Validation: Multi-Keyboard Support

End-to-end validation that feature 002 decouples both halves from Totem. Scenarios map to the
spec's user stories and success criteria. Details live in [contracts/discovery-and-identity.md]
(./contracts/discovery-and-identity.md) and [data-model.md](./data-model.md); this file is the
run guide, not the implementation.

## Prerequisites

- macOS with Bluetooth; the app granted Bluetooth permission on first launch.
- A ZMK split keyboard flashed with the KeyBeacon kit enabled on the **central** half.
- A **second** compatible keyboard, OR the same keyboard re-flashed with a different
  `CONFIG_ZMK_KEYBOARD_NAME`, to prove non-Totem support (SC-001) and multi-keyboard selection.
- Toolchains: `swift` (host build/tests), the ZMK CI (firmware builds), and the probe venv at
  `tools/.venv`.

## A. Firmware kit builds for all targets, Totem unchanged (US3, FR-010/FR-017, SC-004)

```bash
# Build all declared targets (central=totem_left, peripheral=totem_right, settings_reset)
# via the repo's GitHub Actions workflow, or an equivalent local west build.
# Expected: three .uf2 artifacts; the status feature is linked ONLY in the central (left) build.
```

Expected outcomes:
- `totem_left` (central) includes `keybeacon.o`; `totem_right` and `settings_reset` do **not**
  (grep the build/map output for the kit object or the service UUID symbol).
- The Totem snapshot behavior is identical to feature 001 (no regression).

## B. Port the kit to another keyboard in ≤ 10 steps, no shared-logic edits (US3, SC-003)

Follow `config/keybeacon_kit/README.md` on a scratch shield:

```bash
# 1) make the kit available to the target shield (copy config/keybeacon_kit/ or reference it)
# 2) add  include(<kit>/keybeacon.cmake)   to the shield CMakeLists.txt
# 3) source/rsource <kit>/Kconfig.keybeacon from the shield Kconfig
# 4) set  CONFIG_ZMK_KEYBEACON=y          in the keyboard .conf
# 5) build the central target for that keyboard
```

Expected outcomes:
- The build links the feature for that keyboard's **central** role only.
- `git diff config/keybeacon_kit/keybeacon.c` is **empty** (shared logic never edited).
- The documented steps number ≤ 10.

## C. Host unit logic: identity, name fallback, selection, migration (US1/US2/US4, FR-003/006/015)

```bash
cd host/macos
swift test
```

Expected (new `BleWidgetCore` tests, no AppKit needed):
- Identity: a peripheral with the custom service is compatible; one without it is rejected.
- Name: non-empty GAP name is shown verbatim; empty/undecodable → generic fallback label.
- Selection: 1 candidate auto-selects; remembered identifier auto-selects; ≥ 2 & none
  remembered → no auto-select.
- Migration: with legacy `totemPanelFrame*`/`totemPanelLocked` set and new keys absent, the
  one-time migration copies values forward and sets `settingsMigratedV2`; existing new values
  are not overwritten.

## D. App connects to a non-Totem keyboard with no code changes (US1, SC-001/SC-002)

```bash
cd host/macos && swift run BleWidget   # or launch the built .app
```

Steps & expected:
1. Connect a compatible keyboard whose name is **not** "Totem" (or rename via
   `CONFIG_ZMK_KEYBOARD_NAME`).
2. The panel appears and shows live layer/modifier state — **no edits** to app code/config
   (SC-002: zero host-side configuration).
3. The menu bar shows the keyboard under its **own** name (SC-006).

## E. Choose & remember among multiple keyboards (US4, SC-005)

Steps & expected:
1. With two compatible keyboards connected, open menu bar → **Keyboard ▸**: both are listed by
   name; neither auto-connects (none remembered yet).
2. Select keyboard A → panel tracks A; a checkmark marks A.
3. Quit and relaunch → the app reconnects to **A** automatically (remembered identifier).
4. Switch to keyboard B → the single panel now tracks B; selection persists on next launch.

## F. Existing Totem user upgrade preserves settings (FR-004 edge case)

Steps & expected:
1. Starting from a profile with legacy `totemPanelFrame*`/`totemPanelLocked` set, launch the new
   build.
2. The panel reappears at the **same** position and lock state (migrated, not reset).

## G. Probe verifies any keyboard by the contract (US3, FR-012)

```bash
tools/.venv/bin/python tools/probe.py
```

Expected:
- The probe finds the keyboard by the **custom service UUID** (not the name "TOTEM"), prints the
  discovered `.name`, and streams decoded `[idx][mods][name]` snapshots.
- Pointed at a non-Totem compatible keyboard, it still works; pointed at a device without the
  custom service, it reports none found (per the §6 conformance checklist).

## Success-criteria trace

| Scenario | Covers |
|----------|--------|
| A | SC-004, FR-010, FR-017 |
| B | SC-003, FR-008, FR-009, FR-011 |
| C | FR-003, FR-006, FR-013/014/015, FR-004 (migration) |
| D | SC-001, SC-002, FR-001/002, SC-006 |
| E | SC-005, FR-014/015/016 |
| F | FR-004 + "existing Totem users" edge case |
| G | FR-012, SC-007 (no-idle-traffic preserved from 001) |
