# Quickstart & Validation: Standalone App Repo, Shared Protocol Standard & Downloadable Release

End-to-end validation that feature 003 delivers the standalone app repo, the versioned protocol
standard, the firmware pin, the conformance kit, and the (unsigned) downloadable release. Scenarios
map to the spec's user stories and success criteria. Details live in
[contracts/](./contracts/) and [data-model.md](./data-model.md); this is the run guide, not the
implementation.

Repos: app = `github.com/ykiewang/keybeacon`, firmware = `github.com/ykiewang/zmk-config-totem`.

## Prerequisites

- macOS 12+ with Bluetooth; `swift` toolchain; Python 3.13 for the conformance tool.
- A ZMK keyboard flashed with the KeyBeacon kit on its **central** role (the reference Totem build,
  or any candidate keyboard).
- `git` with `subtree` (and optionally `git-filter-repo`) for the split; GitHub auth for the one
  manual push.
- Network access for the migration push and the online pin check (both degrade gracefully offline).

---

## A. App repo builds & releases with NO firmware repo present (US2, FR-005, SC-003)

```bash
# In a clean clone of the app repo ONLY (no firmware repo on disk):
git clone https://github.com/ykiewang/keybeacon && cd keybeacon
cd app/macos && swift build -c release && swift test
cd ../.. && ./packaging/make-app.sh         # assembles BleWidget.app + .dmg/.zip + .sha256
```

Expected:
- `swift build`/`swift test` succeed with no firmware repo anywhere on the machine.
- `make-app.sh` emits `BleWidget.app` inside `BleWidget-<ver>.dmg` and `.zip` with `.sha256` files.
- Nothing in the build references a firmware path (independent build; SC-003).

## B. Protocol standard is self-contained & independently versioned (US2, FR-006/FR-007)

```bash
cd keybeacon
cat protocol/VERSION                 # e.g. 1.0.0
# self-containment: reject links into firmware/app internals (not the mere word
# "firmware", which legitimately names the producer role in prose):
grep -nE '\]\(\.\./|\]\(/?(host|config)/|zmk-config-totem|app/macos' protocol/README.md \
  || echo "no internal links — OK"
git tag --list 'protocol-v*'         # protocol tags disjoint from app-v* tags
```

Expected:
- `protocol/` has `README.md` + `VERSION` + `CHANGELOG.md`; `VERSION` matches a `protocol-vX.Y.Z` tag.
- The self-containment grep finds **no** firmware/app-internal links (FR-006).
- `README.md` fully specifies identity, payload, name, discovery, and versioning (a third party can
  implement from it alone).

## C. Firmware pins the protocol and CI proves no divergence (US2, FR-008, SC-003/SC-006)

```bash
cd zmk-config-totem
cat protocol-pinned/kbp.lock                      # kbp_version, source_ref=protocol-v1.0.0, sha256
./scripts/verify-protocol-pin.sh                  # offline hash + (online) diff vs the pinned tag
echo "exit=$?"                                     # 0 = pin verified
```

Expected:
- Offline: `sha256(protocol-pinned/KBP.md)` equals `kbp.lock:snapshot_sha256`; versions agree.
- Online (if reachable): `KBP.md` is identical to the app repo's `protocol/README.md@protocol-v1.0.0`.
- **Seeded-divergence check**: edit one byte of `protocol-pinned/KBP.md` → `verify-protocol-pin.sh`
  exits non-zero (CI would fail), proving the single-source-of-truth guard (FR-008, SC-006).
- Offline-only run (no network) still passes on the hash alone (standalone guarantee, SC-003).

## D. History-preserving split produced the app repo (US2, migration)

```bash
cd zmk-config-totem
./scripts/migrate/split-app-repo.sh --dry-run     # prints the planned subtree splits & target tree
# produces a local keybeacon/ tree; inspect history on moved paths:
git -C ../keybeacon log --oneline -- app/macos | head
```

Expected:
- `app/macos/` and `conformance/` carry their original commits (history preserved); `protocol/`
  carries its authoring history.
- The script is idempotent/inspectable; the final `git push` to `github.com/ykiewang/keybeacon` is a
  documented **manual maintainer step** (auth required), not run by CI.

## E. Conformance kit: guide + checklist + per-item self-test (US3, FR-009/010/011/012, SC-004/SC-005)

```bash
cd keybeacon/conformance
python3 conformance_tool.py                        # against a connected candidate keyboard
echo "exit=$?"
```

Expected:
- **Conforming keyboard** (reference Totem): every checklist item prints **PASS**; exit `0` (SC-004).
- **Seeded defect** (e.g. a build that sends a 1-byte payload, or doesn't suppress unchanged
  NOTIFYs): the tool prints **FAIL** on the *specific* item (names it) and exits `1` (SC-005,
  partial-conformance edge case).
- `CONFORMANCE.md` enumerates the complete body of work incl. the **central BLE role** prerequisite
  (FR-009); `checklist.md` lists each item as an individually verifiable line (FR-010).
- Identification is by **service UUID only** — pointing the tool at a renamed keyboard still works;
  at a non-KeyBeacon device it reports "not a KeyBeacon keyboard" (FR-012).

## F. Conformance tool environment errors are distinct from failures (US3, edge case)

```bash
# Turn Bluetooth OFF, or run with no keyboard connected:
python3 conformance_tool.py ; echo "exit=$?"
```

Expected:
- A clear **environment error** (e.g. "Bluetooth is off" / "no keyboard found") and exit `2` —
  distinct from a conformance failure (exit `1`), so authors don't confuse "can't test" with "fails".

## G. Downloadable app runs; version/compat declared; Gatekeeper gap documented (US1, FR-001/003/004)

```bash
# As an end user, from the app repo Releases page:
#   download BleWidget-<ver>.dmg → open → drag out BleWidget.app → double-click
```

Expected:
- The app launches as a menu-bar item (`LSUIElement`), and after Bluetooth permission shows live
  keyboard status (FR-001/FR-004).
- Release notes declare `app_version`, `supported_kbp` (traceable to `protocol-v1.0.0`), `min_macos`.
- **Honest gap**: because the artifact is **unsigned**, a clean Mac shows a Gatekeeper prompt on
  first open; the README/notes give the right-click→Open workaround. **SC-001/SC-002 are NOT met this
  iteration** (documented, not claimed). Launching on < macOS 12 shows a clear message, not a crash.

## H. Unsupported protocol version shows a clear message (US4, FR-013/014, SC-007)

```bash
# With a keyboard advertising a hypothetical UNKNOWN KeyBeacon-family service UUID
# (or a test double exposing a different custom service):
```

Expected:
- Known service (`AA440AA0-…`) → the app functions normally (FR-013).
- Unknown/newer KeyBeacon service → the app shows an **"unsupported protocol version"** message and
  does not crash or display wrong data (FR-014, SC-007).
- A plain non-KeyBeacon device → treated as "not a keyboard" (unchanged 002 behavior).

## I. Reference keyboard unchanged — no regression (FR-016, SC-008)

```bash
cd zmk-config-totem
# existing firmware CI builds all build.yaml targets; host logic tests still green:
# (app logic moved to the app repo; run there)
cd ../keybeacon/app/macos && swift test
```

Expected:
- All `build.yaml` targets (`totem_left`, `totem_right`, `settings_reset`) build as before; the
  KeyBeacon feature is still central-only.
- The Totem keyboard passes conformance (scenario E) unchanged and the app shows its status exactly
  as in features 001/002 — no user-visible regression (FR-016, SC-008).

---

## Success-criteria trace

| Scenario | Covers |
|----------|--------|
| A | SC-003, FR-005 |
| B | FR-006, FR-007 |
| C | FR-008, SC-003, SC-006 |
| D | US2 migration (history-preserving split) |
| E | FR-009/010/011/012, SC-004, SC-005 |
| F | FR-011 (environment vs conformance), edge case |
| G | FR-001/003/004; **SC-001/SC-002 deferred (unsigned)**; min-macOS edge case |
| H | FR-013/014, SC-007 |
| I | FR-016, SC-008 |

**Not validated this iteration (deferred with the unsigned-first decision)**: FR-002 (signed +
notarized), SC-001, SC-002 — these are met once Developer ID secrets are added and `release.yml`'s
conditional signing activates (contract `release-artifact.md` §3).
