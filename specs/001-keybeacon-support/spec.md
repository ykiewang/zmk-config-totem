# Feature Specification: Totem KeyBeacon Support

**Feature Branch**: `001-keybeacon-support`

**Created**: 2026-10-11

**Status**: Draft

**Input**: User description: "根据这个说明文档 https://github.com/ykiewang/zmk-keybeacon/blob/main/GETTING-STARTED.md#zh-gs，帮我适配 Totem 仓库，使其支持 zmk-keybeacon，从 main 分支拉取最新分支来进行这个支持"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See the active layer and modifiers on the Mac (Priority: P1)

As a Totem keyboard owner, after building and flashing firmware from this configuration repository, I want the left (central) half to broadcast its current layer and modifier state over its host BLE connection, so that a companion macOS app (or a quick probe) can show me which layer I'm on and which modifiers are held.

**Why this priority**: This is the entire purpose of the request. Without the central half reporting its state, nothing else about the feature has value. It is the minimum viable outcome.

**Independent Test**: Build the left firmware from this repo, flash it to the central half, connect the keyboard to a Mac, and observe that the companion app/probe reports the active layer and modifier state. Changing layers on the keyboard updates the reported state.

**Acceptance Scenarios**:

1. **Given** a Totem flashed with firmware built from this repo, **When** the keyboard is connected to a Mac and the user switches from the BASE layer to the NAVI layer, **Then** the companion reports the new active layer shortly after the change.
2. **Given** the keyboard is connected, **When** the user holds a modifier (e.g., Shift), **Then** the companion reports the modifier as active, and reports it inactive when released.
3. **Given** the keyboard is idle with no state change, **When** no keys are pressed, **Then** the companion does not receive a continuous stream of redundant updates.

---

### User Story 2 - Firmware still builds cleanly in CI (Priority: P2)

As the repository maintainer, I want the existing GitHub Actions build to continue succeeding after the integration, producing the left (central), right (peripheral), and settings_reset firmware artifacts, so that I can download and flash firmware the same way as before.

**Why this priority**: The integration must not break the existing automated build pipeline the owner relies on to obtain firmware. A feature that only works locally but breaks CI is not acceptable.

**Independent Test**: Push the changes to a fork and let GitHub Actions run; confirm the workflow completes successfully and the firmware archive contains all three expected artifacts.

**Acceptance Scenarios**:

1. **Given** the integration changes are committed, **When** the GitHub Actions workflow runs, **Then** it completes successfully and produces firmware artifacts for the left, right, and settings_reset targets.
2. **Given** a successful build, **When** the maintainer inspects the build, **Then** the KeyBeacon capability is compiled into the central (left) target only.

---

### User Story 3 - KeyBeacon is correctly scoped to the central half only (Priority: P3)

As the maintainer, I want the KeyBeacon capability to be active only on the central (left) half and silently excluded from the peripheral (right) and settings_reset targets, so that the peripheral and reset firmware remain unaffected and correct.

**Why this priority**: Correct scoping prevents wasted resources and incorrect behavior on targets that have no host BLE link. It refines quality but the feature can be demonstrated (P1) before this is formally verified.

**Independent Test**: Inspect the right and settings_reset builds and confirm the KeyBeacon reporting code is not present/active, while the left build includes it.

**Acceptance Scenarios**:

1. **Given** firmware built for the right (peripheral) half, **When** the build is inspected, **Then** KeyBeacon reporting is not active in it.
2. **Given** firmware built for the settings_reset target, **When** the build is inspected, **Then** KeyBeacon reporting is not active in it.

---

### Edge Cases

- **Peripheral/reset targets**: KeyBeacon must compile out silently on the right half and settings_reset target because they do not hold the central host-link role; the build must not fail for them.
- **Idle keyboard**: When the layer/modifier snapshot is unchanged, redundant notifications must be suppressed so the host is not flooded while the keyboard is idle.
- **Connected vs advertising**: Once the keyboard is connected to the Mac it stops advertising; the companion must discover it among already-connected peripherals rather than by scanning.
- **Tracking the latest module code**: Because the module is pulled from its `main` branch, an upstream change could in principle alter behavior or break a build between two otherwise-identical local builds; a rebuild always fetches the newest module code.
- **Layer labels**: Layers without a human-readable label fall back to a generic index name. (Totem's keymap already labels its layers, so names should display correctly.)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The configuration repository MUST declare the zmk-keybeacon module as a dependency so the build system fetches it automatically during dependency resolution.
- **FR-002**: The repository MUST pin the zmk-keybeacon module to a released tag (currently the latest, `v1.1.3`) for reproducible builds, rather than tracking a moving branch.
- **FR-003**: The existing ZMK dependency and all current build targets (left, right, settings_reset) MUST remain intact and unaffected by the addition.
- **FR-004**: The KeyBeacon capability MUST be enabled for the central (left) target so that the central half reports its layer and modifier state over the host BLE connection.
- **FR-005**: The KeyBeacon capability MUST NOT be active on the peripheral (right) target or the settings_reset target, and their builds MUST continue to succeed.
- **FR-006**: The central half MUST report the active layer name, active layer index, and modifier state, and MUST reflect changes to these values on the host side.
- **FR-007**: The system MUST suppress redundant reports when the reported state is unchanged, avoiding a continuous stream of updates while idle.
- **FR-008**: The integration MUST NOT require editing the module's own source, nor adding include/source directives to the shield's build or Kconfig files.
- **FR-009**: The existing automated build workflow MUST continue to produce firmware artifacts for all three targets without changes to how the owner retrieves and flashes them.
- **FR-010**: Human-readable layer names MUST be available to the companion for Totem's existing layers (BASE, NAVI, SYM, ADJ) rather than only generic index labels.
- **FR-011**: Upgrading or refreshing the module MUST be achievable by re-running dependency resolution and rebuilding, without further file edits (since the revision tracks `main`).

### Key Entities *(include if feature involves data)*

- **Layer/Modifier Snapshot**: The reported keyboard state consisting of the active layer name, the active layer index, and the current modifier state. Broadcast from the central half to the connected host; changes drive updates, unchanged snapshots are suppressed.
- **Module Dependency Entry**: The repository's declaration of where the zmk-keybeacon module comes from and which revision (`main`) to fetch.
- **Central Target Configuration**: The configuration that governs the central (left) half, where the KeyBeacon capability is switched on.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After flashing firmware built from this repo and connecting to a Mac, the companion displays the active layer and modifier state, and a layer/modifier change is reflected on the host within about 1 second.
- **SC-002**: A clean run of the existing automated build completes successfully and produces firmware for the left, right, and settings_reset targets.
- **SC-003**: The KeyBeacon reporting capability is present only in the central (left) build and absent from the peripheral (right) and settings_reset builds.
- **SC-004**: Enabling the feature required changes to at most two configuration files, with zero edits to module source or to the shield's build/Kconfig files.
- **SC-005**: The companion shows Totem's layer names as the human-readable labels BASE, NAVI, SYM, and ADJ rather than generic index names such as L0/L1.

## Assumptions

- **"Latest version" interpretation**: The instruction to use the latest is taken to mean pinning the newest released tag (`v1.1.3`) of the zmk-keybeacon module. This favors reproducible builds (the upstream-recommended approach) over tracking a moving branch. The pin is trivially updatable later by changing one `revision:` line.
- **Scope boundary**: Scope is limited to the firmware configuration repository changes and a successful build. Building, installing, or distributing the macOS companion app/probe is out of scope and is used only to verify the outcome.
- **Roles**: The left half is the central (host-link) role and is the KeyBeacon target; the right half is the peripheral. This matches the repo's current configuration.
- **BLE availability**: The target board provides host BLE support automatically, satisfying KeyBeacon's BLE prerequisite without additional configuration.
- **No keymap changes needed**: Totem's keymap already defines human-readable layer labels, so no keymap edits are required for correct layer-name display.
- **Flashing workflow unchanged**: The owner continues to flash via the existing drag-and-drop UF2 process using artifacts from the automated build.
- **Verification tooling**: Verification may use either the downloadable companion app or a simple BLE probe; either is acceptable to confirm the outcome.
