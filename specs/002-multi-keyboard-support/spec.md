# Feature Specification: Multi-Keyboard Support (Decouple App & Firmware from Totem)

**Feature Branch**: `002-multi-keyboard-support`

**Created**: 2026-10-05

**Status**: Draft

**Input**: User description: "功能跟键盘解耦:我的 APP 不只支持 Totem 键盘,还能支持别的键盘。键盘上的开发适配:固件不只支持 Totem,也能支持别的键盘,并且能够轻易地改动。按照这种需求,评估如何规范化开发,并基于当前项目进行重构。"

## Clarifications

### Session 2026-10-05

- Q: App 如何处理"支持多把键盘"? → A: 单活动键盘 + 记忆所选(一个悬浮窗;多把时菜单栏选一把并记住)
- Q: 固件"轻易适配到别的键盘"的目标形态? → A: 仓库内可复用套件 + 移植指南(保持 shield 作用域,符合 R1/原则III)
- Q: App 如何识别并命名一把"状态悬浮窗键盘"? → A: 仅凭自定义服务 UUID 识别(无主机侧注册表/白名单);键盘自报人类可读名字,App 据此显示,缺省时优雅回退

### Session 2026-10-05 (reconciliation with feature 003)

- 契约之家:feature 002 只负责代码级解耦,并**就地**沿用现有仓内契约
  (`specs/001-ble-status-widget/contracts/status-snapshot.md`)作为工作参考(可向其
  新增键盘名字段)。把该契约**提升并迁移**为独立版本化的共享 `protocol/` 标准(托管于
  独立 App 仓)是 feature 003 的职责,不在 002 范围内。

## User Scenarios & Testing *(mandatory)*

### User Story 1 - App works with any contract-compliant keyboard, not just Totem (Priority: P1)

A user owns a ZMK keyboard that is **not** a Totem but runs the status feature. They
launch the desktop app and it connects and shows the live layer/modifier readout —
without anyone editing the app, and without the app looking for the name "Totem".
Any keyboard that implements the status interface contract is supported.

**Why this priority**: This is the core of the request ("功能跟键盘解耦"). Removing the
hardcoded model assumption is what turns a Totem-only utility into a general one; with
it, the app delivers value on any compatible keyboard.

**Independent Test**: Take a compatible keyboard whose reported name is not "Totem"
(or rename the keyboard), run the app with no code changes, and confirm it discovers,
connects, and displays correct live status.

**Acceptance Scenarios**:

1. **Given** a non-Totem keyboard exposing the status service is connected, **When**
   the app launches, **Then** it connects and shows that keyboard's live layer and
   modifier state with no app code or config changes.
2. **Given** the app previously only matched "Totem", **When** it is pointed at a
   keyboard with a different name, **Then** it still connects purely on the basis of
   the status service contract.
3. **Given** a device that does **not** expose the status service, **When** the app
   scans connected peripherals, **Then** it does not treat that device as a keyboard.

---

### User Story 2 - The keyboard tells the app its own name (Priority: P2)

The app shows a human-readable keyboard name that comes **from the keyboard itself**,
so there is no host-side list of models to maintain and no per-keyboard setup. If a
keyboard reports no usable name, the app shows a sensible generic label instead of
failing.

**Why this priority**: Self-describing identity is what makes "pure service-UUID
discovery" usable in the UI and in a multi-keyboard chooser; it keeps the host fully
decoupled from any specific model. It builds on US1 but is not required for a single
keyboard to work.

**Independent Test**: Connect two compatible keyboards configured with different
names; confirm each appears under its own correct name, and a keyboard with a blank
name shows the generic fallback — all without editing the app.

**Acceptance Scenarios**:

1. **Given** a compatible keyboard with a configured name, **When** the app connects,
   **Then** the displayed name matches the name set on the keyboard.
2. **Given** a compatible keyboard that reports no name, **When** the app connects,
   **Then** the app shows a generic fallback label and still displays live status.
3. **Given** the keyboard's name is static, **When** status changes stream during
   normal typing, **Then** the name is not re-fetched on every change (no added
   per-change traffic).

---

### User Story 3 - Add the firmware feature to another keyboard with minimal, documented changes (Priority: P3)

A firmware maintainer wants to enable the status feature on a different ZMK keyboard.
They copy a self-contained firmware "kit" into that keyboard's shield, make a small,
documented set of per-keyboard changes (such as enabling one configuration symbol),
and build — **without editing the shared, generic logic**. A porting guide in the repo
spells out the exact steps, prerequisites, and known constraints.

**Why this priority**: This is the second half of the request ("键盘上的开发适配…能够
轻易地改动"). It standardizes how the feature is added to new keyboards and is the
deliverable that makes firmware support reproducible rather than a one-off.

**Independent Test**: Following only the porting guide, add the feature to a second
shield in a scratch build; confirm it builds for that keyboard's central role, emits
the status snapshot, and that the shared logic file was not modified.

**Acceptance Scenarios**:

1. **Given** the portable kit and the porting guide, **When** a maintainer adds the
   feature to a new keyboard, **Then** the only edits needed are the documented
   per-keyboard changes, not the shared logic.
2. **Given** the feature is added to a new keyboard, **When** it is built, **Then** it
   compiles only for the central role and is absent from peripheral and reset builds.
3. **Given** a keyboard that lacks a central BLE role, **When** a maintainer consults
   the guide, **Then** the prerequisite is clearly stated so they know it is
   unsupported before attempting the port.

---

### User Story 4 - Choose and remember the active keyboard when several are present (Priority: P4)

When more than one compatible keyboard is available, the user picks which one the
panel tracks from the menu bar. The app remembers that choice and reconnects to the
same keyboard on the next launch. A single panel shows the selected keyboard.

**Why this priority**: Robustness/UX for multi-device users. It refines an already
working single-keyboard readout, so it comes after the core decoupling.

**Independent Test**: Connect two compatible keyboards, select one, restart the app,
and confirm it reconnects to the remembered one and shows its status in a single
panel.

**Acceptance Scenarios**:

1. **Given** exactly one compatible keyboard is present, **When** the app launches,
   **Then** it connects automatically with no user action.
2. **Given** two or more compatible keyboards are present and none is remembered,
   **When** the app launches, **Then** it offers a menu-bar chooser and connects once
   the user selects one.
3. **Given** a keyboard was previously selected, **When** the app relaunches and that
   keyboard is available, **Then** it reconnects to the same one automatically.
4. **Given** a keyboard was previously selected but is now absent, **When** the app
   launches, **Then** it shows not-connected, keeps retrying, and lets the user pick
   another.

---

### Edge Cases

- **Multiple keyboards, no prior choice**: the app must not silently guess a single
  keyboard as "the" one; it surfaces a chooser and connects only after selection.
- **Remembered keyboard absent**: show not-connected, keep retrying, allow switching.
- **Blank / missing keyboard name**: display a generic fallback; never block the
  connection or crash.
- **Unusual name (very long, non-ASCII, emoji)**: display safely (e.g., truncated),
  no layout break or crash.
- **Two keyboards with identical names**: disambiguate by a stable per-device
  identifier so the user can tell them apart and the remembered choice is exact.
- **Contract version mismatch** (a keyboard adds reserved fields later): the app still
  parses the core snapshot and degrades gracefully rather than rejecting the device.
- **Existing Totem users after refactor**: previously saved panel position and lock
  state are preserved (no reset) even though internal naming is de-branded.
- **Porting to a non-split or peripheral-only keyboard**: the guide states the
  central-BLE-role prerequisite up front.

## Requirements *(mandatory)*

### Functional Requirements

**Host decoupling (US1)**

- **FR-001**: The app MUST identify a compatible keyboard solely by the status
  interface contract (its custom service identity), and MUST NOT match on any
  hardcoded keyboard name or model.
- **FR-002**: The app MUST connect to and display status from any keyboard that
  exposes the status service, regardless of make, model, or name.
- **FR-003**: A device that does not expose the status service MUST NOT be treated as
  a compatible keyboard.
- **FR-004**: The app's persisted settings and user-visible identity MUST NOT be tied
  to a specific keyboard model (no model-specific branding baked into stored data or
  the app name); migration MUST preserve existing users' saved panel position and lock
  state.

**Self-describing keyboard identity (US2)**

- **FR-005**: The keyboard MUST convey a human-readable name to the host as part of
  the documented interface contract, such that the host needs no per-keyboard
  configuration and no host-maintained list of models.
- **FR-006**: The app MUST display the keyboard's self-reported name, and MUST fall
  back to a generic label (without failing to connect) when no usable name is
  provided.
- **FR-007**: Conveying the keyboard name MUST NOT add recurring traffic to the
  high-frequency status stream (the name is static and is obtained at most once per
  connection, not on every state change).

**Firmware portability & standardized development (US3)**

- **FR-008**: The firmware status feature MUST be organized as a self-contained,
  reusable kit whose shared logic is keyboard-independent (no per-keyboard values
  baked into the shared logic).
- **FR-009**: Adding the feature to a different ZMK keyboard MUST be achievable by
  copying the kit and making a documented, minimal set of per-keyboard changes (e.g.,
  enabling one configuration symbol), without editing the shared logic.
- **FR-010**: The feature MUST remain gated so that it compiles only for the
  keyboard's central role and only when explicitly enabled; peripheral and reset
  builds MUST NOT include it.
- **FR-011**: The repository MUST include a porting guide documenting the exact steps,
  prerequisites (central BLE role), and known constraints (including the ZMK
  app-private-header access limitation that keeps the feature shield-scoped) for
  adding the feature to a new keyboard.
- **FR-012**: Developer verification tooling (the on-device probe) MUST also identify
  keyboards by the service contract rather than a hardcoded name, so it works across
  keyboards.

**Multi-keyboard selection (US4)**

- **FR-013**: When exactly one compatible keyboard is present, the app MUST connect to
  it automatically with no user action.
- **FR-014**: When more than one compatible keyboard is present and none is
  remembered, the app MUST let the user choose which one to display from the menu bar
  before committing to a connection.
- **FR-015**: The app MUST remember the user's selected keyboard (by a stable
  identifier) and reconnect to the same one automatically on the next launch when it
  is available.
- **FR-016**: The app MUST show a single status panel for the currently selected
  keyboard at any time.

**Backward compatibility & contract governance**

- **FR-017**: After the refactor, the existing Totem build and app behavior MUST be
  preserved with no regression: same snapshot semantics and same central-only gating.
- **FR-018**: Any change to the interface contract made to satisfy these requirements
  (e.g., adding the keyboard-name field) MUST be recorded in the versioned contract
  document and applied to firmware and host in a coordinated, versioned way. During
  feature 002 the working contract remains the in-repo
  `specs/001-ble-status-widget/contracts/status-snapshot.md`; its authoritative
  long-term home is defined by feature 003 (the standalone App repo's `protocol/`
  standard), not relocated by this feature.

### Key Entities *(include if feature involves data)*

- **Compatible Keyboard**: Any BLE keyboard exposing the status interface contract.
  Attributes: a stable per-device identifier, a self-reported human-readable name
  (optional), and a live connection state. Recognized by the contract alone.
- **Keyboard Identity / Name**: The human-readable name the keyboard reports about
  itself; may be absent, prompting a generic fallback. Not sourced from any host-side
  list.
- **Selected Keyboard**: The single keyboard the user has chosen to display; persisted
  by stable identifier across launches.
- **Firmware Status Kit**: The self-contained, portable firmware component — the
  keyboard-independent shared logic plus the small per-keyboard enablement — together
  with the porting guide. The unit that makes firmware support reproducible.
- **Interface Contract**: The frozen coupling point between firmware and host (status
  service + payload, plus the keyboard-name identity). The single thing both sides
  share; versioned. Its authoritative home and standardization are defined by feature
  003 (a self-contained `protocol/` module in the standalone App repo); feature 002
  consumes it in place without relocating it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The app connects to and correctly displays live status for at least two
  keyboards with distinct identities, one of which is not named "Totem", with zero
  changes to the app's code or configuration.
- **SC-002**: Setting up the app for a brand-new compatible keyboard requires zero
  host-side configuration — no file edits and no list/registry entry; the user only
  launches the app.
- **SC-003**: A maintainer can add the firmware feature to a second keyboard by
  following the porting guide in no more than 10 documented steps and without editing
  the shared logic file; the result builds successfully for that keyboard's central
  role.
- **SC-004**: After the refactor, the existing Totem firmware still produces all of
  its declared build targets and 100% of feature 001's acceptance scenarios still
  pass (no regression).
- **SC-005**: With two compatible keyboards connected, the user can select either one
  and see the correct keyboard's status; the selection survives an app restart in
  100% of trials.
- **SC-006**: The displayed keyboard name matches the name configured on the keyboard
  for 100% of tested keyboards, with a graceful generic fallback shown whenever no
  name is configured.
- **SC-007**: Conveying the keyboard name adds zero redundant updates during a 1-hour
  idle session (the no-idle-traffic guarantee from feature 001 is preserved).

## Assumptions

- **Host platform**: The desktop app remains macOS-only for this iteration;
  Windows/Linux support is explicitly out of scope.
- **Target keyboards**: "Other keyboards" means other ZMK-based keyboards that adopt
  the firmware kit and the interface contract and can expose a custom GATT service
  from a central BLE role. Non-ZMK or closed-source keyboards are out of scope.
- **Shield-scoped firmware**: The feature stays shield-scoped (not a standalone
  distributable module), per research R1 — ZMK's `app`-private headers are not
  reachable from standalone modules. A true west-module distribution is out of scope.
- **Payload unchanged**: The status payload layout (layer index, modifier bitmask,
  layer name) is unchanged. The only anticipated contract change is adding the
  keyboard-name identity; the concrete transport (reuse of the standard device name
  vs. a dedicated read-once contract field) is a planning-phase decision, deferred to
  `/speckit-plan`.
- **Contract home & split with feature 003**: Feature 002 does not relocate the
  interface contract. It uses the existing in-repo contract
  (`specs/001-ble-status-widget/contracts/status-snapshot.md`) as the working reference
  and may add the keyboard-name field to it. Elevating that contract into the shared,
  self-contained, independently-versioned `protocol/` standard hosted in the standalone
  App repo (which firmware then pins by version) is feature 003's scope.
- **Discovery mechanism**: Discovery continues to use connected-peripheral enumeration
  (a connected BLE HID keyboard stops advertising, per research R6); multi-keyboard
  support operates over that same mechanism.
- **Single active keyboard**: One panel tracks one selected keyboard at a time;
  simultaneous multiple panels for multiple keyboards are out of scope.
- **No host registry/whitelist**: The app keeps no curated list of keyboard
  models/metadata/icons; identity and name come from the keyboard and the contract.
- **Explicit non-goals (unchanged from feature 001 and reaffirmed here)**: battery
  level, output/BLE-profile status, typing speed, HID lock-key indicators, animated
  mascots, launch-at-login, per-keyboard themes, and any user-configurable layout or
  settings screen.
