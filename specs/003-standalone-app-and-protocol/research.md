# Phase 0 Research: Standalone App Repo, Shared Protocol Standard & Downloadable Release

All decisions below resolve the Technical Context for feature 003 and lock in the three
architecture choices the user approved: **(1) create the standalone app repo now and migrate with
git history**, **(2) firmware pins the protocol via a vendored snapshot + version lock**, and
**(3) ship an unsigned artifact this iteration**. They build on features 001 (status snapshot) and
002 (service-UUID identity, GAP-name display, KeyBeacon kit, probe). No open NEEDS CLARIFICATION
remains.

Repo URLs are fixed: app repo = `github.com/ykiewang/keybeacon`; firmware repo (this one) =
`github.com/ykiewang/zmk-config-totem`.

---

## R1. Repository split boundary — what moves vs. what stays

- **Decision**: Three assets move to the app repo as top-level directories:
  - `host/macos/` → **`app/macos/`** (the macOS app)
  - `specs/003-standalone-app-and-protocol/protocol/` → **`protocol/`** (authoritative KBP)
  - a conformance kit **evolved from** `tools/probe.py` → **`conformance/`** (tool + guide + checklist)
  The firmware repo keeps `config/` (incl. `keybeacon_kit/`), `build.yaml`, firmware CI, and
  `specs/` (the 001/002/003 planning history), and **gains** `protocol-pinned/` + a verify script.
- **Rationale**: Matches the spec's ownership model (app repo owns app + protocol + conformance kit;
  FR-005/006/009–012) and keeps the firmware repo a clean **reference conforming keyboard** whose
  runtime is unchanged (FR-016). `specs/` are firmware feature records and stay with firmware
  history; only the *protocol artifact* is extracted as the shared source of truth.
- **Alternatives considered**:
  - *Move `specs/` too* — rejected: 001/002 are firmware-feature specs, not app assets; moving them
    would scatter firmware history.
  - *Leave the conformance tool in firmware* — rejected: the kit verifies **any** keyboard against
    the standard and must live with the standard (US3), so a third party needs only the app repo.
  - *Keep `tools/probe.py` as the shipped conformance tool* — rejected as the shipped kit, but
    **retained in firmware** as a developer probe; the app-repo `conformance_tool.py` is the
    productized evolution (R6).

## R2. Migration mechanism — history-preserving split

- **Decision**: Produce the app repo tree with a committed script `scripts/migrate/split-app-repo.sh`
  using **`git subtree split`** (fallback `git filter-repo`) per moved path, re-rooting each path to
  its app-repo location, then assembling a new repo whose `origin` is
  `github.com/ykiewang/keybeacon`. Paths with real history (`host/macos/`, `tools/probe.py`) retain
  their commits; the freshly-authored `protocol/` carries its short history. The final
  `git push -u origin main` (and tag pushes) is a **maintainer step** requiring GitHub auth and is
  documented, not automated, because cross-repo push cannot be verified inside this repo's CI.
- **Rationale**: The user chose "create & migrate now, **preserve git history**." `subtree split`
  is built-in and deterministic; `filter-repo` is the robust fallback for multi-path re-rooting.
  Keeping the push manual avoids embedding credentials and keeps the feature verifiable locally
  (the script's output tree is inspectable before any push).
- **Alternatives considered**:
  - *Snapshot copy (no history)* — rejected: the user explicitly chose to preserve history.
  - *`git submodule` from app→firmware for shared code* — rejected: the two repos share only the
    protocol *contract*, not code; a submodule would recouple them.
  - *Automate the push in CI with a PAT* — rejected: puts cross-repo write credentials in this repo
    and can't be validated here; left as a documented manual step.

## R3. Protocol home, versioning & self-containment (governance)

- **Decision**: `protocol/` in the app repo is the **single source of truth**, versioned with its
  **own semver** in `protocol/VERSION` and `protocol/CHANGELOG.md`, released under **independent
  tags** `protocol-vX.Y.Z` (disjoint from app tags `app-vX.Y.Z`). KBP MAJOR is signaled **on the
  wire by the service UUID** (KBP §9); MINOR = reserved trailing bytes / optional additive
  characteristics; PATCH = clarifications. `protocol/` MUST NOT reference app source or
  firmware-internal files (self-contained; FR-006).
- **Rationale**: Independent tags/semver let firmware and any third party pin a protocol version by
  tag/artifact rather than by an app release (spec assumption), decoupling the standard's cadence
  from the app's. Keeping the UUID as the MAJOR signal reuses the already-shipped mechanism (no new
  version field, no wire change). Self-containment is what lets a third party implement from the app
  repo alone (US2 independent test).
- **Alternatives considered**:
  - *Promote `protocol/` to its own neutral repo now* — rejected for this iteration: the spec's
    **extraction trigger** (a second independent implementation, e.g. a non-macOS app) has not
    fired; promoting early adds a repo with one consumer (YAGNI, Principle IV). Reserved.
  - *Version the protocol together with the app* — rejected: couples the standard to app releases,
    the exact entanglement the feature removes.

## R4. Firmware pin mechanism — vendored snapshot + lock (the chosen "Vendored快照+版本号")

- **Decision**: Firmware pins KBP with two committed artifacts under `protocol-pinned/`:
  - **`KBP.md`** — a byte-for-byte snapshot of the pinned `protocol/README.md`.
  - **`kbp.lock`** — machine-readable pin record: `kbp_version` (e.g. `1.0.0`), `source_repo`
    (`github.com/ykiewang/keybeacon`), `source_ref` (tag `protocol-v1.0.0`), `source_commit` (sha),
    and `snapshot_sha256` (hash of `KBP.md`).
  A CI step runs **`scripts/verify-protocol-pin.sh`**: it recomputes `sha256(KBP.md)` and compares
  to `kbp.lock` (offline, always runs), and **when network is available** additionally fetches the
  pinned tag's `protocol/README.md` from the app repo and diffs it against `KBP.md`. Any mismatch
  **fails CI**.
- **Rationale**: Satisfies **SC-003** (firmware clones and builds with no app repo — the snapshot is
  local) and **FR-008/SC-006** (single source of truth, no divergence — the offline hash guards the
  snapshot's integrity and the online diff proves it still equals the upstream tag). A lock file is
  the standard dependency-pinning pattern and is human-reviewable.
- **Alternatives considered**:
  - *git submodule to the app repo* — rejected (user's non-choice): `clone --recursive` burden,
    pulls the **entire** app repo for a single sub-directory, and breaks standalone offline builds.
  - *CI-only download of a release artifact* — rejected: makes the firmware build network-dependent,
    violating SC-003's "no firmware-repo-present/standalone" spirit for offline clones.
  - *No snapshot, reference by URL only* — rejected: a dangling external reference is exactly what
    the constitution forbids ("not external or ephemeral").

## R5. App bundle & release pipeline (artifact production)

- **Decision**: Add **`packaging/make-app.sh`**: `swift build -c release`, then assemble a proper
  `BleWidget.app` (copy the binary into `Contents/MacOS/`, the existing `Info.plist` into
  `Contents/`, set `LSUIElement`), and emit both a `.zip` (via `ditto`) and a `.dmg` (via `hdiutil`)
  plus `sha256` checksums. **`.github/workflows/release.yml`** triggers on a `app-vX.Y.Z` tag:
  build → bundle → checksum → create a GitHub Release and attach artifacts + release notes. CI
  (`ci.yml`) runs on push/PR: `swift build`, `swift test`, a bundle smoke-assembly, and a protocol
  lint (presence of `VERSION`/`CHANGELOG`, no firmware-internal links).
- **Rationale**: There is **no `.app` bundler today** (the app is only `swift run`/`swift build`);
  a real bundle is the minimum for a double-clickable download (US1, FR-001). Producing `.zip`+`.dmg`
  with checksums is the conventional macOS release shape. Tag-driven release keeps versions explicit
  (FR-003).
- **Alternatives considered**:
  - *Ship the raw `swift build` binary* — rejected: not double-clickable, no `Info.plist`/
    `LSUIElement`, not what a non-technical user can launch.
  - *Xcode archive/`xcodebuild`* — rejected: heavier than needed for a SwiftPM menu-bar app;
    `make-app.sh` keeps the toolchain to `swift` + stock macOS tools.

## R6. Conformance kit (guide + checklist + self-test tool)

- **Decision**: Evolve `tools/probe.py` into **`conformance/conformance_tool.py`** that executes
  each KBP §10 checklist item and prints **PASS/FAIL per item**, naming the specific nonconformance
  on failure, with **distinct exit codes**: `0` all pass, `1` conformance failure, `2` environment
  error (Bluetooth off / no keyboard / connect timeout). Ship **`conformance/CONFORMANCE.md`** (the
  guide: the complete body of work — central BLE role prerequisite, expose service+characteristic,
  payload ≥ 2 bytes, notify-on-change suppression, GAP name) and **`conformance/checklist.md`** (each
  item as an individually verifiable line, cross-referenced to the tool's checks). The tool identifies
  candidates **by the service UUID only** (never by name/model; FR-012).
- **Rationale**: Directly realizes US3 and FR-009–012 and the spec's "probe → self-test/conformance
  tool" lineage. Separating environment errors (exit 2) from conformance failures (exit 1) satisfies
  the "Bluetooth off / no keyboard" edge case. Per-item output satisfies the "pinpoint the exact
  failing requirement" edge case and SC-005.
- **Alternatives considered**:
  - *A single pass/fail* — rejected: fails SC-005 (must name the specific failing requirement) and
    the partial-conformance edge case.
  - *Rewrite the tool in Swift* — rejected: the probe is already proven PyObjC CoreBluetooth; reuse
    minimizes risk and keeps the kit runnable without building the app.

## R7. Versioned compatibility behavior in the app (US4)

- **Decision**: The app **declares** its supported KBP MAJOR(s) as the set of recognized service
  UUIDs (today: `{AA440AA0-…}`), surfaced in `Info.plist` (e.g. `KBPSupportedVersions`) and release
  notes (FR-003/FR-013). Connection semantics: a device exposing the known service → works; a device
  exposing **no** KeyBeacon service → not a keyboard (unchanged 002 behavior); a device exposing only
  an **unknown/newer** KeyBeacon-family service → reported as **"unsupported protocol version"** with
  an actionable message, never mis-parsed (FR-014). Because KBP 1.x defines a single MAJOR UUID, the
  incompatible path is **mostly contract + a guard**; the concrete cross-version test uses a
  hypothetical second UUID (quickstart H).
- **Rationale**: Honors "a standard that constrains interaction must define version-skew behavior"
  while staying YAGNI — only one MAJOR exists, so we reserve the behavior and add the guard rather
  than build a version negotiator. Keeps SC-007 (clear message, no crash/wrong data).
- **Alternatives considered**:
  - *A payload version byte* — rejected: KBP already uses the service UUID as the MAJOR signal (R3);
    adding a byte is a redundant wire change.
  - *Silently ignore unknown services* — rejected: fails SC-007's "clear, actionable message."

## R8. Unsigned-first distribution & the Gatekeeper gap (the chosen "先出未签名产物")

- **Decision**: This iteration publishes an **unsigned** artifact. `make-app.sh` and `release.yml`
  include **inert signing/notarization hooks** gated on the presence of Developer ID secrets
  (`$DEVELOPER_ID`, notarization creds); with no secrets the steps are **skipped**, and with secrets
  present a **failure in signing or notarization fails the job** (fail-safe — never publish a
  half-signed/broken artifact). The CI secret names are **aligned with ZMK Studio's Tauri pipeline**
  (`APPLE_CERTIFICATE`, `APPLE_CERTIFICATE_PASSWORD`, `APPLE_SIGNING_IDENTITY`, `APPLE_ID`,
  `APPLE_PASSWORD`, `APPLE_TEAM_ID`) so the same secrets drop straight into a future Tauri/cross-platform
  pipeline (feature 004) with no renaming. The release notes and app-repo `README.md` document the
  first-open workaround (right-click → Open, or clear the quarantine attribute). **SC-001 and SC-002
  are explicitly marked NOT met this iteration**; a follow-up enables signing once the Developer ID
  account (external prerequisite) is funded.
- **Rationale**: The user chose unsigned-first. Honesty is required by the spec quality bar: an
  unsigned download **is** Gatekeeper-quarantined on a clean Mac, so claiming SC-001/SC-002 would be
  false. Wiring inert, fail-safe hooks means enabling signing later is config-only, and the fail-safe
  path already satisfies the "signing outage / cert expiry" edge case.
- **Alternatives considered**:
  - *ad-hoc sign (`codesign -s -`)* — rejected: still Gatekeeper-blocked after download; adds a step
    with no user-facing benefit for distribution (only helps local/dev runs).
  - *Claim SC-001/SC-002 met* — rejected: factually wrong for an unsigned artifact.
  - *Block the whole feature until Developer ID exists* — rejected: the repo split, protocol
    governance, conformance kit, and release pipeline deliver value now; signing is a later toggle.

## R9. Platform scope — de-lock from macOS-only; Windows & Linux next iteration

- **Decision**: This iteration ships **macOS only**, but the feature **removes the permanent
  "macOS-only" lock**. **Windows and Linux compatibility are planned for the next iteration
  (feature 004)** and are not implemented here. No Windows/Linux code, CI jobs, or bundles are
  added in 003 — adding empty cross-platform scaffolding now would be rework once 004 picks a
  concrete cross-platform approach.
- **Rationale**: KBP is already OS-neutral (BLE GATT + byte layout), so a second-platform app is a
  new *implementation* against the same standard, not a protocol change — precisely the ecosystem
  the standalone-protocol design enables. The next-iteration non-macOS app is the "second
  independent implementation" that **fires the R3 extraction trigger** (promote `protocol/` to its
  own neutral repo). The app's intended cross-platform route is a **single multi-target framework**
  (à la ZMK Studio's Tauri app, one codebase for macOS/Windows/Linux); the concrete framework
  choice and the fate of the current macOS-native Swift app are deferred to feature 004's spec.
- **Alternatives considered**:
  - *Build Windows/Linux now in 003* — rejected: balloons scope and delays the macOS MVP.
  - *Keep "macOS-only" permanently* — rejected: the product must reach Windows/Linux users.
  - *Maintain separate native apps per OS (Swift + WinUI/…)* — noted but not chosen here; the
    standing direction is one cross-platform framework (feature 004 decides).
  - *Move the protocol into the ZMK upstream repo to "ease" multi-platform* — rejected: it
    surrenders governance/independent-semver control, collides with ZMK Studio's existing
    (protobuf-RPC) protocol, and does **not** simplify the single two-repo pin we already have;
    the neutral-repo extraction trigger (R3) achieves neutrality while keeping control.

---

## Resolved unknowns summary

| Topic | Resolution |
|-------|------------|
| Split boundary (R1) | app/macos, protocol/, conformance/ → app repo; firmware keeps config + gains protocol-pinned/ |
| Migration (R2) | history-preserving `subtree split`/`filter-repo` script; manual push to `ykiewang/keybeacon` |
| Protocol governance (R3) | app repo owns `protocol/`; own semver + `protocol-vX.Y.Z` tags; UUID = MAJOR signal; self-contained |
| Firmware pin (R4) | vendored `protocol-pinned/{KBP.md,kbp.lock}` + `verify-protocol-pin.sh` (offline hash + online diff) |
| Release pipeline (R5) | `make-app.sh` → .app + .dmg/.zip + checksums; `release.yml` on `app-vX.Y.Z`; `ci.yml` on push/PR |
| Conformance kit (R6) | `conformance_tool.py` (per-item PASS/FAIL, exit 0/1/2) + CONFORMANCE.md + checklist.md |
| Version skew (R7) | app declares supported KBP MAJOR(s) via service-UUID set; unknown → "unsupported" message |
| Unsigned-first (R8) | unsigned artifact; inert fail-safe signing hooks; SC-001/SC-002 deferred; Gatekeeper workaround documented |
| Platform scope (R9) | macOS this iteration; "macOS-only" lock removed; Windows & Linux planned next (feature 004) via one cross-platform framework; no cross-platform code/CI added in 003 |
