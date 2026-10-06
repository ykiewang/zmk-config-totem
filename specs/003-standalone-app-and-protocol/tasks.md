---

description: "Task list for Standalone App Repo, Shared Protocol Standard & Downloadable Release"
---

# Tasks: Standalone App Repo, Shared Protocol Standard & Downloadable Release

**Input**: Design documents from `/specs/003-standalone-app-and-protocol/`

**Prerequisites**: plan.md, spec.md, research.md (R1–R8), data-model.md,
contracts/{protocol-standard,firmware-pin,release-artifact}.md, quickstart.md (A–I)

**Tests**: This feature is mostly packaging/release/governance; most verification is via CI jobs,
the conformance tool, and `quickstart.md` scenarios rather than unit tests. Two test tasks are
included where they pin **new behavior**: the no-regression gate on the moved app (keep existing
XCTest green) and a US4 unit test for the new protocol-compatibility resolver (pure `BleWidgetCore`
logic, matching the repo's established test pattern). No other test tasks are generated.

**Organization**: Tasks are grouped by user story (priority P1→P4) so each story is independently
implementable and testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on another incomplete task)
- **[Story]**: Which user story the task serves (US1–US4)
- Every task includes an exact repo-relative file path

## Path Conventions

This feature spans **two repositories**:

- **App repo** = the history-preserving split output, a working tree `keybeacon/` whose
  `origin` is `github.com/ykiewang/keybeacon`. App-repo paths below are written as
  `keybeacon/…` (map to that repo's root).
- **Firmware repo** = **this** repo (`github.com/ykiewang/zmk-config-totem`); its paths are
  written repo-root-relative (e.g. `protocol-pinned/…`, `.github/workflows/build.yml`).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Capture the no-regression baseline and perform the history-preserving split that seeds
the app repo (research R1, R2).

- [ ] T001 Capture the pre-split baseline in the firmware repo: run `swift build` + `swift test` in
      `host/macos/` and confirm firmware builds all `build.yaml` targets (`totem_left`,
      `totem_right`, `settings_reset`); record pass/output as the no-regression reference for
      FR-016 / SC-008.
- [ ] T002 [P] Author the migration script `scripts/migrate/split-app-repo.sh` (+
      `scripts/migrate/README.md`) that history-preservingly maps `host/macos/` → `app/macos/`,
      `specs/003-standalone-app-and-protocol/protocol/` → `protocol/`, and seeds `conformance/` from
      `tools/probe.py`, using `git subtree split` (fallback `git filter-repo`); supports
      `--dry-run` to print planned splits and the target tree without writing (research R2).
- [ ] T003 Execute `scripts/migrate/split-app-repo.sh` to produce the local `keybeacon/` working
      tree (preserved commits on `app/macos/` and `conformance/`), `git init` it, set
      `origin=https://github.com/ykiewang/keybeacon.git`; do **not** push (push is the documented
      manual maintainer step, T031). Verify `git -C keybeacon log --oneline -- app/macos` shows
      original history (quickstart D).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Prove the moved app is intact and give the app repo the minimal scaffolding every story
builds on. **No user story may begin until this phase passes.**

**⚠️ CRITICAL**: The no-regression gate (T004) blocks US1/US3/US4 (they touch app code); the repo
scaffolding (T005/T006) blocks all stories.

- [ ] T004 No-regression gate: in `keybeacon/app/macos/` run `swift build` + `swift test` and confirm
      the existing `BleWidgetTests` pass unchanged after the move (fix only path/package metadata in
      `keybeacon/app/macos/Package.swift`, never logic) — the move MUST NOT change behavior
      (FR-016, SC-008).
- [ ] T005 [P] Scaffold app-repo meta: `keybeacon/.gitignore` (Swift `.build/`, bundle outputs),
      `keybeacon/LICENSE` (MIT, matching the protocol license), and a `keybeacon/README.md`
      placeholder header (expanded in T011).
- [ ] T006 [P] Create the app-repo CI skeleton `keybeacon/.github/workflows/ci.yml`: on push/PR, run
      `swift build` + `swift test` in `app/macos/` (bundle smoke + protocol lint added later by
      T012/T016).

**Checkpoint**: The app repo exists with preserved history, builds, and tests green — stories can begin.

---

## Phase 3: User Story 1 - Non-technical user downloads a ready-to-run app (Priority: P1) 🎯 MVP

**Goal**: Produce a double-clickable macOS app artifact on the app repo's Releases page that a
non-technical user can download, launch, grant Bluetooth, and see keyboard status — **unsigned this
iteration**, with the Gatekeeper first-open gap documented (research R5, R8; contract
`release-artifact.md`).

**Independent Test**: On a Mac, download the produced `.dmg`/`.zip`, open `BleWidget.app` (right-click
→ Open once, since unsigned), grant Bluetooth, and confirm live status shows; release notes declare
version, supported KBP, and min macOS (quickstart G).

- [ ] T007 [US1] Create `keybeacon/packaging/make-app.sh`: `swift build -c release`, assemble
      `BleWidget.app` (`Contents/MacOS/BleWidget`, `Contents/Info.plist`, `Contents/PkgInfo`
      `APPL????`), then emit `BleWidget-<ver>.zip` (`ditto -c -k --keepParent`), `BleWidget-<ver>.dmg`
      (`hdiutil create`), and `*.sha256`; runnable with only `swift` + stock macOS tools (FR-001;
      contract `release-artifact.md` §1).
- [ ] T008 [P] [US1] Update `keybeacon/app/macos/Info.plist`: add `KBPSupportedVersions` (the
      supported service-UUID/MAJOR set, `AA440AA0-…` for KBP 1.x) and confirm `LSUIElement=true`,
      `LSMinimumSystemVersion=12.0`, `NSBluetoothAlwaysUsageDescription` (FR-003; contract
      `release-artifact.md` §4).
- [ ] T009 [US1] Create `keybeacon/.github/workflows/release.yml`: trigger on tag `app-v*`; job order
      `swift build` → `swift test` → `packaging/make-app.sh` → sha256 → create GitHub Release +
      upload `.dmg`/`.zip`/`.sha256` + notes; signing/notarization steps **conditional on
      ZMK-Studio-aligned Developer ID secrets** (`APPLE_CERTIFICATE`, `APPLE_CERTIFICATE_PASSWORD`,
      `APPLE_SIGNING_IDENTITY`, `APPLE_ID`, `APPLE_PASSWORD`, `APPLE_TEAM_ID`; skipped now ⇒
      `signing_state=unsigned`), and **fail-safe** (a signing/notarize failure fails the job, never
      publishes) (FR-001/FR-002; R8; contract `release-artifact.md` §2–3).
- [ ] T010 [US1] Add a minimum-macOS runtime guard in
      `keybeacon/app/macos/Sources/BleWidget/main.swift` (or `AppDelegate.swift`): on < macOS 12 show
      a clear message and exit cleanly rather than crash ("older/newer macOS" edge case).
- [ ] T011 [US1] Write `keybeacon/README.md` download/run guide: find → download → open → grant
      Bluetooth with **no terminal/build** (FR-004); the unsigned **Gatekeeper first-open workaround**
      (right-click → Open; or clear quarantine), a platform note stating macOS is available now and
      **Windows/Linux are planned for the next iteration (feature 004)**, and an explicit
      statement that **SC-001/SC-002 are not met this iteration** (unsigned) and a future signed
      release removes the step (R8; contract `release-artifact.md` §5).
- [ ] T012 [US1] Extend `keybeacon/.github/workflows/ci.yml` with a **bundle smoke** step: run
      `packaging/make-app.sh` in CI and assert `BleWidget.app` + `.dmg` + `.zip` are produced (guards
      FR-001 on every push).

**Checkpoint**: A tag `app-v…` yields a downloadable (unsigned) artifact; the app launches and shows
status. MVP complete and demoable (with the documented first-open step).

---

## Phase 4: User Story 2 - Standalone app repo owns the versioned protocol standard (Priority: P2)

**Goal**: The protocol is a self-contained, independently-versioned `protocol/` module in the app
repo; the app repo builds/releases with **no firmware repo present**; and the firmware **pins** a
published KBP version via a vendored snapshot + lock with a CI equality check (research R3, R4;
contracts `protocol-standard.md`, `firmware-pin.md`).

**Independent Test**: Clone **only** the app repo → it builds and `make-app.sh` runs; `protocol/` has
`README.md`+`VERSION`+`CHANGELOG.md`, is self-contained (no firmware/app-internal links); and
`scripts/verify-protocol-pin.sh` in the firmware repo exits 0, failing if a byte diverges (quickstart
A, B, C).

- [ ] T013 [P] [US2] Create `keybeacon/protocol/VERSION` = `1.0.0` (matches tag `protocol-v1.0.0`;
      contract `protocol-standard.md` §2).
- [ ] T014 [P] [US2] Create `keybeacon/protocol/CHANGELOG.md` with a `1.0.0` entry consolidating the
      feature-001 snapshot contract + feature-002 discovery/identity amendment (KBP §13).
- [ ] T015 [US2] Self-containment pass on `keybeacon/protocol/README.md`: remove/convert any
      firmware-internal or app-source links and confirm it fully specifies service identity, payload
      layout, GAP-name identity, discovery, and versioning so a third party can implement from it
      alone (FR-006/FR-007; contract `protocol-standard.md` §1).
- [ ] T016 [P] [US2] Create `keybeacon/.github/workflows/protocol.yml`: assert `protocol/VERSION` is
      valid semver and matches the `protocol-v*` tag on release, `CHANGELOG.md` has an entry for
      `VERSION`, and a self-containment lint fails on any `../ | host/ | config/ | firmware` link in
      `protocol/README.md` (contract `protocol-standard.md` §6).
- [ ] T017 [US2] Add an explicit **standalone-build** assertion to `keybeacon/.github/workflows/ci.yml`
      (or `protocol.yml`): the app-repo job uses only the app checkout (no firmware repo) and must
      succeed — documents/guards SC-003 / FR-005.
- [ ] T018 [P] [US2] Create the firmware pin snapshot `protocol-pinned/KBP.md`: a byte-for-byte copy
      of `keybeacon/protocol/README.md` at the pinned tag (contract `firmware-pin.md` §1).
- [ ] T019 [US2] Create `protocol-pinned/kbp.lock` with `kbp_version: 1.0.0`,
      `source_repo: https://github.com/ykiewang/keybeacon`, `source_ref: protocol-v1.0.0`,
      `source_commit: <sha>`, `snapshot_sha256: <sha256 of protocol-pinned/KBP.md>` (contract
      `firmware-pin.md` §2).
- [ ] T020 [US2] Create `scripts/verify-protocol-pin.sh`: **offline** recompute `sha256(KBP.md)` ==
      `kbp.lock:snapshot_sha256` and `kbp_version` match; **online (when reachable)** fetch
      `protocol/README.md@source_ref` and diff vs `KBP.md`, soft-skip when offline; exit `0`/`1`/`2`
      (verified / mismatch / malformed lock) (contract `firmware-pin.md` §3; FR-008, SC-003, SC-006).
- [ ] T021 [US2] Add a non-firmware **protocol-pin verify** job to `.github/workflows/build.yml` that
      runs `scripts/verify-protocol-pin.sh` and fails CI on mismatch (FR-008, SC-006).
- [ ] T022 [US2] Record the protocol release action: tag `protocol-v1.0.0` in the app repo (executed
      with the push, T031) and note it in `keybeacon/protocol/CHANGELOG.md` — the pinnable,
      traceable ref (contract `protocol-standard.md` §2; SC-006).

**Checkpoint**: App repo stands alone with a governed, versioned protocol; firmware provably pins
`protocol-v1.0.0` and CI guards divergence.

---

## Phase 5: User Story 3 - A keyboard author can make a keyboard conform and prove it (Priority: P3)

**Goal**: Ship the Conformance Kit — a guide + checklist + self-test tool (evolved from the probe) —
so an author can enumerate the required work and get per-item PASS/FAIL against their keyboard
(research R6; contract `protocol-standard.md` §4).

**Independent Test**: Run the tool against the reference Totem → all items PASS, exit 0; against a
seeded-defect keyboard → the specific item FAILs, exit 1; with Bluetooth off/no keyboard → clear
environment error, exit 2 (quickstart E, F).

- [ ] T023 [US3] Create `keybeacon/conformance/conformance_tool.py` by evolving `tools/probe.py`:
      discover candidates by **service UUID only** (never name/model); run each checklist item and
      print **per-item PASS/FAIL** naming the specific nonconformance; exit `0` all-pass / `1`
      conformance-failure / `2` environment-error (BT off, no keyboard, connect timeout); print the
      discovered GAP name for confirmation (FR-011/FR-012, SC-004/SC-005; contract
      `protocol-standard.md` §4).
- [ ] T024 [P] [US3] Write `keybeacon/conformance/CONFORMANCE.md`: the complete, concrete body of
      work a keyboard must do — the **central BLE role prerequisite**, expose service+characteristic,
      payload ≥ 2 bytes per §4, notify-on-change suppression, GAP name — plus tool usage and exit-code
      meanings (FR-009).
- [ ] T025 [P] [US3] Write `keybeacon/conformance/checklist.md`: each KBP §10 item as an
      individually verifiable line, cross-referenced to the tool's checks (FR-010).

**Checkpoint**: An author can read the guide, check the list, and self-verify a keyboard; the
reference Totem passes.

---

## Phase 6: User Story 4 - App and keyboards stay compatible across protocol versions (Priority: P4)

**Goal**: The app declares its supported KBP MAJOR(s) and, on connect, works with compatible versions
and shows a clear "unsupported protocol version" message for incompatible ones — no crash/wrong data
(research R7; contract `protocol-standard.md` §3).

**Independent Test**: Known service → works; a device exposing only an unknown KeyBeacon-family
service → clear "unsupported" message; a non-KeyBeacon device → "not a keyboard" (quickstart H).

- [ ] T026 [P] [US4] Add `keybeacon/app/macos/Tests/BleWidgetTests/CompatibilityTests.swift`
      (write first, ensure it FAILs): the pure resolver classifies a known supported service UUID as
      *supported*, an unknown KeyBeacon-family service as *unsupported*, and a non-KeyBeacon device as
      *not-a-keyboard* (FR-013/FR-014).
- [ ] T027 [US4] Implement the supported-KBP declaration + resolver in
      `keybeacon/app/macos/Sources/BleWidgetCore/` (e.g. a `KBPCompatibility` type exposing the
      supported service-UUID set and a `classify(discoveredServices:)`); keep it pure/unit-testable
      (FR-013; the unit under test in T026).
- [ ] T028 [US4] Wire the "unsupported protocol version" path in
      `keybeacon/app/macos/Sources/BleWidget/AppDelegate.swift`: on an unknown KeyBeacon-family
      service show a clear, actionable message (menu bar/panel) and do not connect/parse; known
      service behaves normally (FR-014, SC-007).

**Checkpoint**: Version-skew behavior is predictable and user-visible; current-version experience
unchanged.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Firmware-side cleanup to the reference-keyboard shape, the manual cross-repo push, and
end-to-end validation.

- [ ] T029 [P] Update firmware `readme.md`: point users to the app repo's **Releases** for downloads
      and note the app/protocol/conformance kit now live in `github.com/ykiewang/keybeacon`; keep
      firmware instructions scoped to the reference keyboard.
- [ ] T030 [P] Firmware cleanup after the split: remove the migrated app sources (`host/macos/`) from
      the firmware repo, **retain** `tools/probe.py` as the developer probe, and confirm `build.yaml`
      targets still build unchanged (plan Project Structure; FR-016).
- [ ] T031 Execute/document the manual cross-repo push (auth required): `git push -u origin main` to
      `github.com/ykiewang/keybeacon`, then push tags `protocol-v1.0.0` and the first `app-vX.Y.Z`;
      update `scripts/migrate/README.md` to mark the migration tooling retired after seeding
      (research R2; this is the one step not verifiable in this repo's CI).
- [ ] T032 Run `quickstart.md` scenarios A–I end to end and record outcomes; confirm no regression vs
      the T001 baseline (reference Totem still passes conformance and shows status as in 001/002)
      (FR-016, SC-008).
- [ ] T033 [P] Confirm the **deferred** items are stated honestly everywhere they surface: release
      notes template + `keybeacon/README.md` mark FR-002 / SC-001 / SC-002 as not-met-this-iteration
      (unsigned), with the signed-release follow-up noted (R8).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies. T001 (baseline) ∥ T002 (script authoring); T003 needs T002.
- **Foundational (Phase 2)**: after Setup. T004 needs the split (T003); T005/T006 need the
  `keybeacon/` tree (T003). **Blocks all user stories.**
- **US1 (Phase 3)**: after Foundational. The MVP.
- **US2 (Phase 4)**: after Foundational. Independent of US1 (shares the repo, not its tasks).
- **US3 (Phase 5)**: after Foundational. Independent of US1/US2.
- **US4 (Phase 6)**: after Foundational. Independent of US1–US3 (touches app code only).
- **Polish (Phase 7)**: after the stories it validates; T031 (push) should follow US1/US2 so the
  first app + protocol tags exist; T032 after all stories.

### User Story Dependencies

- All four stories depend only on **Foundational**; none depends on another story. US4 shares
  `AppDelegate.swift` with US1's T010 — sequence T010 before T028 if the same developer edits it.

### Within Each User Story

- US1: T007 → T009 (release uses make-app.sh); T008 ∥ T007; T010 ∥; T012 after T007; T011 ∥.
- US2: T013/T014 ∥; T015 before T016 (lint target); T018 → T019 → T020 → T021 (pin chain); T017 ∥;
  T022 governance.
- US3: T023 (tool) ∥ T024/T025 (docs); the three can proceed together.
- US4: T026 (failing test) → T027 (resolver) → T028 (UI message).

### Parallel Opportunities

- Setup: T001 ∥ T002.
- Foundational: T005 ∥ T006 (after T004 gate).
- US1: T007, T008, T010, T011 are different files — parallelizable; T009/T012 touch workflows.
- US2: T013, T014, T016, T018 ∥; the firmware-repo pin chain T018→T021 is sequential.
- US3: T023, T024, T025 ∥ (three different files).
- Polish: T029, T030, T033 ∥.
- With staffing: US1/US2/US3/US4 run in parallel once Foundational completes (US1 app-release track,
  US2 protocol+pin track, US3 conformance track, US4 app-logic track).

---

## Parallel Example: User Story 2 (firmware pin chain + parallel docs)

```bash
# Parallel (different files):
Task: "protocol/VERSION = 1.0.0 (keybeacon/protocol/VERSION)"
Task: "protocol/CHANGELOG.md 1.0.0 entry (keybeacon/protocol/CHANGELOG.md)"
Task: "protocol.yml governance CI (keybeacon/.github/workflows/protocol.yml)"
Task: "protocol-pinned/KBP.md snapshot (firmware repo)"

# Then the firmware pin chain (sequential, same subsystem):
#   protocol-pinned/kbp.lock → scripts/verify-protocol-pin.sh → build.yml verify job
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1 Setup (baseline + split) → Phase 2 Foundational (app builds, tests green) → Phase 3 US1.
2. **STOP and VALIDATE**: tag `app-v…`, confirm a downloadable (unsigned) `.app` launches and shows
   status with the documented first-open step. Demo the MVP. (SC-001/SC-002 remain explicitly
   deferred until signing is enabled.)

### Incremental Delivery

1. Setup + Foundational → app repo seeded and green.
2. US1 → downloadable release (MVP) → demo.
3. US2 → standalone-repo proof + governed protocol + firmware pin → demo (clone-only build; pin CI).
4. US3 → conformance kit → demo (self-test the reference keyboard + a seeded defect).
5. US4 → version-skew message → demo.
6. Polish → firmware cleanup, the manual push (T031), quickstart A–I, honest-gap statements.

### Parallel Team Strategy

- Dev A: US1 (release pipeline). Dev B: US2 (protocol governance + firmware pin). Dev C: US3
  (conformance kit). Dev D: US4 (compatibility resolver). All start after Foundational; integrate at
  Polish.

---

## Notes

- `[P]` = different files, no dependency on an incomplete task.
- `[Story]` maps each task to its user story; Setup/Foundational/Polish carry no story label.
- **Cross-repo**: `keybeacon/…` = app repo (origin `github.com/ykiewang/keybeacon`); bare paths =
  this firmware repo. T031's push is the only step not verifiable inside this repo's CI.
- **Honest gap**: the first release is **unsigned** → FR-002 / SC-001 / SC-002 are deferred and must
  be labeled as such (T011, T033).
- No firmware runtime/wire change; the reference Totem stays conforming with no regression (T030,
  T032; FR-016, SC-008).
- Commit after each task or logical group; stop at any checkpoint to validate a story independently.
