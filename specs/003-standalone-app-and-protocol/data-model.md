# Phase 1 Data Model: Standalone App Repo, Shared Protocol Standard & Downloadable Release

This feature's "data" is **ecosystem topology and release metadata**, not runtime payloads. The BLE
wire entities (status snapshot, modifier bitmask, Compatible Keyboard, Panel Settings) are
**unchanged** from features 001/002 — see `specs/001-ble-status-widget/data-model.md` and
`specs/002-multi-keyboard-support/data-model.md`. Entities below model the repos, the versioned
standard, the pin, the release, and the conformance kit. Field names are illustrative of structure,
not a mandated schema.

---

## Entity: Protocol Standard (KBP)

The authoritative, independently-versioned specification of the firmware↔app interface. Lives in the
**app repo** `protocol/` as the single shared source of truth (research R3; contract
`contracts/protocol-standard.md`).

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `spec` | Markdown | `protocol/README.md` | The normative KBP document (transport, discovery, identity, payload, versioning, conformance) |
| `version` | semver string | `protocol/VERSION` | e.g. `1.0.0`; independent of app version |
| `changelog` | Markdown | `protocol/CHANGELOG.md` | Protocol-only history, separate from app releases |
| `tag` | git tag | app repo | `protocol-vX.Y.Z`; the pinnable, citable release ref |
| `major_signal` | service UUID | KBP §9 | The on-wire MAJOR identifier (`AA440AA0-…` for 1.x) |

**Validation rules**:
- MUST be self-contained: no links into app source or firmware-internal files (FR-006).
- A MAJOR change MUST introduce a **new service UUID** and a new `protocol-v(MAJOR)…` tag (KBP §9).
- MINOR = reserved trailing bytes or an optional additive characteristic; same UUID. PATCH = wording.
- `version` and `tag` MUST agree; each released version MUST have a changelog entry.

**State / lifecycle**: `Draft` (authored in `specs/003/protocol/`) → `Published` (migrated to app
repo `protocol/`, tagged `protocol-v1.0.0`) → `Superseded` (a later tag exists; old tag stays
pinnable).

## Entity: Firmware Protocol Pin (`protocol-pinned/`)

How the **firmware repo** records exactly which KBP version it implements, so it builds standalone yet
provably tracks the upstream standard (research R4; contract `contracts/firmware-pin.md`).

| Field | Type | Storage | Rules |
|-------|------|---------|-------|
| `snapshot` | Markdown | `protocol-pinned/KBP.md` | Byte-for-byte copy of the pinned `protocol/README.md` |
| `kbp_version` | semver | `protocol-pinned/kbp.lock` | MUST match the snapshot's declared version |
| `source_repo` | URL | `kbp.lock` | `github.com/ykiewang/keybeacon` |
| `source_ref` | git tag | `kbp.lock` | `protocol-v1.0.0` |
| `source_commit` | sha | `kbp.lock` | Commit the snapshot was taken from |
| `snapshot_sha256` | hash | `kbp.lock` | `sha256(KBP.md)`; the offline integrity guard |

**Validation rules (enforced by `scripts/verify-protocol-pin.sh` in firmware CI)**:
- **Offline (always)**: `sha256(KBP.md)` MUST equal `snapshot_sha256` — the snapshot is intact.
- **Online (when network available)**: `KBP.md` MUST be identical to the app repo's
  `protocol/README.md` at `source_ref` — no divergence from the source of truth (FR-008, SC-006).
- A pin update is a deliberate commit that bumps `kbp_version`/`source_ref`/`source_commit` and
  refreshes `KBP.md` + `snapshot_sha256` together.

## Entity: App Release

A versioned, downloadable build published on the app repo's Releases page (research R5; contract
`contracts/release-artifact.md`).

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `app_version` | semver | git tag `app-vX.Y.Z` | Triggers `release.yml` |
| `platform` | enum | pipeline | **`macOS`** this iteration; **`windows`/`linux` planned (feature 004)** — not built in 003 |
| `bundle` | `BleWidget.app` | `packaging/make-app.sh` | Real bundle: binary + `Info.plist` + `LSUIElement` |
| `artifacts` | `.dmg`, `.zip` | packaging | Double-click-openable; plus `.sha256` checksums |
| `supported_kbp` | version set | `Info.plist` `KBPSupportedVersions` + notes | Declares supported KBP MAJOR(s) (FR-003/013) |
| `min_macos` | version | `Info.plist` `LSMinimumSystemVersion` (12.0) | Stated minimum OS (FR-003, edge case) |
| `signing_state` | enum | pipeline | **`unsigned`** this iteration; `signed+notarized` once Developer ID exists (R8) |
| `trust_note` | text | release notes + README | Gatekeeper first-open workaround while `unsigned` |

**Validation rules**:
- MUST be produced only if `swift build` + `swift test` + bundle assembly succeed (fail-safe; V).
- When `signing_state=signed+notarized`, a signing/notarization failure MUST fail the job (never
  publish a broken/half-signed artifact) — "signing outage/cert expiry" edge case.
- While `signing_state=unsigned`, the release MUST carry `trust_note`, and **SC-001/SC-002 are
  marked not-met** (honest gap, R8).
- Each release's `supported_kbp` MUST be traceable to a published `protocol-vX.Y.Z` (SC-006).

**State / lifecycle**: `built` → `bundled` → (`signed+notarized` | `unsigned`) → `published`
(GitHub Release) → `superseded` (manual; no in-app auto-update this iteration).

## Entity: Conformance Kit

The guide + checklist + self-test tool used to verify a keyboard against KBP (research R6; contract
`contracts/protocol-standard.md` §conformance). Lives in the app repo `conformance/`.

| Part | File | Role | Output |
|------|------|------|--------|
| Guide | `conformance/CONFORMANCE.md` | The complete body of work a keyboard must do (incl. central BLE role prerequisite) | human-readable |
| Checklist | `conformance/checklist.md` | Each KBP §10 item as an individually verifiable line | one line per requirement |
| Self-test tool | `conformance/conformance_tool.py` | Connects by service UUID; checks each item | **PASS/FAIL per item** + exit code |

**Tool contract**:
- Identifies candidates by the **service UUID only**, never by make/model/name (FR-012).
- Exit codes: `0` = all items pass; `1` = at least one **conformance** failure (names the specific
  item, e.g. "payload < 2 bytes", "NOTIFY not suppressed when unchanged"); `2` = **environment**
  error (Bluetooth off, no keyboard, connect timeout) — distinct from a conformance failure.
- Reports the discovered GAP name for human confirmation; absence of a non-empty name is a SHOULD
  (fallback), not a hard failure (KBP §10 item 5).

## Entity: Conforming Keyboard

Any keyboard that passes the Conformance Kit. The firmware repo's **Totem build is the reference**
conforming keyboard.

| Field | Type | Notes |
|-------|------|-------|
| `implements` | KBP version | The pinned `kbp_version` from `protocol-pinned/kbp.lock` |
| `role` | BLE role | Central (host-link) only — the feature is central-gated (Principle III) |
| `evidence` | tool run | `conformance_tool.py` exit `0` against the device |
| `reference` | bool | `true` for Totem; a third party's keyboard is a non-reference conforming keyboard |

**Validation rules**:
- MUST expose service `AA440AA0-…` + characteristic `AA440AA1-…` (`READ`+`NOTIFY`, CCC).
- MUST pass all `checklist.md` items (tool exit `0`) for the KBP version it pins.
- The reference keyboard MUST continue to pass **unchanged** from feature 001/002 (FR-016, SC-008).

## Entity: Personas (actors)

| Persona | Goal | Touches |
|---------|------|---------|
| End User | Download & run the app, see keyboard status | App Release (`.dmg`/`.zip`), README download/run guide |
| Keyboard Author | Make a keyboard conform and prove it | Protocol Standard, Conformance Kit (guide + checklist + tool) |
| Maintainer | Own the standard, cut releases, keep the pin honest | Protocol Standard tags, App Release pipeline, firmware pin + CI verify |

---

## Repository topology (relationships)

```text
app repo: github.com/ykiewang/keybeacon  (authoritative)
├── protocol/        ──(tag protocol-vX.Y.Z)──► cited/pinned by anyone
│      ▲ source of truth
├── app/macos/       ──(tag app-vX.Y.Z)──► release.yml ──► GitHub Release (.dmg/.zip, unsigned)
└── conformance/     ──► verifies ──► any Conforming Keyboard

firmware repo: github.com/ykiewang/zmk-config-totem  (reference conforming keyboard)
├── config/ (unchanged runtime)
└── protocol-pinned/{KBP.md, kbp.lock}
       ▲ vendored snapshot of protocol/ @ source_ref
       └── verify-protocol-pin.sh: sha256(KBP.md)==lock  AND (online) KBP.md==protocol/README.md@tag
                                   └── mismatch ⇒ CI fails  (single source of truth; FR-008/SC-006)
```

**Invariants**:
- Firmware builds with **no app repo present** (uses the local snapshot) — SC-003.
- The pin's online diff ties the firmware's implemented version to a published protocol tag — SC-006.
- No firmware runtime/wire change; the reference keyboard's behavior is byte-identical to 001/002 —
  FR-016, SC-008.
