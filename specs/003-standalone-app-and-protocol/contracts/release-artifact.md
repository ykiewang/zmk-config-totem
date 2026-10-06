# Contract: Release Artifact & Distribution

**Status**: PROPOSED for feature 003. Defines the **downloadable macOS app artifact** and the
release pipeline in the app repo `github.com/ykiewang/keybeacon`. Realizes US1 (download & run) with
the user's chosen **unsigned-first** distribution (research R5, R8). Honestly scopes the Gatekeeper
gap: **SC-001 and SC-002 are NOT met this iteration** and are documented, not claimed.

## 1. Bundle shape (`packaging/make-app.sh`)

Input: a clean app-repo checkout. Steps:

1. `swift build -c release` (product `BleWidget`).
2. Assemble `BleWidget.app`:
   - `Contents/MacOS/BleWidget` (the release binary)
   - `Contents/Info.plist` (the existing plist; `LSUIElement=true`, `LSMinimumSystemVersion=12.0`,
     Bluetooth usage description) **plus** a declared `KBPSupportedVersions` key (§4).
   - `Contents/PkgInfo` (`APPL????`).
3. Emit distributables + checksums:
   - `BleWidget-<app_version>.zip` via `ditto -c -k --keepParent`
   - `BleWidget-<app_version>.dmg` via `hdiutil create`
   - `*.sha256` for each.

Output: a double-clickable `.app` inside `.dmg`/`.zip` (FR-001). The script MUST be runnable locally
and in CI with only `swift` + stock macOS tools (no Xcode project).

## 2. Release pipeline (`.github/workflows/release.yml`)

Trigger: push of tag `app-vX.Y.Z`. Job (macOS runner), **fail-safe** ordering:

```text
checkout → swift build -c release → swift test        # gate: tests must pass
        → packaging/make-app.sh                        # gate: bundle must assemble
        → [sign + notarize]  (CONDITIONAL — see §3)
        → compute sha256 → create GitHub Release → upload .dmg/.zip/.sha256 + notes
```

- If **any** gated step fails, the job fails and **no Release is published** (Principle V; the
  "signing/notarization outage or cert expiry" edge case fails safe).
- Release notes MUST state: `app_version`, `supported_kbp`, `min_macos`, `signing_state`, and (while
  unsigned) the `trust_note` first-open workaround.

## 3. Signing / notarization (wired but INERT this iteration)

The sign+notarize steps are **conditional on the presence of Developer ID secrets** and are
**skipped** when they are absent (this iteration) → `signing_state = unsigned`. The secret names are
**aligned with ZMK Studio's Tauri pipeline** so they are reusable as-is if feature 004 adopts a
cross-platform framework (same env contract that `tauri-action` consumes):

| Secret | Meaning |
|--------|---------|
| `APPLE_CERTIFICATE` | base64 of the Developer ID Application cert (`.p12`) |
| `APPLE_CERTIFICATE_PASSWORD` | password for that `.p12` |
| `APPLE_SIGNING_IDENTITY` | identity string, e.g. `Developer ID Application: Name (TEAMID)` |
| `APPLE_ID` | Apple ID used for notarization |
| `APPLE_PASSWORD` | app-specific password for `notarytool` |
| `APPLE_TEAM_ID` | Apple Developer Team ID |

- **Gating**: if `APPLE_SIGNING_IDENTITY` (and the cert pair) are present, run signing; else skip.
- **When present**: import `APPLE_CERTIFICATE` into a temp keychain, `codesign --options runtime
  --sign "$APPLE_SIGNING_IDENTITY"` the bundle, `xcrun notarytool submit --wait` with
  `APPLE_ID`/`APPLE_PASSWORD`/`APPLE_TEAM_ID`, then `xcrun stapler staple`. A failure in **either**
  signing or notarization **fails the job** (never publishes a half-signed/untrusted artifact).
- Enabling signing is **config-only** (add the six secrets); no pipeline rewrite. This is the
  follow-up that lets SC-001/SC-002 be met.
- *Alternative notarization creds* (not chosen, aligned path kept for parity with ZMK Studio): an
  App Store Connect **API key** (`APPLE_API_KEY`/`APPLE_API_ISSUER`/`APPLE_API_KEY_ID`) may replace
  the `APPLE_ID`/`APPLE_PASSWORD` pair later; the gating/fail-safe logic is unchanged.

## 4. Version & compatibility declaration

| Declared | Where | Satisfies |
|----------|-------|-----------|
| `app_version` | git tag `app-vX.Y.Z` + release title | FR-003 |
| `supported_kbp` | `Info.plist:KBPSupportedVersions` (service-UUID set) + release notes | FR-003/FR-013, SC-006 |
| `min_macos` | `Info.plist:LSMinimumSystemVersion` (`12.0`) + release notes | FR-003, "older/newer macOS" edge case |
| `signing_state` | release notes (`unsigned` now) | US1 honesty (R8) |

- `supported_kbp` MUST be traceable to a published `protocol-vX.Y.Z` (single source of truth, SC-006).
- Launching on an unsupported macOS MUST show a clear message rather than crash (edge case) — the
  stated `min_macos` + a runtime OS check.

## 5. Download & run UX (user-facing)

- The app repo `README.md` MUST let a non-technical user **find → download → launch → grant
  Bluetooth** without a terminal or build tools (FR-004).
- While `signing_state=unsigned`, the README + release notes MUST give the first-open workaround
  (right-click → **Open**, confirm once; or remove the quarantine attribute) and state that a future
  signed release will remove this step.
- Non-macOS visitors MUST see a clear platform-requirement note, stating that Windows and Linux
  are planned for the next iteration (feature 004) and not yet available (edge case).

## 6. Explicitly NOT in scope (this iteration)

Signed/notarized artifact (deferred until Developer ID account exists), Homebrew/App Store channels,
in-app auto-update, and **Windows/Linux builds (planned for the next iteration — feature 004)**.
These are deferred items; the macOS-only artifact scope here is for **this iteration**, not a
permanent constraint.

## 7. Success-criteria status for US1

| Criterion | This iteration |
|-----------|----------------|
| FR-001 (prebuilt, double-click, no terminal) | **Met** (unsigned `.app` in `.dmg`/`.zip`) |
| FR-003 (versioned; declares KBP + min macOS) | **Met** |
| FR-004 (non-technical download/run/permission) | **Met** (with documented first-open step) |
| **SC-001** (< 5 min, zero warnings) | **NOT met — deferred** (unsigned ⇒ Gatekeeper prompt) |
| **SC-002** (double-click, zero warnings, 100%) | **NOT met — deferred** (unsigned ⇒ Gatekeeper prompt) |
| FR-002 (signed + notarized) | **NOT met — deferred** (fail-safe hooks wired; secrets pending) |
