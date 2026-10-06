# Governance Contract: Protocol Standard Home, Versioning & Conformance

**Status**: PROPOSED for feature 003. This contract governs **where the KeyBeacon Protocol (KBP)
lives, how it is versioned, and how conformance is proven**. It does **not** change the KBP wire
contract — the service/characteristic UUIDs and the `[layer_index][mods][layer_name]` payload are
frozen from features 001/002 (see `specs/001-ble-status-widget/contracts/status-snapshot.md` and the
KBP document itself). This is a packaging/ownership/versioning contract, so there is **no payload
version bump**.

## 1. Home & self-containment

- The authoritative KBP standard lives in the **app repository** `github.com/ykiewang/keybeacon` at
  `protocol/` (`README.md` + `VERSION` + `CHANGELOG.md`).
- `protocol/` MUST be **self-contained**: no links or references into app source, build files, or any
  firmware-repo-internal path. A third party MUST be able to implement a conforming keyboard by
  reading `protocol/` **alone** (FR-006, US2 independent test).
- The firmware repo (and any other implementer) MUST NOT keep a *separate editorial copy*; it keeps a
  **pinned vendored snapshot** governed by `firmware-pin.md`, never an independently-edited fork
  (FR-008).

## 2. Versioning (independent semver, UUID = MAJOR signal)

| Change kind | Rule | Wire effect | Tag |
|-------------|------|-------------|-----|
| MAJOR (breaking) | Reinterpret existing bytes / change identifiers | **New service UUID** | `protocol-v(N).0.0` |
| MINOR (additive) | Append reserved trailing bytes, or add an optional characteristic/descriptor | Same UUID; old hosts ignore the tail | `protocol-v(N).(M).0` |
| PATCH | Clarification only | None | `protocol-v(N).(M).(P)` |

- `protocol/VERSION` MUST equal the released tag's version; every release MUST add a
  `protocol/CHANGELOG.md` entry.
- Protocol tags (`protocol-vX.Y.Z`) are **disjoint** from app tags (`app-vX.Y.Z`): the standard and
  the app version independently (spec assumption).
- KBP `1.x` is service UUID `AA440AA0-…` with the §4 payload; there is **no** explicit version field
  in the v1 payload — the service UUID *is* the MAJOR signal.

## 3. Compatibility detection (on the wire)

- A host declares the set of KBP MAJORs it supports as the set of **service UUIDs** it recognizes.
- A device exposing a **recognized** service → compatible. A device exposing **no** KeyBeacon service
  → not a keyboard. A device exposing only an **unknown/newer** KeyBeacon-family service → reported as
  **"unsupported protocol version"**, never mis-parsed (FR-013/FR-014, SC-007).

## 4. Conformance (the kit is normative for "a keyboard supports KBP")

A keyboard **conforms to KBP 1.x** iff all items hold (this is the checklist the tool automates;
mirrors KBP §10):

1. Exposes service `AA440AA0-…` with characteristic `AA440AA1-…` (`READ`+`NOTIFY`, CCC present).
2. READ returns a snapshot **≥ 2 bytes** matching the §4 layout; `layer_name` is valid UTF-8 or empty.
3. NOTIFY fires on layer/modifier change and is **suppressed** when the snapshot is unchanged.
4. Remains discoverable **while connected** via connected-peripheral enumeration (stops advertising
   once connected).
5. Advertises a non-empty GAP device name (RECOMMENDED; else host uses a generic fallback).
6. For split keyboards: the feature is present only on the **central** (host-link) role and absent
   from peripheral and `settings_reset` images.

**Conformance kit obligations** (app repo `conformance/`):
- `CONFORMANCE.md` MUST enumerate the **complete, concrete** body of work (incl. the central BLE role
  prerequisite) so an author can plan the port (FR-009).
- `checklist.md` MUST list each item above as an **individually verifiable** line (FR-010).
- `conformance_tool.py` MUST test **by the service contract alone** (never by name/model), report
  **per-item PASS/FAIL** naming the specific nonconformance, and use exit codes `0`/`1`/`2`
  (pass / conformance-failure / environment-error) (FR-011/FR-012, SC-005, edge cases).

## 5. Extraction trigger (reserved, not executed now)

`protocol/` stays in the app repo **until** a second independent implementation appears (e.g. a
non-macOS app). On that trigger it is promoted to its own neutral repository, keeping the same semver
and tag scheme; existing pins (by tag) continue to resolve. Until then, promoting is a non-goal
(Principle IV / YAGNI). **The next iteration's Windows/Linux app (feature 004) is the anticipated
trigger** — the protocol's wire rules (service/characteristic, payload, discovery) are already
OS-neutral, so a second-platform implementation needs no protocol change.

## 6. Governance checks (CI, app repo)

- `protocol/VERSION` present and semver-valid; matches the latest `protocol-v*` tag on release.
- `protocol/CHANGELOG.md` has an entry for `VERSION`.
- `protocol/README.md` contains **no** firmware-internal or app-source links (self-containment lint).
