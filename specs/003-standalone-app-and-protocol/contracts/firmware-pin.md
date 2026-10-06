# Contract: Firmware Protocol Pin (vendored snapshot + lock)

**Status**: PROPOSED for feature 003. Defines how the **firmware repo**
(`github.com/ykiewang/zmk-config-totem`) pins an exact KeyBeacon Protocol (KBP) version so it builds
**standalone** (no app repo present) while provably tracking the authoritative `protocol/` in the app
repo. Realizes the user's chosen mechanism: **vendored snapshot + version lock** (research R4).
Satisfies FR-008 (single source of truth), SC-003 (independent firmware build), SC-006 (version
traceable to one published standard).

## 1. On-disk layout (firmware repo)

```text
protocol-pinned/
├── KBP.md        # byte-for-byte snapshot of protocol/README.md @ the pinned tag
└── kbp.lock      # the pin record (below)
scripts/
└── verify-protocol-pin.sh   # CI check (offline hash + optional online diff)
```

## 2. `kbp.lock` format

A small, human-reviewable key/value file (YAML-style). All fields REQUIRED:

```yaml
kbp_version:     1.0.0
source_repo:     https://github.com/ykiewang/keybeacon
source_ref:      protocol-v1.0.0        # the pinnable git tag
source_commit:   <40-hex-sha>           # commit the snapshot was taken from
snapshot_sha256: <64-hex>               # sha256 of protocol-pinned/KBP.md
```

- `kbp_version` MUST equal the version declared inside `KBP.md`.
- `source_ref` MUST be a `protocol-vX.Y.Z` tag (not a branch) so the pin is immutable.
- `snapshot_sha256` MUST equal `sha256(protocol-pinned/KBP.md)`.

## 3. `verify-protocol-pin.sh` behavior (firmware CI)

Two layers; the script runs in firmware CI as a **non-firmware job** (no board build needed):

1. **Offline integrity (ALWAYS runs; no network)**
   - Recompute `sha256(protocol-pinned/KBP.md)` and compare to `kbp.lock:snapshot_sha256`.
   - Parse `KBP.md`'s declared version and compare to `kbp.lock:kbp_version`.
   - **Mismatch ⇒ exit non-zero (CI fails).** This guarantees the vendored snapshot is intact and
     self-consistent even with no app repo reachable (SC-003).

2. **Online equality (runs WHEN network is available; soft-skips offline)**
   - Fetch `protocol/README.md` at `kbp.lock:source_ref` from `source_repo` (e.g. raw URL or
     `git archive`).
   - Diff it against `protocol-pinned/KBP.md`.
   - **Any difference ⇒ exit non-zero (CI fails).** This proves the firmware's implemented version
     has **not diverged** from the authoritative standard at the pinned tag (FR-008, SC-006).
   - If the network/tag is unreachable, print a clear "online check skipped (offline)" notice and
     pass on the offline result alone — never fail *because* the app repo is unreachable (preserves
     SC-003's standalone guarantee).

Exit codes: `0` = pin verified; `1` = integrity/version/diff mismatch; `2` = malformed `kbp.lock`.

## 4. Updating the pin (deliberate, reviewable commit)

To adopt a new KBP version, a maintainer:

1. Copies `protocol/README.md` at the new `protocol-vX.Y.Z` tag into `protocol-pinned/KBP.md`.
2. Updates all `kbp.lock` fields (`kbp_version`, `source_ref`, `source_commit`, `snapshot_sha256`).
3. Commits both together; CI re-runs §3 and must pass.

A pin bump is the **only** sanctioned way the firmware's KBP version changes; `KBP.md` MUST NOT be
edited independently of the upstream standard (that would fork the contract, violating FR-008).

## 5. Standalone-build guarantee

- Firmware clone + `west build` (or the existing `build.yaml` CI) MUST NOT require the app repo: the
  snapshot is local and the online check is best-effort.
- Nothing in `config/` depends on `protocol-pinned/` at build time; the pin is **documentation +
  governance metadata**, so it adds **zero** firmware runtime/on-air change (Principle III).

## 6. Traceability

Given any firmware commit, `kbp.lock` names the exact `protocol-vX.Y.Z` it implements; given any app
release, its `Info.plist` `KBPSupportedVersions` names the KBP MAJOR(s) it supports. Both therefore
trace to the **same** published standard version (SC-006).
