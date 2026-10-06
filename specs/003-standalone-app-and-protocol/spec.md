# Feature Specification: Standalone App Repo, Shared Protocol Standard & Downloadable Release

**Feature Branch**: `003-standalone-app-and-protocol`

**Created**: 2026-10-05

**Status**: Draft

**Input**: User description: "APP 的仓库要是一个单独的,它和键盘之间的交互通过一些共用的标准来说明和约束,也希望能提供给用户预先编译好的 App,让用户可以直接下载运行。另外,我们要先设计好用户的键盘支持该协议的话,需要完成什么样的工作?"

## Clarifications

### Session 2026-10-05

- Q: "共用标准/协议"应该住在哪里? → A: 放在 App 仓内(App 仓是协议唯一真相源;键盘按 App 的标准配置/支持)。实现上保持自包含、独立版本化,降低"标准绑死单一实现"的耦合。
- Q: 预编译 App 的分发与信任方式? → A: 签名 + 公证(Apple Developer ID + CI 签名密钥),双击即运行、无 Gatekeeper 阻拦。
- Q: "键盘支持该协议要完成什么工作"的交付严格度? → A: 移植指南 + 一致性清单 + 由探针演进的自测/一致性工具(键盘作者自助验证达标)。

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A non-technical user downloads a ready-to-run, trusted app (Priority: P1)

A user who does not build software goes to the project's releases page, downloads the
prebuilt app, and launches it by double-clicking. On a clean machine it opens without
security warnings and, once they grant Bluetooth permission, shows the live status of
their compatible keyboard. No source checkout, no build tools, no terminal.

**Why this priority**: "让用户可以直接下载运行" is the headline user-facing deliverable.
A downloadable, trusted binary is what turns a developer project into something an
ordinary user can actually use; without it the product is inaccessible to most people.

**Independent Test**: On a clean, supported Mac that has never seen the app, download
the published artifact, double-click it, and confirm it opens with no Gatekeeper block
and displays the status panel when a compatible keyboard is connected.

**Acceptance Scenarios**:

1. **Given** the releases page, **When** a non-technical user downloads the published
   app, **Then** they can launch it by double-click with no build step and no terminal.
2. **Given** a clean supported Mac, **When** the downloaded app is opened for the first
   time, **Then** it is not blocked as untrusted and starts normally.
3. **Given** the app is running and Bluetooth permission is granted, **When** a
   compatible keyboard is connected, **Then** the app shows its live status.

---

### User Story 2 - The app is a standalone repo that owns the versioned protocol standard (Priority: P2)

The app lives in its own repository, independent of any keyboard's firmware. That repo
contains the authoritative, versioned **protocol standard** that defines and constrains
how a keyboard and the app talk to each other. Anyone — including this firmware project
and any third party — can implement a keyboard against the protocol by reading the app
repo alone, without access to any firmware source.

**Why this priority**: "APP 的仓库要是一个单独的" plus "通过一些共用的标准来说明和约束"
is the architectural backbone. A single, independently referenceable source of truth is
what lets the app and many keyboards evolve without being entangled.

**Independent Test**: Clone only the app repo; confirm it builds and produces a release
with no access to any firmware repo, and that the protocol standard is present,
versioned, and self-contained (no references to firmware-repo-internal files).

**Acceptance Scenarios**:

1. **Given** only the app repository, **When** a developer builds and releases the app,
   **Then** it succeeds without any firmware repository present.
2. **Given** the app repository, **When** a third party reads the protocol standard,
   **Then** it fully specifies the interface (identity, payload, keyboard name,
   discovery, versioning) with no external/internal dangling references.
3. **Given** the firmware project, **When** it implements the interface, **Then** it
   consumes a pinned version of the published standard rather than its own private copy.

---

### User Story 3 - A keyboard author can make their keyboard conform and prove it (Priority: P3)

A keyboard author wants their keyboard to work with the app. They follow a conformance
guide that states exactly what work their keyboard must do to "speak the protocol,"
check each required behavior against a conformance checklist, then run a self-test tool
that connects to their keyboard and reports pass/fail per item — so they can confirm
compliance before telling users to download the app.

**Why this priority**: This is the user's explicit question — "键盘支持该协议需要完成什
么样的工作". A guide + checklist + self-test turns "support other keyboards" from a vague
promise into a reproducible, self-verifiable process.

**Independent Test**: Point the self-test tool at a conforming keyboard and confirm all
checks pass; point it at a deliberately broken keyboard and confirm it reports the
specific failing requirement(s).

**Acceptance Scenarios**:

1. **Given** the conformance guide, **When** a keyboard author reads it, **Then** they
   can enumerate the complete, concrete body of work required to support the protocol.
2. **Given** a conforming keyboard, **When** the self-test tool runs against it, **Then**
   every checklist item reports pass.
3. **Given** a keyboard that exposes the service but violates one requirement, **When**
   the self-test tool runs, **Then** it reports that specific nonconformance rather than
   a generic failure.

---

### User Story 4 - App and keyboards stay compatible across protocol versions (Priority: P4)

The app declares which protocol version(s) it supports. When it connects to a keyboard,
it behaves predictably across version differences: it works with compatible versions and
shows a clear message for incompatible ones, so neither users nor keyboard authors are
surprised by silent breakage.

**Why this priority**: A standard that "约束" interaction must define what happens when
versions differ. It protects the ecosystem as the protocol evolves, but refines an
already-working current-version experience.

**Independent Test**: Connect keyboards implementing an older (compatible) and a
hypothetical incompatible protocol variant; confirm the app works in the first case and
shows a clear "unsupported protocol version" message (no crash/misread) in the second.

**Acceptance Scenarios**:

1. **Given** a keyboard using a backward-compatible protocol version, **When** the app
   connects, **Then** it functions normally.
2. **Given** a keyboard advertising an incompatible protocol version, **When** the app
   connects, **Then** it shows a clear, actionable message instead of misbehaving.
3. **Given** a released app and a released firmware, **When** their declared protocol
   versions are compared, **Then** both can be traced to the same published standard.

---

### Edge Cases

- **Download quarantine**: a browser marks the download as quarantined — the signed +
  notarized app must still open without the user editing attributes or running commands.
- **Older/newer macOS**: the published app states its minimum supported macOS; launching
  on an unsupported version shows a clear message rather than crashing.
- **Signing/notarization outage or cert expiry**: the release process must fail safe
  (no broken/untrusted artifact silently published).
- **Partial conformance**: a keyboard exposes the service but sends a malformed payload —
  the self-test tool pinpoints the exact failing requirement.
- **Conformance tool with no keyboard / Bluetooth off**: the tool reports a clear
  environment error, distinct from a conformance failure.
- **Version skew**: the app no longer supports a protocol version an old firmware pins —
  the app explains the incompatibility and points to an upgrade path.
- **Non-macOS user downloads the app**: messaging makes the platform requirement clear, and
  notes that Windows and Linux are planned for the next iteration (not yet available).
- **Standard change propagation**: when the standard is revised, both the app and the
  firmware must be able to pin and migrate versions without ambiguity about which is
  authoritative.
- **Existing Totem users**: after the app moves to its own repo, current users keep
  working (their keyboard remains a conforming keyboard; settings are preserved).

## Requirements *(mandatory)*

### Functional Requirements

**Downloadable, trusted app (US1)**

- **FR-001**: The project MUST publish prebuilt, ready-to-run app artifacts that end
  users can download and launch without building from source or using a terminal.
- **FR-002**: The published macOS app MUST be signed and notarized so that, on a clean
  supported machine, it launches via normal double-click without being blocked as
  untrusted.
- **FR-003**: Each published app release MUST be versioned and MUST state which protocol
  version(s) it supports and its minimum supported macOS version.
- **FR-004**: User-facing instructions MUST let a non-technical user find, download,
  launch, and grant Bluetooth permission to the app without developer knowledge.

**Standalone app repo & protocol ownership (US2)**

- **FR-005**: The app MUST reside in its own repository, independent of any keyboard
  firmware repository, and MUST be buildable and releasable without access to any
  firmware repository.
- **FR-006**: The authoritative, versioned protocol standard MUST live in the app
  repository as a self-contained, independently versioned artifact with no dependencies
  on firmware-repo-internal files, so any party can implement against it by reading the
  app repo alone.
- **FR-007**: The protocol standard MUST completely specify and constrain the
  firmware↔app interaction: the status service identity, the payload layout, the
  keyboard's self-reported name, discovery expectations, and the versioning/compatibility
  rules.
- **FR-008**: This firmware project MUST consume a pinned version of the published
  protocol standard rather than maintaining its own separate copy, so the two sides share
  a single source of truth.

**Keyboard conformance (US3)**

- **FR-009**: The project MUST provide a conformance guide that states the complete,
  concrete body of work a keyboard must complete to support the protocol, including
  prerequisites (e.g., a central BLE role).
- **FR-010**: The project MUST provide a conformance checklist that enumerates each
  required behavior as an individually verifiable item.
- **FR-011**: The project MUST provide a self-test/conformance tool that connects to a
  candidate keyboard and reports pass/fail for each checklist item, naming the specific
  nonconformance when an item fails.
- **FR-012**: The conformance tool MUST identify and test keyboards by the protocol
  standard (the service contract) alone, never by a specific make, model, or name.

**Versioned compatibility (US4)**

- **FR-013**: The app MUST declare the protocol version(s) it supports and MUST
  determine, on connection, whether a keyboard's protocol version is compatible.
- **FR-014**: On a backward-compatible version difference the app MUST continue to
  function; on an incompatible version it MUST show a clear, actionable message rather
  than crashing or displaying wrong data.
- **FR-015**: Protocol changes MUST follow documented versioning rules (compatible
  additions vs. breaking changes) and MUST be published as a new protocol version that
  both the app and keyboards can pin.

**Backward compatibility / migration**

- **FR-016**: Moving the app into its own repository and elevating the interface contract
  to the shared standard MUST preserve current functionality for existing users, and the
  existing Totem keyboard MUST remain supported as a conforming keyboard with no
  user-visible regression.

### Key Entities *(include if feature involves data)*

- **Protocol Standard**: The authoritative, versioned specification of the firmware↔app
  interface; hosted in the app repo as the single shared source of truth. Covers service
  identity, payload layout, keyboard name, discovery, and versioning/compatibility rules.
- **App Release**: A versioned, signed, notarized, downloadable build; declares its
  supported protocol version(s) and minimum OS.
- **Conformance Kit**: The guide + checklist + self-test tool used to verify a keyboard
  against the standard.
- **Conforming Keyboard**: Any keyboard that passes the conformance checks. The firmware
  project's Totem build is the reference conforming keyboard.
- **Personas**: End User (downloads/runs the app), Keyboard Author (makes a keyboard
  conform), Maintainer (owns the standard and publishes releases).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On a clean supported Mac, a non-technical user can go from "open the
  releases page" to "app running and showing keyboard status" in under 5 minutes using
  only the published artifact and instructions — no terminal, no build.
- **SC-002**: The published app launches via double-click with zero security warnings on
  a clean supported machine in 100% of trial launches.
- **SC-003**: The app repository can be cloned and produce a release artifact with no
  keyboard-firmware repository present (independent build succeeds).
- **SC-004**: A third party can build a conforming keyboard using only the app repo's
  protocol standard (no access to the reference firmware), and the self-test tool then
  reports 100% pass.
- **SC-005**: Running the self-test tool against a keyboard with a deliberately
  introduced defect pinpoints the specific failing requirement in 100% of seeded-defect
  trials.
- **SC-006**: In 100% of releases, the protocol version used by the app and by the
  firmware can each be traced to the same published standard version (single source of
  truth; no divergence).
- **SC-007**: When the app encounters a keyboard advertising an unsupported protocol
  version, it shows a clear message in 100% of cases, with zero crashes or wrong-data
  displays.
- **SC-008**: The existing Totem keyboard passes conformance unchanged and continues to
  work with the released app (no regression against feature 001's acceptance scenarios).

## Assumptions

- **Platform**: This iteration delivers the **macOS** implementation only (consistent with
  features 001/002); its prebuilt distribution, signing, and notarization are macOS-specific.
  The architecture is **not locked to a single platform**: **Windows and Linux compatibility
  are planned for the next iteration (feature 004)** and are deliberately not built this
  iteration. Because the KBP standard is already OS-neutral, adding a platform is a new
  implementation against the same protocol, not a protocol change.
- **Signing prerequisite**: Signed + notarized distribution requires an Apple Developer
  ID account and CI signing secrets; obtaining and funding that account is a project
  prerequisite and external dependency.
- **Protocol home & coupling mitigation**: Per the user's decision, the protocol standard
  lives in the app repo, but as a self-contained, open, permissively-licensed `protocol/`
  module that does not depend on app source. It is versioned independently of the app (its
  own semver + changelog), and firmware and any other implementation pin a protocol
  version by tag/artifact rather than by an app release. This supersedes feature 002's
  in-place use of the in-repo contract as the long-term home. Pre-agreed extraction
  trigger: if a second independent implementation (e.g., a non-macOS app) appears,
  `protocol/` is promoted to its own neutral repository. The next iteration's Windows/Linux
  app is expected to be exactly that trigger.
- **Dependency on feature 002**: The code-level decoupling from feature 002 (service-UUID
  identity, keyboard self-reported name, firmware kit + porting guide) is a prerequisite
  input; this feature standardizes, packages, and distributes that work.
- **Conformance tool lineage**: The self-test/conformance tool evolves from the existing
  on-device probe.
- **Distribution channel**: Releases are published on the app repo's releases page; other
  channels (Homebrew, App Store) and in-app auto-update are out of scope for this
  iteration (users download new releases manually).
- **Versioning policy**: Protocol versioning follows the existing contract's compatibility
  rules — trailing/reserved additions are backward-compatible; changing byte positions or
  identifiers is breaking.
- **Reference keyboard**: This firmware repository becomes the reference conforming
  keyboard and pins a specific published protocol version.
- **Explicit non-goals (this iteration)**: Windows/Linux binaries (planned for the next
  iteration — feature 004), in-app auto-update, App Store distribution, a public "verified
  keyboards" certification/registry program, and per-keyboard custom UI are all out of scope
  for this feature. Cross-platform support is **deferred, not rejected**.
