---

description: "Task list for BLE Keyboard Status Widget"

---

# Tasks: BLE Keyboard Status Widget

**Input**: Design documents from `/specs/001-ble-status-widget/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/status-snapshot.md, quickstart.md

**Tests**: Host-side tests ARE requested (spec §Testing Strategy mandates XCTest for `KeyboardStatus.parse`). Firmware has no unit framework — validated by CI build + on-device probe (no firmware test tasks).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Exact file paths are included in every task

## Path Conventions

- **Firmware**: `config/boards/shields/totem/`, `config/totem.conf`
- **Host (macOS app)**: `host/macos/`
- **Tools**: `tools/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the build surface on both sides so the feature can compile.

- [X] T001 [P] Add Kconfig symbol `CONFIG_ZMK_TOTEM_GATT_STATUS` (bool, `depends on ZMK_BLE`, `default n`) in `config/boards/shields/totem/Kconfig`
- [X] T002 [P] Create shield build file `config/boards/shields/totem/CMakeLists.txt` guarding on `CONFIG_ZMK_TOTEM_GATT_STATUS` AND `CONFIG_ZMK_SPLIT_ROLE_CENTRAL`, adding `zephyr_library_include_directories(${CMAKE_SOURCE_DIR}/include)` and `gatt_status.c`
- [X] T003 Enable `CONFIG_ZMK_TOTEM_GATT_STATUS=y` in `config/totem.conf`
- [X] T004 [P] Scaffold the macOS app (`host/macos/Package.swift` or `BleWidget.xcodeproj`) with `Sources/` and `Tests/` targets and an `Info.plist` setting `LSUIElement = true`
- [X] T005 [P] Rework the probe script into `tools/probe.py`, parsing payload `[idx][mods][name]` per `contracts/status-snapshot.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Plumbing shared by every user story — firmware emitting snapshots, host receiving and parsing them, panel and app shell existing.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T006 Define the GATT service/characteristic in `config/boards/shields/totem/gatt_status.c`: primary service `AA440AA0-F5ED-4C48-84A1-8062D20D3D55`, characteristic `AA440AA1-...` with `BT_GATT_CHRC_READ | BT_GATT_CHRC_NOTIFY`, `BT_GATT_PERM_READ`, and a `BT_GATT_CCC`
- [X] T007 Implement state read helpers in `config/boards/shields/totem/gatt_status.c`: layer index via `zmk_keymap_highest_layer_active()`, index→id via `zmk_keymap_layer_index_to_id()`, name via `zmk_keymap_layer_name()` (treat `NULL`/`""` as empty), mods via `zmk_hid_get_explicit_mods()`
- [X] T008 Implement snapshot packing, cache comparison, `bt_gatt_notify` on change only, `ZMK_LISTENER`/`ZMK_SUBSCRIPTION` to `zmk_layer_state_changed` and `zmk_keycode_state_changed`, and `SYS_INIT` initial read in `config/boards/shields/totem/gatt_status.c`
- [X] T009 Implement `host/macos/Sources/BLEClient.swift`: `CBCentralManager` on main queue, connect via `retrieveConnectedPeripherals(withServices: [CBUUID(0x1812), custom])`, `discoverServices`/`discoverCharacteristics`, READ initial value, `setNotifyValue(true)`
- [X] T010 Implement `host/macos/Sources/KeyboardStatus.swift`: parse `[0]=layer_index`, `[1]=mods`, `[2..]=UTF-8 name` into `{ layerName, mods, connected }`; reject payloads shorter than 2 bytes; fall back to `L{index}` on empty/undecodable name
- [X] T011 Implement `host/macos/Sources/FloatingPanel.swift` base window: `.borderless`, `level = .floating`, `isOpaque = false`, `backgroundColor = .clear`, `canBecomeKey = false`, `collectionBehavior = [.canJoinAllSpaces, .stationary]`
- [X] T012 Implement `host/macos/Sources/AppDelegate.swift` + `main.swift`: app lifecycle, `NSStatusItem` creation, floating panel instantiation

**Checkpoint**: Firmware emits and host receives/parses snapshots; foundation ready for all stories.

---

## Phase 3: User Story 1 - See the active layer (Priority: P1) 🎯 MVP

**Goal**: The panel shows the active layer's name and updates live.

**Independent Test**: Connect the panel, switch layers, confirm the shown name tracks the real layer.

### Tests for User Story 1

- [X] T013 [P] [US1] XCTest for `KeyboardStatus.parse` layer-name paths in `host/macos/Tests/KeyboardStatusTests.swift`: normal name, empty name → `L{index}`, undersized packet rejected, invalid UTF-8 → `L{index}`

### Implementation for User Story 1

- [X] T014 [US1] Render the layer name as a text label in `host/macos/Sources/FloatingPanel.swift`
- [X] T015 [US1] Wire `BLEClient` → `KeyboardStatus.parse` → panel label update in `host/macos/Sources/AppDelegate.swift`
- [X] T016 [US1] Board-level verify: build firmware, flash `totem_left`, run `tools/probe.py`, confirm `layer_index` + `layer_name` match physical layer for all four layers

**Checkpoint**: User Story 1 is fully functional — live layer readout delivered (MVP).

---

## Phase 4: User Story 2 - See active modifiers, merged (Priority: P2)

**Goal**: Four fixed modifier indicators highlight when the matching modifier is held; left/right merge.

**Independent Test**: Hold/release each of the 8 modifier keys; the matching indicator highlights; both halves light the same indicator.

### Tests for User Story 2

- [X] T017 [P] [US2] XCTest for modifier parsing/merge in `host/macos/Tests/KeyboardStatusTests.swift`: each bit set/clear, and merge (Shift `0x02|0x20`, Control `0x01|0x10`, Alt `0x04|0x40`, Gui `0x08|0x80`)

### Implementation for User Story 2

- [X] T018 [P] [US2] Implement the four fixed-slot modifier indicator views in `host/macos/Sources/FloatingPanel.swift` (no reflow, same row as layer name)
- [X] T019 [US2] Implement merge + active/inactive highlight rendering in `host/macos/Sources/FloatingPanel.swift`

**Checkpoint**: User Stories 1 and 2 both work independently.

---

## Phase 5: User Story 3 - Place and dock the panel (Priority: P3)

**Goal**: Panel is draggable and remembers its position; a persistent lock toggle makes it click-through.

**Independent Test**: Drag, restart, verify position restored; toggle lock, verify clicks pass through and the state persists.

### Implementation for User Story 3

- [X] T020 [US3] Enable dragging via `isMovableByWindowBackground = true` in `host/macos/Sources/FloatingPanel.swift`
- [X] T021 [US3] Persist window frame per screen identity in `UserDefaults` and restore/clamp to visible bounds on launch in `host/macos/Sources/FloatingPanel.swift`
- [X] T022 [US3] Implement the lock/click-through state (`ignoresMouseEvents`) with `UserDefaults` persistence in `host/macos/Sources/FloatingPanel.swift`
- [X] T023 [US3] Wire the menu-bar "lock / click-through" toggle and default first-launch position (top-right + margin) in `host/macos/Sources/AppDelegate.swift`

**Checkpoint**: All three stories independently functional.

---

## Phase 6: User Story 4 - Stay connected, fail gracefully (Priority: P4)

**Goal**: The panel recovers on its own and shows clear failure states without crashing.

**Independent Test**: Disconnect/reconnect, toggle Bluetooth off/on; panel shows not-connected then recovers; no crash.

### Implementation for User Story 4

- [X] T024 [US4] Implement the reconnect loop (interval retry via `retrieveConnectedPeripherals`, remember peripheral identifier) and auto-resubscribe in `host/macos/Sources/BLEClient.swift`
- [X] T025 [US4] Implement `connecting`/`connected`/`not_connected`/`unavailable` states and surface status + reconnect control in the menu bar in `host/macos/Sources/AppDelegate.swift`
- [X] T026 [US4] Ensure malformed/undersized payloads are discarded and never shown; do not render stale state as current in `host/macos/Sources/KeyboardStatus.swift`

**Checkpoint**: All user stories independently functional.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and hardening.

- [X] T027 [P] Run the full XCTest suite and confirm all pass in `host/macos/Tests/`
- [X] T028 Confirm GitHub Actions builds all `build.yaml` targets (`totem_left`, `totem_right`, `settings_reset`) with the feature present only on the central half
- [ ] T029 Execute the `specs/001-ble-status-widget/quickstart.md` scenarios (13 end-to-end) and record results
- [ ] T030 Verify idle behavior: 1-hour idle produces zero notifications (SC-002) via `tools/probe.py` log
- [ ] T031 [P] Update `readme.md`/docs with the feature's usage (menu-bar controls, lock toggle) if warranted

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Stories (Phase 3–6)**: All depend on Foundational
- **Polish (Phase 7)**: Depends on all targeted user stories

### User Story Dependencies

- **US1 (P1)**: After Foundational — no dependencies on other stories
- **US2 (P2)**: After Foundational — shares the parser/panel with US1 but independently testable
- **US3 (P3)**: After Foundational — panel window behavior, independent of US1/US2 data
- **US4 (P4)**: After Foundational — connection lifecycle, independent of rendering

### Within/Cross phases

- T006–T008 (firmware) and T009–T012 (host) can proceed in parallel — different files, coupled only by the frozen contract
- Firmware bootstrapping (T006–T008) should land early so board verification (T016) is unblocked
- Tests within a story (T013, T017) should be written before their implementation tasks

### Parallel Opportunities

- T001, T002, T004, T005 in Setup
- T006–T008 (firmware) alongside T009–T012 (host)
- T013 and T017 (tests) can be written together
- T018 alongside T019-adjacent UI work is sequential (same file)

---

## Parallel Example: Foundation

```bash
# Firmware track and host track in parallel:
Task: "Define GATT service in config/boards/shields/totem/gatt_status.c"
Task: "Implement BLEClient in host/macos/Sources/BLEClient.swift"
Task: "Implement KeyboardStatus parser in host/macos/Sources/KeyboardStatus.swift"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1: Setup
2. Phase 2: Foundational (CRITICAL)
3. Phase 3: User Story 1
4. **STOP and VALIDATE**: layer name tracks physical layer
5. Demo the MVP

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. US1 → validate → MVP (live layer name)
3. US2 → validate → modifier indicators
4. US3 → validate → position/lock
5. US4 → validate → resilience

---

## Notes

- [P] = different files, no dependencies
- [Story] label maps tasks to user stories for traceability
- Commit after each logical group
- Firmware validation = CI build + `tools/probe.py` on device; host validation = XCTest + panel checks
- Contract changes require a coordinated bump (see `contracts/status-snapshot.md`)
