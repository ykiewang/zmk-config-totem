---

description: "Task list for Totem KeyBeacon Support"
---

# Tasks: Totem KeyBeacon Support

**Input**: Design documents from `/specs/001-keybeacon-support/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/, quickstart.md

**Tests**: No automated test suite is requested — this is a ZMK user-config change (West manifest + Kconfig). Verification is done via build-log inspection and a runtime BLE probe/app, mapped to the acceptance scenarios in the contracts. These verification tasks are included inline, not as TDD test tasks.

> **Implementation adjustment (2026-10-11)**: Prior CI showed that zmk-keybeacon ≥ v1.1.0 (incl. the pinned `v1.1.3`) fails to compile against ZMK `main` because the KBP 1.1 **Connectivity** path calls the removed `zmk_endpoints_selected()` (`keybeacon.c:249`, guarded by `CONFIG_ZMK_KEYBEACON_CONNECTIVITY`, default `y`). T006 sets `CONFIG_ZMK_KEYBEACON_CONNECTIVITY=n` and `CONFIG_ZMK_KEYBEACON_BATTERY=n` (both out of scope here) so the pinned tag builds green. The core characteristic (layer name + index + modifier state, FR-006) is unaffected. See research.md R2/R9.

**Organization**: Tasks are grouped by user story (from spec.md) so each story can be implemented and validated as an independent increment.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths are included in each task

## Path Conventions

This is a **ZMK user-config repository** (not a src/tests application). Paths are repo-relative, e.g. `config/west.yml`, `config/boards/shields/totem/`. Builds run via GitHub Actions (`.github/workflows/build.yml`) or locally with `west`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the starting state and that KeyBeacon's prerequisites already hold for Totem

- [X] T001 [P] Verify prerequisites (read-only): confirm `config/boards/shields/totem/Kconfig.defconfig` sets `CONFIG_ZMK_SPLIT_ROLE_CENTRAL` default `y` under `SHIELD_TOTEM_LEFT`, and that `build.yaml` uses `board: xiao_ble//zmk` for all targets (BLE board ⇒ `CONFIG_ZMK_BLE=y` automatically). Satisfies research R4/R5.
- [X] T002 [P] Verify layer labels (read-only) in `config/totem.keymap`: `label = "BASE"`, `"NAVI"`, `"SYM"`, `"ADJ"` are present, so no keymap change is needed (FR-010, SC-005; research R6).
- [X] T003 Establish a known-good baseline by building the three current `build.yaml` targets (`totem_left`, `totem_right`, `settings_reset`) before any edits — via a GitHub Actions run or local `west build` — and note success.

**Checkpoint**: Prerequisites confirmed; baseline builds green.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Declare and fetch the module dependency. Required by ALL user stories — nothing works until the module is on the manifest.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Add the module to the manifest in `config/west.yml`: add remote `ykiewang` (`url-base: https://github.com/ykiewang`) and project `zmk-keybeacon` (`remote: ykiewang`, `revision: v1.1.3`, NO `import:`). The existing `zmk` project (`remote: zmkfirmware`, `revision: main`, `import: app/west.yml`) and `self: { path: config }` MUST remain unchanged (data-model "Module Dependency Entry"; FR-001, FR-002, FR-003).
- [X] T005 Fetch the module: run `west update` locally (or rely on the CI step that runs it) and confirm `zmk-keybeacon` resolves at branch `main`. Keep YAML valid so `west update` parses (SC-002). → Delegated to CI (`west update` runs inside the GitHub Actions build; no local build per user instruction).

**Checkpoint**: Module declared and fetched — user stories can begin.

---

## Phase 3: User Story 1 - See the active layer and modifiers on the Mac (Priority: P1) 🎯 MVP

**Goal**: The central (left) half reports active layer name, layer index, and modifier state over its host BLE connection; a Mac app/probe displays it and reflects changes.

**Independent Test**: Build + flash the left half, connect to a Mac, and confirm the companion shows the active layer and modifiers, updating when layers/modifiers change.

### Implementation for User Story 1

- [X] T006 [US1] Enable the feature on the central target: add `CONFIG_ZMK_KEYBEACON=y` to `config/boards/shields/totem/totem_left.conf` (central half's conf ONLY). Do NOT add it to `config/boards/shields/totem/totem_right.conf` or `config/totem.conf` (data-model "Central Target Configuration"; FR-004; research R3). **Adjusted**: also set `CONFIG_ZMK_KEYBEACON_CONNECTIVITY=n` and `CONFIG_ZMK_KEYBEACON_BATTERY=n` so the pinned v1.1.3 builds (see adjustment note above).
- [X] T007 [US1] Build the central firmware and confirm success — GitHub Actions artifact, or local `west build -d build/left -b xiao_ble//zmk -- -DSHIELD=totem_left`.
- [ ] T008 [US1] Flash the keyboard: double-tap reset on the left half and drag the `totem_left …-zmk.uf2`; repeat for the right half with `totem_right …-zmk.uf2`; then connect the keyboard to the Mac over BLE.
- [ ] T009 [US1] Verify runtime reporting (contracts/keybeacon-report.md) with the `BleWidget` app or a locally-written `bleak` probe (the module ships no `tools/probe.py`, so write one from GETTING-STARTED.md): BASE shows as `BASE` not `L0` (K1/SC-005); BASE→NAVI reflected within ~1 s (K2/SC-001); modifier hold/release reflected (K3); idle produces no continuous update stream (K4/FR-007); device found among connected peripherals, not by scanning (K5).

**Checkpoint**: MVP complete — the core user-visible value (live layer/modifier display) works and is independently demonstrable.

---

## Phase 4: User Story 2 - Firmware still builds cleanly in CI (Priority: P2)

**Goal**: The existing GitHub Actions build keeps succeeding and produces the left, right, and settings_reset artifacts with the feature present.

**Independent Test**: Push the branch; confirm the workflow completes and the firmware archive contains all three UF2 artifacts.

### Implementation for User Story 2

- [X] T010 [US2] Trigger the workflow in `.github/workflows/build.yml` on the feature branch; confirm it completes successfully (B1) and the `firmware` archive contains `totem_left`, `totem_right`, and `settings_reset` UF2 files (B2–B4; SC-002; FR-009). No change to `build.yaml` or the workflow is expected.
- [X] T011 [P] [US2] Confirm minimal footprint: `git diff` against baseline touches ONLY `config/west.yml` and `config/boards/shields/totem/totem_left.conf`; no edits to module source or any shield `CMakeLists.txt`/`Kconfig*` (B7; SC-004; FR-008).

**Checkpoint**: CI remains green and artifacts are complete with the feature enabled.

---

## Phase 5: User Story 3 - KeyBeacon correctly scoped to the central half only (Priority: P3)

**Goal**: The feature is compiled into the left (central) build only and silently excluded from the right (peripheral) and settings_reset targets.

**Independent Test**: Inspect the three builds — `keybeacon.c` present/active only in the left build.

### Implementation for User Story 3

- [X] T012 [P] [US3] From the build logs/outputs, confirm `keybeacon.c` IS compiled in the `totem_left` build (B5; FR-004; SC-003).
- [X] T013 [P] [US3] Confirm `keybeacon.c` is NOT compiled for `totem_right` or `settings_reset` (B6; FR-005; SC-003) — the module's cmake guard `if(CONFIG_ZMK_KEYBEACON AND CONFIG_ZMK_BLE AND CONFIG_ZMK_SPLIT_ROLE_CENTRAL)` excludes them; verify no KeyBeacon output originates from these targets (K6).

**Checkpoint**: Scoping verified — peripheral and reset images are unaffected.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation and final end-to-end validation

- [X] T014 [P] Update `readme.md` to note zmk-keybeacon support (left/central half reports active layer + modifiers to a macOS app/probe) and that the module is tracked at `main`, reversible to a pinned tag by editing the single `revision:` line in `config/west.yml` (FR-011; plan Complexity Tracking).
- [ ] T015 [P] Run the full `specs/001-keybeacon-support/quickstart.md` validation checklist end-to-end and check off all acceptance items (SC-001..SC-005).
- [ ] T016 (Optional) Validate the upgrade/pin path (FR-011): temporarily set `config/west.yml` `revision:` to a released tag (e.g. `v1.0.0`), run `west update && west build`, confirm success, then revert to `main` per the user's request.

---

## CI Evidence (run 38138696991 — branch 001-keybeacon-support)

- T003: [CI baseline: prior successful runs on master-equivalent config; new branch run 38138696991 green]
- T007: [CI run 38138696991: totem_left build success]
- T010: [CI run 38138696991: workflow success; left/right/settings_reset artifacts built]
- T011: [git diff: only config/west.yml + totem_left.conf changed under config/]
- T012: [CI log: keybeacon.c compiled in totem_left]
- T013: [CI log: no keybeacon.c in totem_right / settings_reset]
- T014: [readme.md KEYBEACON section added]

> T008/T009/T015/T016 require physical flashing to a Mac and are left unchecked for the user to perform (no local build / no hardware in CI).

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS all user stories** (the module must be on the manifest and fetched).
- **User Story 1 (Phase 3)**: Depends on Foundational. This is the MVP.
- **User Story 2 (Phase 4)**: Depends on Foundational **and** US1 T006 (symbol enabled) so the build is exercised with the feature present.
- **User Story 3 (Phase 5)**: Depends on Foundational **and** US1 T006/T007 (a build exists with the feature enabled) to inspect per-target compilation.
- **Polish (Phase 6)**: Depends on US1 (and ideally US2/US3) being complete.

### User Story Dependencies

- **US1 (P1)**: Independent after Foundational — delivers standalone value.
- **US2 (P2)**: Builds on US1's enabled symbol; otherwise independently verifiable via CI.
- **US3 (P3)**: Builds on US1's enabled symbol/build; otherwise independently verifiable via build inspection.

> Note: Because the entire change is two lines, US2 and US3 are verification increments layered on the US1 edit rather than fully isolated code paths. This dependency is intentional and documented.

### Within Each User Story

- US1: T006 (enable) → T007 (build) → T008 (flash) → T009 (verify). Strictly sequential.
- US2: T010 then T011 (T011 is [P], read-only diff).
- US3: T012 and T013 are [P] (different targets).

### Parallel Opportunities

- Setup: T001 and T002 (read-only, different files) in parallel.
- US2: T011 parallel with monitoring T010.
- US3: T012 and T013 in parallel.
- Polish: T014 and T015 in parallel.

---

## Parallel Example: Setup Phase

```bash
# Read-only prerequisite checks together:
Task T001: "Verify CONFIG_ZMK_SPLIT_ROLE_CENTRAL / board BLE in Kconfig.defconfig + build.yaml"
Task T002: "Verify layer labels BASE/NAVI/SYM/ADJ in config/totem.keymap"
```

## Parallel Example: User Story 3

```bash
# Per-target compilation checks together:
Task T012: "Confirm keybeacon.c compiled in totem_left build"
Task T013: "Confirm keybeacon.c excluded from totem_right and settings_reset builds"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1: Setup (confirm prerequisites + baseline).
2. Phase 2: Foundational (declare + fetch the module) — CRITICAL, blocks everything.
3. Phase 3: User Story 1 (enable symbol, build, flash, verify live layer/modifier display).
4. **STOP and VALIDATE**: Demonstrate US1 on a Mac. This is a shippable MVP.

### Incremental Delivery

1. Setup + Foundational → module on the manifest.
2. US1 → live reporting works → **MVP demo**.
3. US2 → CI green with all three artifacts.
4. US3 → scoping verified (central only).
5. Polish → readme + full quickstart validation.

---

## Notes

- `[P]` = different files, no dependency on an incomplete task.
- `[Story]` labels map tasks to spec.md user stories for traceability.
- The only production edits are **T004** (`config/west.yml`) and **T006** (`config/boards/shields/totem/totem_left.conf`); every other task is a build/verify/doc step.
- Honor the request to pin the latest released tag `revision: v1.1.3` (FR-002) for reproducible builds; updating later is a one-line change (FR-011).
- Commit after T004 and after T006 (logical groups); avoid touching module source or shield CMake/Kconfig (FR-008).
