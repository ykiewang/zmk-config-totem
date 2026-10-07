---

description: "Task list for ZMK Module Distribution"
---

# Tasks: ZMK Module Distribution

**Input**: Design documents from `specs/005-zmk-module-distribution/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/module-interface.md, quickstart.md

**Tests**: No unit-test framework is requested for this firmware/build/docs feature. Validation is performed via the `quickstart.md` scenarios (A–E) against real builds and on-device probing — no separate TDD test suite is generated.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Firmware repo** (this repo, `zmk-config-totem`): `config/` (incl. the ZMK manifest at `config/west.yml`), `scripts/`, `readme.md` at repository root
- **Module repo content** (destined for `github.com/ykiewang/zmk-keybeacon`): authored in place under `config/keybeacon_kit/` and carried out by the migration split

---

## Phase 1: Setup (make the kit a valid Zephyr module in place)

**Purpose**: Add the Zephyr module metadata alongside the existing kit files so `config/keybeacon_kit/` becomes a complete, self-contained module. These files are additive and inert until a consumer references the module, so they do not disturb Totem's current `include()`-based build.

- [X] T001 [P] Create `config/keybeacon_kit/zephyr/module.yml` declaring `name: zmk-keybeacon`, `build.cmake: .`, `build.kconfig: Kconfig.keybeacon` (per contracts/module-interface.md §1.1)
- [X] T002 [P] Create `config/keybeacon_kit/CMakeLists.txt` containing exactly `include(${CMAKE_CURRENT_LIST_DIR}/keybeacon.cmake)` (thin cmake entry; introduces no logic, per research.md R4)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Verify the moved/retained kit files are correct and byte-stable as a module. These checks block ALL user stories because every story depends on the module being valid and the GATT behavior being unchanged.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Verify `config/keybeacon_kit/keybeacon.cmake` resolves correctly in module context: confirm the guard `if(CONFIG_ZMK_KEYBEACON AND CONFIG_ZMK_BLE AND CONFIG_ZMK_SPLIT_ROLE_CENTRAL)` is preserved verbatim and that `${CMAKE_SOURCE_DIR}/include` and `${CMAKE_CURRENT_LIST_DIR}/keybeacon.c` remain correct (no edits expected)
- [X] T004 Confirm `config/keybeacon_kit/keybeacon.c` is byte-for-byte unchanged from the current shipped version (modularization MUST NOT touch GATT logic — Service UUID `AA440AA0-…`, payload `[layer_index][mods][layer_name]` unchanged, per contracts §1.4)
- [X] T005 Confirm `config/keybeacon_kit/Kconfig.keybeacon` is unchanged: symbol `ZMK_KEYBEACON` is `bool`, `depends on ZMK_BLE`, `default n` (per contracts §1.2)

**Checkpoint**: The module is valid and self-contained — user story work can begin.

---

## Phase 3: User Story 1 - 新用户零拷贝接入 (Priority: P1) 🎯 MVP

**Goal**: Any ZMK keyboard with a central BLE role can enable KeyBeacon by adding one entry to `west.yml` and one `CONFIG_ZMK_KEYBEACON=y` line — with zero file copying and no `include()`/`rsource` wiring.

**Independent Test**: From a clean config that references the module (local path acceptable pre-publish) plus `CONFIG_ZMK_KEYBEACON=y`, a central build links `keybeacon.c` and a peripheral build excludes it — matching quickstart.md Scenario A.

- [X] T006 [US1] Rewrite Step 1 of `config/keybeacon_kit/GETTING-STARTED.md` from "copy the directory" to "add the module to `west.yml`", and remove the former Step 2 (`include(...)`) and Step 3 (`rsource ...`) so the only remaining user wiring is the `.conf` symbol (per spec FR-003 and research.md R2)
- [X] T007 [US1] In `config/keybeacon_kit/GETTING-STARTED.md`, document BOTH onboarding scenarios required by FR-007 (sequential after T006, same file): (a) **no `west.yml` yet** — create the full minimal manifest (remotes `zmkfirmware` + `ykiewang`, `zmk` with `import: app/west.yml`, `zmk-keybeacon` pinned by tag, `self: path: config`); (b) **existing `west.yml`** — append only the `zmk-keybeacon` project entry. Reference contracts/module-interface.md §2.1
- [ ] T008 [US1] Validate quickstart.md Scenario A locally using the **canonical pre-publish mechanism** `ZEPHYR_EXTRA_MODULES=<repo>/config/keybeacon_kit` with `CONFIG_ZMK_KEYBEACON=y`: confirm the central target links `keybeacon.c` and the peripheral target excludes it (no `include()`/`rsource` present in the consumer), and record the verification result for research.md R7's two assumptions (`${CMAKE_SOURCE_DIR}/include` reachability + `ZMK_KEYBEACON` visibility)

**Checkpoint**: A new user can onboard with only `west.yml` + `.conf` edits — MVP value proven.

---

## Phase 4: User Story 2 - 模块升级不破坏用户仓库 (Priority: P2)

**Goal**: Upgrading the module requires changing only the `revision` field in `west.yml`; no consumer source files change.

**Independent Test**: Changing the module `revision` and running `west update && west build` rebuilds successfully with zero changes to the consumer's `config/`, shield `CMakeLists.txt`, or `Kconfig.defconfig` — matching quickstart.md Scenario D.

- [X] T009 [P] [US2] Create `config/keybeacon_kit/CHANGELOG.md` with an initial `v1.0.0` entry and the semver policy: MAJOR = GATT/payload breaking change, MINOR = new backward-compatible Kconfig symbol, PATCH = fix with no interface change (per contracts §3)
- [X] T010 [US2] Document the version-pinning convention in `config/keybeacon_kit/GETTING-STARTED.md`: `revision` MUST be a semver tag (e.g. `v1.0.0`), never `main`; include the upgrade flow (edit `revision` → `west update` → `west build`) (per research.md R5)
- [ ] T011 [US2] Validate quickstart.md Scenario D: bumping the module `revision` rebuilds with no diff in the consumer `config/`, shield `CMakeLists.txt`, or `Kconfig.defconfig` (only `west.yml` changes)

**Checkpoint**: Module upgrades are a single-line `west.yml` change — User Stories 1 AND 2 both validated.

---

## Phase 5: User Story 3 - 现有 Totem 迁移 + 分发 (Priority: P3)

**Goal**: Remove the in-repo `keybeacon_kit/` copy; Totem consumes the module via `west.yml`; the kit is distributed from the standalone `zmk-keybeacon` repo with git history preserved.

**Independent Test**: With `config/keybeacon_kit/` removed and Totem wired to the module via `west.yml`, `totem_left`/`totem_right` build and on-device probe output matches pre-migration — matching quickstart.md Scenarios B, C, E.

- [X] T012 [US3] Edit the firmware `config/west.yml` (ZMK convention — Totem already ships one): add the `ykiewang` remote and append the `zmk-keybeacon` project pinned to tag `v1.0.0`, keeping `zmk` with `import: app/west.yml` and `self: path: config` (per contracts §2.1). Pre-publish validation uses the canonical `ZEPHYR_EXTRA_MODULES` mechanism from T008 — do **not** introduce a second local-path mechanism here; the `revision` now resolves to the published tag (T017)
- [X] T013 [US3] Remove the line `include(${CMAKE_CURRENT_LIST_DIR}/../../../keybeacon_kit/keybeacon.cmake)` from `config/boards/shields/totem/CMakeLists.txt` (file becomes comment-only or is deleted) — MUST run after T012 so the module provides the source (per research.md R2/R6)
- [X] T014 [US3] Remove the line `rsource "../../../keybeacon_kit/Kconfig.keybeacon"` from `config/boards/shields/totem/Kconfig.defconfig` — MUST run after T012 (per research.md R2/R6)
- [X] T015 [US3] Finalize `config/keybeacon_kit/README.md` as the module-level integration guide: **remove the copy-based porting steps table (the 1–5 steps using `include()`/`rsource`)** and replace with the west-module flow (`west.yml` + `.conf`) so no copy/include/rsource wording remains — this file is carried into the module repo by the split
- [X] T016 [US3] Create `scripts/migrate/split-keybeacon-module.sh` that subtree-splits `config/keybeacon_kit/` into the `zmk-keybeacon` module repo tree (preserving `keybeacon.c` history, re-rooting kit files to the module root) (mirrors feature 003's history-preserving split in research.md R4)
- [X] T017 [P] [US3] Create `scripts/migrate/README.md` documenting the manual, non-CI-verifiable steps: create `github.com/ykiewang/zmk-keybeacon`, push the split tree, tag `v1.0.0` (maintainer action requiring GitHub auth)
- [X] T018 [US3] Remove `config/keybeacon_kit/` from the firmware repo after the split (content now lives in the module repo and is fetched via `west`) — destructive; MUST run after T008 and T011 if sharing one workspace
- [X] T019 [P] [US3] Update firmware `readme.md` to point users to the `zmk-keybeacon` module and the Releases/tags for versions (replace any in-repo `keybeacon_kit` references)
- [ ] T020 [US3] Validate quickstart.md Scenarios B, C, E: `totem_left`/`totem_right` build via the module; on-device `probe.py` output matches the pre-migration baseline; peripheral and `settings_reset` exclude `keybeacon.c`. If the keybeacon app repo's conformance tool is available, run it for a per-item cross-check (SC-003); otherwise record conformance-tool verification as deferred

**Checkpoint**: Totem is migrated to the module, the in-repo copy is gone, and the kit is distributable from one canonical repo.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Repo-wide consistency and full end-to-end validation.

- [ ] T021 [P] Verify all `build.yaml` targets build cleanly through GitHub Actions with the new `west.yml` manifest present (per plan.md constraint; Constitution Principle V)
- [X] T022 [P] Grep the repository for stale `keybeacon_kit` path references in `docs/` and `specs/` and reconcile or redirect them to the module
- [ ] T023 Run the full `quickstart.md` validation (Scenarios A–E) end to end and record the results

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Stories (Phase 3–5)**: All depend on Foundational completion
  - Independently testable from a clean checkout
  - In a single shared workspace, run in priority order P1 → P2 → P3 because US3 (T018) removes `config/keybeacon_kit/`, which US1 (T008) and US2 (T011) validate against in place
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US1 (P1)**: After Foundational. No dependency on other stories. Validated against the in-place module.
- **US2 (P2)**: After Foundational. Independent of US1/US3. Adds versioning artifacts + upgrade validation.
- **US3 (P3)**: After Foundational. Internally ordered: T012 (`west.yml`) → T013/T014 (remove Totem wiring) → T016 (split) → T018 (remove dir). Destructive step T018 must come after US1/US2 local validations when sharing one tree.

### Critical Intra-Story Ordering (US3)

- T012 **before** T013 and T014 (module must provide the source before the inline wiring is removed, or Totem loses KeyBeacon)
- T015 **before** T016 (README finalized before the split carries it out)
- T016 **before** T018 (split the content out before deleting the local copy)

### Parallel Opportunities

- T001 and T002 (different files) run in parallel
- Within US1: T006 → T007 are sequential (both edit `GETTING-STARTED.md`); T008 validation follows both
- Within US3: T017 and T019 are [P] (different files) and can run alongside the T016 script authoring
- Polish: T021 and T022 are [P]

---

## Parallel Example: Phase 1 Setup

```bash
# Author both module-metadata files together (different files, no dependency):
Task T001: "Create config/keybeacon_kit/zephyr/module.yml (name/build.cmake/build.kconfig)"
Task T002: "Create config/keybeacon_kit/CMakeLists.txt with include(... keybeacon.cmake)"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (module.yml + CMakeLists wrapper)
2. Complete Phase 2: Foundational (verify cmake/c/Kconfig unchanged & valid)
3. Complete Phase 3: US1 (onboarding doc + local module validation)
4. **STOP and VALIDATE**: quickstart Scenario A — a clean config builds with only `west.yml` + `.conf`
5. This proves the zero-copy value proposition before any destructive migration

### Incremental Delivery

1. Setup + Foundational → module is valid in place
2. US1 → new-user onboarding proven (MVP)
3. US2 → versioning/upgrade proven (single-line `west.yml` change)
4. US3 → Totem migrated, in-repo copy removed, kit distributed from the standalone repo
5. Polish → CI green across all `build.yaml` targets + full quickstart run

### Distribution Note

Publishing to `github.com/ykiewang/zmk-keybeacon` (create repo, push split tree, tag `v1.0.0`) is a **manual maintainer step** (T017) that cannot be verified inside this repo's CI — mirroring feature 003's cross-repo push. Pre-publish, all local validation uses the in-place module via the single canonical mechanism `ZEPHYR_EXTRA_MODULES` (T008); no local-path `west.yml` variant is introduced.

---

## Notes

- [P] tasks = different files, no dependencies
- `keybeacon.c` MUST NOT be edited during this feature — modularization is packaging/distribution only (Constitution Principles I, II, III)
- The cmake guard keeps `keybeacon.c` out of peripheral/`settings_reset` images at all times
- Validate via quickstart scenarios, not unit tests (none requested)
- Commit after each task or logical group; US3's destructive removal (T018) should be its own commit
