# Feature Specification: Cross-Platform App (Windows & Linux) on One Codebase

**Feature Branch**: `004-cross-platform-app`

**Created**: 2026-10-06

**Status**: Draft (skeleton — pending `/speckit-clarify`)

**Input**: Carried over from the feature 003 discussion: "我们不是 macOS-only,后续也要兼容
Windows 和 Linux" + chosen route "跨平台框架一套多端" (one cross-platform framework, one
codebase, multiple targets). This feature is the "next iteration" that feature 003 deferred
Windows/Linux support to.

> **Skeleton note**: This is an intentionally incomplete draft that captures the known direction
> and flags the open decisions as `[NEEDS CLARIFICATION]`. Run `/speckit-clarify` to resolve the
> pending questions, then `/speckit-plan`. It inherits feature 003's architecture (standalone app
> repo, KBP protocol standard, conformance kit, unsigned-first-then-signed release pipeline) and
> only extends it to more platforms — it does **not** revisit those decisions.

## Clarifications

### Pending (resolve via `/speckit-clarify`)

- **Q-FRAMEWORK**: Which cross-platform framework? (e.g. Tauri / Electron / Flutter / Qt /
  .NET MAUI.) Decider for the whole feature. Prior art: ZMK Studio uses **Tauri v2**. →
  `[NEEDS CLARIFICATION]`
- **Q-MACOS-FATE**: Does the cross-platform app **replace** the existing macOS-native Swift app
  (one codebase for all three OSes), or do we **keep macOS native** and add the cross-platform app
  for Windows/Linux only? (The chosen "one codebase multi-target" route implies replacing the
  Swift app, retiring features 001/002's native implementation — confirm the sunk-cost tradeoff.)
  → `[NEEDS CLARIFICATION]`
- **Q-BLE-FEASIBILITY**: Can the chosen framework reach each OS's BLE stack to satisfy KBP's
  discovery rule — enumerating an **already-connected, non-advertising** BLE HID keyboard and
  reading its GATT? macOS uses CoreBluetooth `retrieveConnectedPeripherals`; Windows uses WinRT
  (`BluetoothLEDevice` + paired/connected-device enumeration); Linux uses BlueZ (D-Bus). Needs a
  spike. May force a KBP discovery-wording amendment (should stay additive/MINOR). →
  `[NEEDS CLARIFICATION]`
- **Q-LINUX-DIST**: Linux distribution format(s) and "download & run" expectation —
  AppImage? `.deb`? Flatpak? Snap? Which is the primary trusted artifact? → `[NEEDS CLARIFICATION]`
- **Q-WIN-SIGNING**: Windows code-signing approach — Azure Trusted Signing (ZMK Studio's choice)
  vs an OV/EV certificate vs unsigned-first (mirroring 003's macOS stance)? → `[NEEDS CLARIFICATION]`
- **Q-MIN-OS**: Minimum supported Windows (e.g. Windows 10 1809+/11) and Linux baseline (BlueZ
  version / distro matrix). → `[NEEDS CLARIFICATION]`
- **Q-TRANSPORT**: Stay **BLE-only** (consistent with KBP v1), or also support USB/serial (ZMK
  Studio supports serial)? Recommended: BLE-only this feature; serial is a separate future item.
  → `[NEEDS CLARIFICATION]`

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A Windows user downloads a ready-to-run app (Priority: P1)

A Windows user goes to the project's releases page, downloads the prebuilt Windows app, and
launches it. After granting any required Bluetooth permission, it shows the live status (active
layer + held modifiers) of their compatible keyboard — no source checkout, no build tools, no
terminal. Mirrors feature 003's US1, on Windows.

**Why this priority**: Windows is the largest desktop audience the product currently cannot reach;
it is the headline deliverable of this iteration.

**Independent Test**: On a clean, supported Windows machine, download the published artifact, launch
it, and confirm it shows the status panel when a compatible keyboard is connected.

**Acceptance Scenarios**:

1. **Given** the releases page, **When** a Windows user downloads the published app, **Then** they
   can launch it with no build step and no terminal.
2. **Given** the app running with Bluetooth permission, **When** a compatible keyboard is connected,
   **Then** the app shows its live status.
3. **Given** a Windows trust prompt (SmartScreen), **When** the artifact is `[NEEDS CLARIFICATION:
   signed vs unsigned-first]`, **Then** the first-launch experience matches the declared signing
   state (documented workaround if unsigned).

---

### User Story 2 - A Linux user downloads a ready-to-run app (Priority: P2)

A Linux user downloads the published Linux artifact (`[NEEDS CLARIFICATION: AppImage/deb/flatpak]`)
and runs it; after Bluetooth permission/BlueZ access it shows live keyboard status.

**Why this priority**: Completes "cross-platform" and serves the mechanical-keyboard/Linux overlap,
but is a smaller audience than Windows.

**Independent Test**: On a clean supported Linux distro, obtain the published artifact, run it, and
confirm live status with a compatible keyboard connected.

**Acceptance Scenarios**:

1. **Given** the releases page, **When** a Linux user downloads the artifact, **Then** it runs
   without building from source.
2. **Given** BlueZ access, **When** a compatible keyboard is connected, **Then** the app shows live
   status.

---

### User Story 3 - One codebase builds all platforms (Priority: P2)

Maintainers build macOS, Windows, and Linux artifacts from a **single cross-platform codebase**, so
a change ships to all three without maintaining divergent native apps.

**Why this priority**: The chosen architecture ("一套多端"); it is what makes ongoing multi-platform
maintenance sustainable rather than a per-OS fork.

**Independent Test**: From one clean checkout, CI produces runnable artifacts for all three OSes
from the same source, with no per-OS source fork.

**Acceptance Scenarios**:

1. **Given** the app repo, **When** CI runs the matrix build, **Then** macOS/Windows/Linux artifacts
   are produced from the same codebase.
2. **Given** a single bug fix, **When** it is committed once, **Then** it is reflected in all three
   platform builds without duplicated per-OS edits.

---

### User Story 4 - The protocol becomes a neutral, shared standard (Priority: P3)

With a second independent implementation now existing (the cross-platform app alongside — or
replacing — the macOS one), the KBP `protocol/` is promoted to its **own neutral repository**
(feature 003's pre-agreed extraction trigger). All platform builds and the firmware pin the **same**
published KBP version.

**Why this priority**: Realizes the ecosystem endgame of feature 003; it protects neutrality once
more than one implementation depends on the standard.

**Independent Test**: The protocol lives in its own repo with unchanged semver/tags; the app and the
firmware both pin a `protocol-vX.Y.Z` tag from that repo; nothing references an app-repo-internal
path for the standard.

**Acceptance Scenarios**:

1. **Given** the extracted protocol repo, **When** a third party implements a keyboard, **Then** they
   read only that repo.
2. **Given** app + firmware releases, **When** their KBP versions are compared, **Then** both trace
   to the same neutral-repo tag.

---

### Edge Cases

- **Windows BLE quirks**: a connected BLE HID keyboard that stopped advertising must still be
  discoverable via WinRT connected/paired-device enumeration (not scanning). `[NEEDS CLARIFICATION:
  verified by spike]`
- **Linux BlueZ permissions**: the app must handle missing BlueZ/no adapter/permission denied with a
  clear message, distinct from "no keyboard".
- **Per-OS trust prompts**: SmartScreen (Windows), Gatekeeper (macOS), and Linux's lack of a
  universal signing model must each be messaged according to the declared signing state.
- **Framework can't reach a BLE API**: if the chosen framework lacks adequate BLE access on an OS,
  a native plugin/sidecar is required — `[NEEDS CLARIFICATION: fallback plan]`.
- **macOS parity**: if the macOS Swift app is replaced, the cross-platform macOS build must preserve
  features 001/002 behavior with no user-visible regression.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The project MUST publish prebuilt, ready-to-run **Windows** artifacts downloadable and
  launchable without building from source or using a terminal.
- **FR-002**: The project MUST publish prebuilt, ready-to-run **Linux** artifacts (`[NEEDS
  CLARIFICATION: format(s)]`) with the same no-build, no-terminal expectation.
- **FR-003**: All platform apps MUST be built from a **single cross-platform codebase** (`[NEEDS
  CLARIFICATION: framework]`); no per-OS source fork of the app logic.
- **FR-004**: Each platform app MUST discover and identify a keyboard **by the KBP service contract
  alone** (service UUID), never by make/model/name — reusing KBP unchanged (no new protocol version
  unless a discovery-wording amendment proves necessary; `[NEEDS CLARIFICATION: Q-BLE-FEASIBILITY]`).
- **FR-005**: Each platform app MUST render the keyboard's self-reported GAP name (with the generic
  fallback) and the live `[layer_index][mods][layer_name]` status, identical in meaning across OSes.
- **FR-006**: Each published app release MUST be versioned and MUST declare its supported KBP
  version(s) and its minimum OS version per platform.
- **FR-007**: Each platform's artifact MUST state its **signing/trust state**; the pipeline MUST be
  **fail-safe** (never publish a broken/half-signed artifact) — reusing 003's inert-then-enabled
  signing model, extended to Windows (`[NEEDS CLARIFICATION: Q-WIN-SIGNING]`) and Linux.
- **FR-008**: The KBP `protocol/` MUST be promoted to its own **neutral repository**; the app (all
  platforms) and the firmware MUST pin the same published KBP tag (extraction trigger from 003).
- **FR-009**: The conformance kit MUST remain platform-agnostic and continue to verify a keyboard by
  the KBP contract regardless of which OS the kit runs on.
- **FR-010**: Backward compatibility — the existing Totem reference keyboard MUST keep working with
  all platform apps with no firmware change; existing macOS users MUST retain their settings
  (`[NEEDS CLARIFICATION: Q-MACOS-FATE — settings migration if the macOS app is replaced]`).

### Key Entities *(include if feature involves data)*

- **Cross-Platform App**: One codebase, multiple platform targets (macOS/Windows/Linux); the
  KBP consumer. Supersedes or complements the macOS-native Swift app (`[NEEDS CLARIFICATION:
  Q-MACOS-FATE]`).
- **Platform Release**: A per-OS versioned, downloadable artifact (Windows installer/portable,
  Linux `[format]`, macOS bundle) with a declared signing/trust state and min-OS.
- **Neutral Protocol Repo**: The promoted KBP standard in its own repository; the single shared
  source of truth pinned by every implementation.
- **Per-OS BLE Adapter**: The platform binding (CoreBluetooth / WinRT / BlueZ) the framework uses to
  satisfy KBP discovery; may be a plugin/sidecar if the framework lacks native BLE.
- **Personas**: End User (Windows/Linux/macOS), Keyboard Author (unchanged, uses the conformance
  kit), Maintainer (owns the neutral protocol repo + the multi-platform release pipeline).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On a clean supported Windows machine, a user goes from "releases page" to "app showing
  keyboard status" without a terminal or build, in under 5 minutes.
- **SC-002**: On a clean supported Linux machine, the same download-to-status flow succeeds without
  building from source.
- **SC-003**: A single committed change produces updated macOS/Windows/Linux artifacts from one
  codebase in CI (no per-OS source fork).
- **SC-004**: The existing Totem keyboard shows correct live status on **all three** platforms with
  no firmware change (no regression vs features 001/002).
- **SC-005**: The app and the firmware each pin a KBP version that traces to the **same** neutral
  protocol-repo tag (single source of truth preserved across the extraction).
- **SC-006**: Each platform release declares its signing/trust state; in 100% of releases the
  pipeline either publishes a correctly-signed artifact or fails without publishing (fail-safe).
- **SC-007**: `[NEEDS CLARIFICATION: zero-warning first launch targets per OS once signing is
  enabled — mirror of 003's SC-001/SC-002, pending Q-WIN-SIGNING and the macOS Developer ID
  follow-up]`.

## Assumptions

- **Inherits feature 003**: standalone app repo, KBP standard, conformance kit, release pipeline,
  and the ZMK-Studio-aligned signing-secret contract (`APPLE_*`) are prerequisites and are reused,
  not redesigned.
- **One cross-platform framework** is adopted (`[NEEDS CLARIFICATION: Q-FRAMEWORK]`); the current
  macOS-native Swift app is likely rewritten/retired under that framework (`[NEEDS CLARIFICATION:
  Q-MACOS-FATE]`).
- **KBP is OS-neutral** and reused as-is; any cross-platform discovery nuance SHOULD be an additive
  (MINOR) clarification, not a breaking change.
- **BLE-only transport** this feature (`[NEEDS CLARIFICATION: Q-TRANSPORT]`); USB/serial is a
  separate future item.
- **Signing**: Windows likely via Azure Trusted Signing (ZMK Studio's approach) or unsigned-first
  mirroring 003; Linux typically unsigned/GPG. All `[NEEDS CLARIFICATION]`.
- **Explicit non-goals (this feature)**: in-app auto-update, App Store/Microsoft Store/Flatpak-hub
  distribution channels, a "verified keyboards" registry, per-keyboard custom UI, and USB/serial
  transport — deferred, consistent with 003's non-goals.
