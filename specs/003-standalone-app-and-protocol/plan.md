# Implementation Plan: Standalone App Repo, Shared Protocol Standard & Downloadable Release

**Branch**: `003-standalone-app-and-protocol` | **Date**: 2026-10-06 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-standalone-app-and-protocol/spec.md`

## Summary

Turn the KeyBeacon work into an ecosystem with three assets that can evolve independently:

1. **A standalone app repository** (`github.com/ykiewang/keybeacon`) that owns the macOS app,
   the protocol standard, and the conformance kit — buildable and releasable with **no firmware
   repo present** (SC-003). The current firmware repo (`github.com/ykiewang/zmk-config-totem`)
   becomes the **reference conforming keyboard**.
2. **The KeyBeacon Protocol (KBP)** elevated from an in-firmware draft to the app repo's
   self-contained, **independently versioned** `protocol/` module (own semver + changelog).
   Firmware **pins** a KBP version by a **vendored snapshot + lock record** (not a submodule,
   not an app release), so firmware still clones and builds standalone while a CI check proves
   the snapshot equals the pinned upstream tag — single source of truth with no divergence (FR-008).
3. **A downloadable release** produced by app-repo CI: `swift build -c release` → assemble a real
   `BleWidget.app` bundle → `.dmg`/`.zip` → GitHub Release, with checksums and a declared
   supported-KBP-version + minimum-macOS. The **signing/notarization steps are wired but inert
   this iteration** (no Developer ID secrets yet) so the artifact is **unsigned**; the release
   pipeline is fail-safe (never publishes a broken/half-signed artifact).

Per the user's three architecture decisions: the split is **executed now, preserving git history**
(git `subtree split`/`filter-repo`) with the repo URL above; firmware pins the protocol via a
**vendored snapshot + version lock**; and the first release is **unsigned**, so US1's zero-warning
criteria (SC-001/SC-002) are **explicitly deferred** and the Gatekeeper first-open workaround is
documented honestly rather than claimed as met.

This feature changes **no firmware runtime behavior** and **no BLE wire contract**: it is
repository topology, protocol packaging/versioning, conformance tooling, and release engineering.
The existing Totem keyboard remains a conforming keyboard with no user-visible regression (FR-016).

## Technical Context

**Language/Version**: App: Swift 5.9+ (macOS 12+). Conformance tool: Python 3.13 (PyObjC
CoreBluetooth, evolved from `tools/probe.py`). Protocol standard: Markdown. Release/migration
tooling: Bash + GitHub Actions YAML. Firmware reference: C (ZMK/Zephyr) — unchanged.

**Primary Dependencies**: SwiftPM, AppKit, CoreBluetooth, Foundation (app, unchanged from 002);
PyObjC CoreBluetooth (conformance tool); GitHub Actions macOS runner; `git subtree`/`git
filter-repo` (history-preserving split); `sha256sum`/`shasum` (pin + release checksums);
`hdiutil`/`ditto` (bundle `.dmg`/`.zip`). Deferred: `codesign` + `notarytool` (Developer ID).

**Storage**: No new runtime storage — the app keeps feature 002's `UserDefaults` keys. Protocol
versions are files under git with independent tags (`protocol-vX.Y.Z`); firmware pin is a committed
lock file + snapshot (`protocol-pinned/`).

**Testing**: App logic: existing XCTest over `BleWidgetCore` (unchanged, must stay green after the
move). Conformance tool: per-item PASS/FAIL self-test with distinct exit codes (pass / nonconformance
/ environment error). App-repo CI: `swift build` + `swift test` + bundle assembly + protocol lint.
Firmware CI: existing `build.yaml` targets **plus** a protocol-pin verification step. End-to-end:
`quickstart.md` scenarios.

**Target Platform**: macOS 12+ (app + conformance tool host) **this iteration**; **Windows and
Linux are planned for the next iteration (feature 004)**, not built here. Reference keyboard: ZMK
central role (SEEED XIAO BLE), unchanged.

**Project Type**: Multi-repo ecosystem — a standalone **app repo** (app + protocol + conformance
kit + release CI; macOS implementation this iteration, Windows/Linux planned next) and a
**reference firmware repo** (this repo) that pins the protocol.

**Performance Goals**: Preserve features 001/002 (layer/modifier change ≤ 1 s for ≥ 95% of changes;
zero idle traffic). Release build reproducible from a clean app-repo clone. SC-001 "download → running
in < 5 min" is **gated by signing** and therefore **deferred** with the unsigned-first decision.

**Constraints**:
- App repo MUST build & release with **no firmware repo present** (SC-003).
- Protocol `protocol/` MUST be self-contained — no dependency on app source or firmware-internal
  files — so a third party implements from the app repo alone (FR-006).
- Firmware MUST pin a KBP version by **vendored snapshot + lock**; a CI check MUST fail on
  snapshot/upstream divergence (FR-008, SC-006).
- First release is **unsigned** → on a clean Mac the download is Gatekeeper-quarantined; SC-001/SC-002
  are not met this iteration and MUST be labeled as such (honest gap).
- Release pipeline MUST be **fail-safe**: when signing is later enabled, a signing/notarization
  failure fails the job rather than publishing an untrusted/broken artifact (edge case).
- No firmware runtime/wire change; Totem stays conforming with no regression (FR-016, SC-008).

**Scale/Scope**: One protocol standard (KBP 1.x), one reference keyboard, a handful of releases.
Small codebases: ~4 Swift sources + tests (moved intact), one ~100-line conformance tool, one
Markdown standard, a few CI/packaging/migration scripts.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|-----------|------|--------|
| I. Interface Contract First | The in-repo contract is **promoted** to the authoritative, independently-versioned KBP standard; firmware pins an exact version and a CI check proves no divergence. The wire contract (service/char UUID, payload) is unchanged — no version bump. Both the app and the conformance tool are built against KBP alone. | PASS (strengthens I) |
| II. Keyboard as Source of Truth | No change to reported state: KBP preserves authoritative layer/mods + GAP-name identity from features 001/002. The app adds no inference and keeps no model registry. | PASS |
| III. Shield-Scoped, Minimal Footprint | Firmware reference is untouched (kit stays shield-scoped, central-gated, `default n`); this feature adds only a committed `protocol-pinned/` snapshot + a CI verify step — docs/metadata, **zero** on-air traffic or power change. | PASS |
| IV. MVP Discipline (YAGNI) | Bounded scope with explicit non-goals **this iteration** (Windows/Linux binaries — planned for the next iteration / feature 004, auto-update, App Store, verified-keyboard registry, per-keyboard UI). Unsigned-first defers signing instead of half-building it. Protocol-repo promotion is **reserved** behind the stated extraction trigger (second independent implementation — expected to be the next-iteration non-macOS app). | PASS |
| V. Hardware-Verified by CI | Firmware still builds all `build.yaml` targets and gains a protocol-pin check; the app repo gets its own CI (build + `swift test` + bundle + protocol lint); the conformance tool verifies a real keyboard on-device. A release is produced only if the whole pipeline passes (fail-safe). | PASS |

**Platform/workflow-constraint note (Principle I / "sources of truth under version control")**: the
authoritative protocol moves to the **app** repo, which is itself under version control, and the
firmware repo retains a **version-controlled pinned snapshot** (`protocol-pinned/`) plus a lock file.
The source of truth is therefore never external or ephemeral; it is split across two VCS repos with a
CI-enforced equality check. This is the spec's explicit, clarified decision (protocol home = app repo)
and supersedes feature 002's in-place in-repo contract as the long-term home. Recorded here as a
**justified evolution**, not a violation.

No violations. **Complexity Tracking not required.**

**Post-Phase-1 re-check**: Re-evaluated after `research.md`, `data-model.md`, `contracts/`, and
`quickstart.md`. The design keeps firmware runtime/wire unchanged, keeps `protocol/` self-contained,
enforces the single-source-of-truth with a CI diff against the pinned tag, and confines signing to a
later, fail-safe activation. Gate remains **PASS**.

## Project Structure

### Documentation (this feature)

```text
specs/003-standalone-app-and-protocol/
├── plan.md              # This file
├── research.md          # Phase 0 output (decisions R1–R8)
├── data-model.md        # Phase 1 output (ecosystem entities)
├── quickstart.md        # Phase 1 output (validation scenarios A–H)
├── contracts/
│   ├── protocol-standard.md     # governance: KBP home, semver, tags, self-containment
│   ├── firmware-pin.md          # vendored-snapshot + lock-file contract + CI verify
│   └── release-artifact.md      # bundle/release contract; signing deferred; version declaration
├── protocol/
│   └── README.md        # KBP 1.0.0 draft (authored here; migrates to app repo protocol/)
├── checklists/
│   └── requirements.md  # (from /speckit-specify)
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (the two repositories)

**App repository — NEW: `github.com/ykiewang/keybeacon`** (migrated with git history; the
authoritative home for the app, the protocol standard, and the conformance kit):

```text
keybeacon/
├── protocol/                       # authoritative KBP standard (independent semver)
│   ├── README.md                   # the KBP spec (from specs/003/protocol/README.md)
│   ├── VERSION                     # e.g. 1.0.0  (tagged protocol-v1.0.0)
│   └── CHANGELOG.md                # protocol-only changelog (separate from app releases)
├── app/macos/                      # the macOS app (moved from host/macos/, history preserved)
│   ├── Package.swift               # product renamed path; sources unchanged
│   ├── Sources/BleWidgetCore/{BLEClient,KeyboardStatus,CompatibleKeyboard,AppSettings}.swift
│   ├── Sources/BleWidget/{AppDelegate,FloatingPanel,main}.swift
│   ├── Tests/BleWidgetTests/*.swift
│   └── Info.plist                  # + declared supported KBP version(s) & LSMinimumSystemVersion
├── conformance/                    # the Conformance Kit (guide + checklist + self-test tool)
│   ├── conformance_tool.py         # evolved from tools/probe.py: per-item PASS/FAIL, exit codes
│   ├── CONFORMANCE.md              # the porting/conformance guide (what work a keyboard must do)
│   └── checklist.md                # each KBP §10 item as an individually verifiable line
├── packaging/
│   └── make-app.sh                 # assemble BleWidget.app (+ .dmg/.zip); signing hooks inert
├── .github/workflows/
│   ├── ci.yml                      # swift build + swift test + bundle smoke + protocol lint
│   └── release.yml                 # tag app-vX.Y.Z → build → bundle → checksums → Release (unsigned)
└── README.md                       # user download/run guide + Gatekeeper first-open note
```

**Firmware repository — THIS repo (`zmk-config-totem`), becomes the reference conforming keyboard**:

```text
zmk-config-totem/
├── config/                         # UNCHANGED (keybeacon_kit stays shield-scoped/central-gated)
├── build.yaml                      # UNCHANGED firmware targets
├── .github/workflows/
│   └── build.yml                   # EDITED: add a protocol-pin verify step (non-firmware job)
├── protocol-pinned/                # NEW: the pinned protocol (vendored, version-controlled)
│   ├── KBP.md                      # byte-for-byte snapshot of the pinned KBP README
│   └── kbp.lock                    # kbp_version + source_repo + source_ref(tag) + commit + sha256
├── scripts/
│   └── verify-protocol-pin.sh      # NEW: recompute sha256 == lock; optional online diff vs tag
├── tools/
│   └── probe.py                    # retained (dev probe); conformance tool now lives in app repo
└── readme.md                       # EDITED: point users to the app repo's Releases for downloads

# One-time migration tooling (run to seed the app repo, then retired):
scripts/migrate/
├── split-app-repo.sh               # subtree-split app/ (host/macos), protocol/, conformance paths
└── README.md                       # how the split was produced + the manual push/auth step
```

**Structure Decision**: Execute a **history-preserving split** into the new app repo
(`github.com/ykiewang/keybeacon`): the macOS app (`host/macos/` → `app/macos/`), the protocol draft
(`specs/003/protocol/` → `protocol/`), and the conformance kit (evolved from `tools/probe.py` →
`conformance/`) become the app repo's three top-level assets. The firmware repo keeps its ZMK config
**unchanged at runtime** and gains only a **version-controlled `protocol-pinned/` snapshot + lock**
and a CI verify step, so it still clones and builds standalone (SC-003) while the pin proves
single-source-of-truth (FR-008, SC-006). Signing is deferred: `packaging/make-app.sh` and
`release.yml` carry inert, fail-safe signing hooks that activate once Developer ID secrets exist,
without which the published artifact is unsigned and the Gatekeeper gap is documented (SC-001/SC-002
deferred). Cross-repo pushes (creating/populating the remote) are the only steps that cannot be
verified inside this repo's CI; the migration script produces the exact tree and the push to
`github.com/ykiewang/keybeacon` is a maintainer action requiring GitHub auth.

## Complexity Tracking

> No constitution violations — table intentionally omitted. The one notable topology change
> (authoritative protocol moving to the app repo) is a spec-clarified decision recorded as a
> justified evolution in the Constitution Check, enforced by a CI pin-equality check.
