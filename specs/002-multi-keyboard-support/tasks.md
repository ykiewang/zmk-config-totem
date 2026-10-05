---

description: "Task list for Multi-Keyboard Support (Decouple App & Firmware from Totem)"
---

# Tasks: Multi-Keyboard Support (Decouple App & Firmware from Totem)

**Input**: Design documents from `/specs/002-multi-keyboard-support/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/discovery-and-identity.md, quickstart.md

**Tests**: Host logic tests ARE requested (plan "Testing": XCTest over `BleWidgetCore` for snapshot
parsing, name fallback, compatible-keyboard selection, settings migration — all pure logic, no
AppKit). Firmware has **no in-tree unit harness**; it is verified by the GitHub Actions build of all
`build.yaml` targets plus the on-device probe. Test tasks below therefore exist for the host stories
(US1, US2, US4) only.

**Organization**: Tasks are grouped by user story (priority order P1→P4) so each story is
independently implementable and testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on another incomplete task)
- **[Story]**: Which user story the task serves (US1, US2, US3, US4)
- Every task includes an exact repo-relative file path

## Path Conventions

- Firmware kit: `config/keybeacon_kit/`
- Firmware reference shield: `config/boards/shields/totem/`, keyboard config `config/totem.conf`
- Host app (SwiftPM): pure logic in `host/macos/Sources/BleWidgetCore/`, AppKit in
  `host/macos/Sources/BleWidget/`, tests in `host/macos/Tests/BleWidgetTests/`
- Probe: `tools/probe.py`
- Working contract: `specs/001-ble-status-widget/contracts/status-snapshot.md`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the no-regression baseline before refactoring either half.

- [X] T001 Capture the pre-refactor baseline: run `swift build` and `swift test` in `host/macos/`
      and confirm the current firmware builds all `build.yaml` targets (`totem_left`, `totem_right`,
      `settings_reset`); record pass/output as the no-regression reference for FR-017 / SC-004.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared, pure host entity that the three host stories (US1, US2, US4) build on.

**⚠️ CRITICAL**: Blocks the host stories (US1/US2/US4). US3 (firmware) is independent of this phase
and may start right after Setup.

- [X] T002 [P] Create pure `CompatibleKeyboard` value type in
      `host/macos/Sources/BleWidgetCore/CompatibleKeyboard.swift` with stored fields per
      data-model.md: `identifier: UUID` (from `CBPeripheral.identifier`, the stable disambiguator /
      reconnect key), `name: String?` (self-reported GAP name, may be nil/empty), `state:
      BLEConnectionState` (reuse the enum from `BLEClient.swift`), `isCompatible: Bool` (true once the
      custom service is confirmed). Make it `Equatable`. Add a pure static helper
      `isCompatible(discoveredServiceUUIDs:)` returning true iff the set contains the custom service
      `AA440AA0-F5ED-4C48-84A1-8062D20D3D55` — testable without CoreBluetooth. Do NOT add
      `displayName` yet (US2).

**Checkpoint**: Shared host model ready — host stories can begin.

---

## Phase 3: User Story 1 - App works with any contract-compliant keyboard, not just Totem (Priority: P1) 🎯 MVP

**Goal**: The app discovers, connects to, and displays live status from ANY keyboard that exposes the
custom status service — with no hardcoded `"TOTEM"` name match and no host-side registry — and
de-brands persisted settings while preserving existing users' saved panel position and lock state.

**Independent Test**: Point the app at a compatible keyboard whose name is not "Totem" (or rename it);
with zero app code/config changes it discovers, connects, and shows correct live layer/modifier state.
A device lacking the custom service is not treated as a keyboard. A legacy profile's panel
position/lock survive the upgrade.

### Tests for User Story 1 ⚠️ (write first, ensure they FAIL before implementation)

- [X] T003 [P] [US1] Identity tests in `host/macos/Tests/BleWidgetTests/KeyboardIdentityTests.swift`:
      assert `CompatibleKeyboard.isCompatible(discoveredServiceUUIDs:)` is true when the custom service
      `AA440AA0-…` is present and false when it is absent (FR-001/FR-003: identify by service, never by
      name/model).
- [X] T004 [P] [US1] Migration tests in `host/macos/Tests/BleWidgetTests/MigrationTests.swift` against
      an injected `UserDefaults` instance: given legacy `totemPanelFrame.<screenId>` /
      `totemPanelLocked` set and the new keys absent, the one-time migration copies legacy → new and
      sets `settingsMigratedV2 = true`; assert it "never overwrite[s] an existing new value" and
      "never reset[s]" (FR-004 + "existing Totem users" edge case).

### Implementation for User Story 1

- [X] T005 [P] [US1] Create `host/macos/Sources/BleWidgetCore/AppSettings.swift` wrapping an injectable
      `UserDefaults` (default `.standard`) with de-branded keys from data-model.md: `position` →
      `panelFrame.<screenId>` (legacy `totemPanelFrame.<screenId>`), `locked` → `panelLocked` (legacy
      `totemPanelLocked`, `false`=draggable default / `true`=click-through), and guard flag
      `settingsMigratedV2`. Implement the one-time launch migration: "if `settingsMigratedV2` is unset,
      then for each new key that is absent while its legacy `totem*` counterpart exists, copy legacy →
      new; finally set `settingsMigratedV2 = true`. Never overwrite an existing new value; never reset."
- [X] T006 [US1] Refactor `host/macos/Sources/BleWidgetCore/BLEClient.swift`: delete the
      `name?.localizedCaseInsensitiveContains("TOTEM")` gate (line ~52); keep the connected-peripheral
      enumeration `retrieveConnectedPeripherals(withServices: [hidServiceUUID, serviceUUID])`; treat a
      peripheral as a candidate without any name test; in `didDiscoverServices` confirm compatibility via
      `CompatibleKeyboard.isCompatible(discoveredServiceUUIDs:)` and drop a peripheral lacking the custom
      service (FR-003). Preserve the feature-001 connect/read/subscribe/reconnect flow unchanged.
- [X] T007 [US1] Update `host/macos/Sources/BleWidget/FloatingPanel.swift` to read/write panel position
      and lock through de-branded keys (replace the `totemPanelFrame` prefix and `totemPanelLocked`
      constants at lines 8–9 with `AppSettings`), so no `totem*` key is written going forward.
- [X] T008 [US1] Run the one-time settings migration at launch before the panel restores its position,
      in `host/macos/Sources/BleWidget/AppDelegate.swift` (`applicationDidFinishLaunching`, before
      `FloatingPanel()` is created) or `host/macos/Sources/BleWidget/main.swift`.

**Checkpoint**: Non-Totem keyboards connect and display status; settings are de-branded and migrated.
MVP is complete and independently demoable.

---

## Phase 4: User Story 2 - The keyboard tells the app its own name (Priority: P2)

**Goal**: Show a human-readable name that comes from the keyboard itself (its BLE GAP name), with a
graceful generic fallback when none is reported, and with no added per-change traffic.

**Independent Test**: Connect two compatible keyboards with different names — each appears under its own
correct name; a keyboard with a blank name shows the generic fallback; the name is not re-fetched as
status streams during typing.

**Depends on**: US1 (refactored `BLEClient` + `CompatibleKeyboard`).

### Tests for User Story 2 ⚠️ (write first, ensure they FAIL before implementation)

- [X] T009 [P] [US2] Name/fallback tests appended to
      `host/macos/Tests/BleWidgetTests/KeyboardIdentityTests.swift`: a non-empty GAP name is returned
      verbatim as `displayName`; an empty/nil/undecodable `name` yields the generic fallback (e.g.
      `Keyboard <short-id>`) — asserting data-model rule "`displayName` MUST never be blank" (FR-006).

### Implementation for User Story 2

- [X] T010 [US2] Add a pure computed `displayName: String` to
      `host/macos/Sources/BleWidgetCore/CompatibleKeyboard.swift`: return `name` when non-empty, else a
      generic fallback derived from a short form of `identifier` (e.g. `Keyboard <short-id>`); never
      blank (FR-006).
- [X] T011 [US2] In `host/macos/Sources/BleWidgetCore/BLEClient.swift`, read `CBPeripheral.name`
      **once at discovery/connection** (it is the GAP name obtained for free at enumeration) and carry
      it into the `CompatibleKeyboard`; MUST NOT re-read the name on `didUpdateValueFor` status
      notifications (FR-007 / data-model "read at most once per connection"). Surface the active
      keyboard's `displayName` to the delegate for the UI.
- [X] T012 [US2] Display the active keyboard's `displayName` in the menu bar (and optionally the panel)
      in `host/macos/Sources/BleWidget/AppDelegate.swift` so the connected keyboard is shown under its
      own name (SC-006).

**Checkpoint**: Connected keyboards are labeled by their own name with a safe fallback; US1 behavior
still intact.

---

## Phase 5: User Story 3 - Add the firmware feature to another keyboard with minimal, documented changes (Priority: P3)

**Goal**: Repackage the shared firmware logic as a self-contained, keyboard-independent **KeyBeacon
kit** behind the generic symbol `CONFIG_ZMK_KEYBEACON`, make the Totem shield the reference consumer,
ship a porting guide, and genericize the probe — all with Totem behavior unchanged.

**Independent Test**: Following only `config/keybeacon_kit/README.md`, add the feature to a scratch
shield; it builds for that keyboard's central role only, emits the status snapshot, and
`git diff config/keybeacon_kit/keybeacon.c` is empty (shared logic never edited); steps number ≤ 10.

**Depends on**: Setup only. Independent of the host stories — may run fully in parallel with US1/US2/US4.

### Implementation for User Story 3

- [X] T013 [P] [US3] Create `config/keybeacon_kit/keybeacon.c` by moving the shared logic from
      `config/boards/shields/totem/gatt_status.c` verbatim (GATT service/characteristic
      `AA440AA0-…`/`AA440AA1-…`, state read from `zmk/keymap.h` + `zmk/hid.h`, change-detection,
      notify-on-change). Confirm it is keyboard-independent — no Totem values baked in; it is "never
      edited to port".
- [X] T014 [P] [US3] Create `config/keybeacon_kit/Kconfig.keybeacon` declaring the generic symbol:
      `config ZMK_KEYBEACON` (`bool`, prompt "KeyBeacon: expose keyboard status (layer+mods) over a
      custom GATT characteristic", `depends on ZMK_BLE`, `default n`).
- [X] T015 [P] [US3] Create `config/keybeacon_kit/keybeacon.cmake`: a guarded `zephyr_library` snippet
      `if(CONFIG_ZMK_KEYBEACON AND CONFIG_ZMK_BLE AND CONFIG_ZMK_SPLIT_ROLE_CENTRAL)` that calls
      `zephyr_library()`, `zephyr_library_include_directories(${CMAKE_SOURCE_DIR}/include)` (R1:
      reach ZMK `app`-private headers from shield scope), and
      `zephyr_library_sources(${CMAKE_CURRENT_LIST_DIR}/keybeacon.c)`.
- [X] T016 [P] [US3] Create `config/keybeacon_kit/README.md` porting guide: the ≤10 documented
      per-keyboard steps (make kit available → `include(<kit>/keybeacon.cmake)` in shield
      `CMakeLists.txt` → `rsource <kit>/Kconfig.keybeacon` from shield Kconfig → `CONFIG_ZMK_KEYBEACON=y`
      in the keyboard `.conf`), the **central BLE role prerequisite**, and the R1 app-private-header
      constraint that keeps the feature shield-scoped (FR-011).
- [X] T017 [US3] Edit `config/boards/shields/totem/CMakeLists.txt` to become the reference consumer:
      replace the inline `if(CONFIG_ZMK_TOTEM_GATT_STATUS …)` block with
      `include(${CMAKE_CURRENT_LIST_DIR}/../../keybeacon_kit/keybeacon.cmake)` (needs T013–T015).
- [X] T018 [US3] Edit `config/boards/shields/totem/Kconfig.defconfig`: `rsource
      "../../keybeacon_kit/Kconfig.keybeacon"` and remove the old `config ZMK_TOTEM_GATT_STATUS` block
      (lines ~21–24); leave the `ZMK_KEYBOARD_NAME` / split-role defaults untouched.
- [X] T019 [US3] Delete `config/boards/shields/totem/gatt_status.c` (its logic now lives in the kit as
      `keybeacon.c`).
- [X] T020 [US3] Update `config/totem.conf`: replace `CONFIG_ZMK_TOTEM_GATT_STATUS=y` with
      `CONFIG_ZMK_KEYBEACON=y`.
- [X] T021 [P] [US3] Genericize `tools/probe.py`: remove the `"TOTEM"` name filter (line ~89) and the
      "no connected TOTEM found" message (line ~97); discover by the custom service UUID (same rule as
      the host), keep the `retrieveConnectedPeripheralsWithServices_([HID_UUID, SERVICE_UUID])`
      enumeration and the scan fallback, and print the discovered peripheral's `.name` for confirmation
      (FR-012 / MR7).
- [ ] T022 [US3] Verify via the repo's GitHub Actions build that all three `build.yaml` targets
      (`totem_left`, `totem_right`, `settings_reset`) build, and that the kit object/service-UUID symbol
      is linked **only** in the central (`totem_left`) image and absent from `totem_right` and
      `settings_reset` (FR-010 / SC-004; needs T017–T020).

**Checkpoint**: Totem builds unchanged behavior from a reusable kit; the feature is central-only; the
probe and a scratch port both work via the service contract.

---

## Phase 6: User Story 4 - Choose and remember the active keyboard when several are present (Priority: P4)

**Goal**: With one compatible keyboard, auto-connect; with several and none remembered, let the user
pick from a menu-bar chooser; remember the choice (by stable identifier) and reconnect to it next
launch; always a single panel for the selected keyboard.

**Independent Test**: Connect two compatible keyboards, select one, restart the app → it reconnects to
the remembered one and shows its status in a single panel; switching updates the single panel.

**Depends on**: US1 (discovery + `AppSettings`); integrates with US2 names for the chooser labels.

### Tests for User Story 4 ⚠️ (write first, ensure they FAIL before implementation)

- [X] T023 [P] [US4] Selection tests appended to
      `host/macos/Tests/BleWidgetTests/KeyboardIdentityTests.swift` for the pure selection resolver:
      exactly 1 candidate → auto-select it (FR-013); a remembered identifier present among candidates →
      auto-select it (FR-015); ≥ 2 candidates and none remembered → return nil / no auto-select
      (FR-014, "no silent guess").

### Implementation for User Story 4

- [X] T024 [US4] Extend `host/macos/Sources/BleWidgetCore/AppSettings.swift` with
      `selectedKeyboardIdentifier: UUID?` persisted as a UUID string (MR4/FR-015), and add a pure
      `resolveSelection(candidates:remembered:) -> UUID?` helper (in `AppSettings` or
      `CompatibleKeyboard.swift`) implementing the three selection rules — the unit under test in T023.
- [X] T025 [US4] Wire `host/macos/Sources/BleWidgetCore/BLEClient.swift` to build the full candidate
      list from enumeration, call `resolveSelection(...)` to decide auto-connect vs await-choice, expose
      the candidate list + active selection to the delegate, persist `selectedKeyboardIdentifier` on an
      explicit selection, and reconnect the remembered identifier on launch via the enumeration match or
      `retrievePeripherals(withIdentifiers:)` (FR-013/014/015/016); keep exactly one active connection.
- [X] T026 [US4] Add a menu-bar **"Keyboard ▸"** submenu in
      `host/macos/Sources/BleWidget/AppDelegate.swift` listing compatible keyboards by `displayName`
      with a checkmark on the active one; selecting an item switches the single connection and persists
      the choice (MR6/FR-014/FR-016).

**Checkpoint**: Multi-keyboard selection works and survives restart; a single panel tracks the choice.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Contract governance, docs, and end-to-end validation spanning all stories.

- [X] T027 [P] Fold the normative text of
      `specs/002-multi-keyboard-support/contracts/discovery-and-identity.md` into the canonical
      `specs/001-ble-status-widget/contracts/status-snapshot.md` as a backward-compatible clarification
      (identity = custom service UUID; display name = GAP name; no payload layout change / no version
      bump) — FR-018 contract governance.
- [X] T028 [P] Update `readme.md` (both EN and ZH sections): replace `CONFIG_ZMK_TOTEM_GATT_STATUS`
      with `CONFIG_ZMK_KEYBEACON` (lines ~47 and ~109) and document multi-keyboard support + the
      de-branded settings behavior.
- [ ] T029 Run the `quickstart.md` validation scenarios A–G end to end and confirm each expected
      outcome (firmware targets/central-only, scratch port ≤10 steps with no shared-logic edits,
      `swift test` green, non-Totem connect, choose/remember, legacy-settings upgrade, probe-by-contract).
- [ ] T030 [P] Confirm against the T001 baseline that feature 001's acceptance scenarios still pass with
      no regression (SC-004) and that conveying the name adds zero idle traffic over a 1-hour idle
      session (SC-007).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies.
- **Foundational (Phase 2)**: after Setup. Blocks host stories US1/US2/US4. Does NOT block US3.
- **US1 (Phase 3)**: after Foundational.
- **US2 (Phase 4)**: after US1 (uses the refactored `BLEClient` and `CompatibleKeyboard`).
- **US3 (Phase 5)**: after Setup only — firmware is independent of the host; can run fully in parallel
  with US1/US2/US4.
- **US4 (Phase 6)**: after US1 (extends `AppSettings` + discovery); chooser labels use US2 names.
- **Polish (Phase 7)**: after the stories it validates are complete.

### Within Each User Story

- Tests (T003/T004, T009, T023) are written first and must FAIL before implementation.
- Models/pure helpers before services; services before UI:
  - US1: T005/T006 → T007 → T008
  - US2: T010 → T011 → T012
  - US3: T013–T016 (kit files) → T017/T018/T019/T020 (shield wiring) → T022 (CI); T021 (probe) parallel
  - US4: T024 → T025 → T026

### Parallel Opportunities

- US1 tests T003 and T004 (different files) run together; implementation T005 and T006 (different files)
  run together.
- US3 kit-creation tasks T013, T014, T015, T016 (four new files) run together; probe T021 runs anytime.
- Entire US3 (firmware) runs in parallel with the host stories if staffed separately.
- Polish T027, T028, T030 (different files) run together.

---

## Parallel Example: User Story 1

```bash
# Tests first (different files, in parallel):
Task: "Identity tests in host/macos/Tests/BleWidgetTests/KeyboardIdentityTests.swift"
Task: "Migration tests in host/macos/Tests/BleWidgetTests/MigrationTests.swift"

# Then implementation (different files, in parallel):
Task: "Create AppSettings in host/macos/Sources/BleWidgetCore/AppSettings.swift"
Task: "Refactor BLEClient in host/macos/Sources/BleWidgetCore/BLEClient.swift"
```

## Parallel Example: User Story 3 (firmware kit)

```bash
# Four new kit files have no inter-dependencies:
Task: "Create config/keybeacon_kit/keybeacon.c"
Task: "Create config/keybeacon_kit/Kconfig.keybeacon"
Task: "Create config/keybeacon_kit/keybeacon.cmake"
Task: "Create config/keybeacon_kit/README.md"
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Phase 1 Setup (baseline) → Phase 2 Foundational (`CompatibleKeyboard`) → Phase 3 US1.
2. **STOP and VALIDATE**: a non-Totem keyboard connects and shows live status with zero code/config
   changes; a non-service device is rejected; legacy panel settings survive. Demo the MVP.

### Incremental Delivery

1. Setup + Foundational → host foundation ready.
2. US1 → decoupled single-keyboard readout (MVP) → demo.
3. US2 → self-reported names with fallback → demo.
4. US4 → choose & remember among multiple keyboards → demo.
5. US3 (firmware) proceeds in parallel at any time → reusable kit + porting guide + generic probe.

### Parallel Team Strategy

- Developer A: host track (Foundational → US1 → US2 → US4).
- Developer B: firmware track (US3) in parallel from the start — no dependency on the host track.
- Integrate at Polish: fold the contract, update docs, run quickstart A–G, confirm no regression.

---

## Notes

- `[P]` = different files, no dependency on an incomplete task.
- `[Story]` label maps each task to its user story for traceability (Setup/Foundational/Polish carry no
  story label).
- Host pure logic (`CompatibleKeyboard`, `AppSettings`, selection resolver) lives in `BleWidgetCore`
  so it is unit-testable without AppKit/CoreBluetooth, per the plan's Testing section.
- Firmware is verified by CI build of all `build.yaml` targets + the on-device probe, not unit tests.
- Shared firmware logic `config/keybeacon_kit/keybeacon.c` MUST NOT be edited to port (SC-003).
- Commit after each task or logical group; stop at any checkpoint to validate a story independently.
