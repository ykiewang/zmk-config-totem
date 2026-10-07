# Implementation Plan: ZMK Module Distribution

**Branch**: `005-zmk-module-distribution` | **Date**: 2026-10-07 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/005-zmk-module-distribution/spec.md`

## Summary

Extract `config/keybeacon_kit/` from the zmk-config-totem firmware repo into a standalone GitHub repository (`github.com/ykiewang/zmk-keybeacon`) that implements the Zephyr module interface (`zephyr/module.yml`). Once published, any ZMK user can reference the module in their `west.yml` and enable the feature with a single `CONFIG_ZMK_KEYBEACON=y` line in their `.conf` — no file copying, no `rsource`, no `include()` required. The Totem shield in this repo is updated to consume the module (its `include()`/`rsource` wiring removed) and serves as the reference integration.

## Technical Context

**Language/Version**: C (ZMK/Zephyr, unchanged); CMake; Kconfig; YAML (west manifest, `zephyr/module.yml`); Bash (migration/verification scripts); Markdown (docs).

**Primary Dependencies**: Zephyr module system (native to ZMK build environment, no new tooling); west (already required by all ZMK users); GitHub Actions (ZMK's existing CI template already supports west manifests with external projects).

**Storage**: N/A — no runtime storage. The module repo contains only firmware source files and module metadata. The firmware repo pins the module by adding a `zmk-keybeacon` entry (semver tag) to its `config/west.yml`.

**Testing**: Firmware build CI (`build.yaml`) is the primary gate — the module must compile cleanly for all existing Totem targets. On-device: existing `probe.py` and conformance tool validate runtime behavior is unchanged.

**Target Platform**: ZMK on Zephyr (embedded, SEEED XIAO BLE reference board). Module build environment: GitHub Actions macOS/Linux runners via ZMK's standard workflow.

**Project Type**: Firmware module (Zephyr external module, independent Git repo) + firmware repo update (west manifest wiring + shield path update).

**Performance Goals**: Zero runtime behavior change — firmware on-air traffic, power draw, and GATT payload are unchanged. Build time impact is negligible (one small `.c` file added conditionally).

**Constraints**:
- `keybeacon.c`, `keybeacon.cmake`, and `Kconfig.keybeacon` content MUST NOT change — only packaging and path.
- The cmake guard (`CONFIG_ZMK_KEYBEACON AND CONFIG_ZMK_BLE AND CONFIG_ZMK_SPLIT_ROLE_CENTRAL`) MUST be preserved verbatim.
- After migration, `config/keybeacon_kit/` MUST be removed from the firmware repo; no dual-path build.
- The module MUST be versioned with a semver tag (`v1.0.0`) before the firmware repo pins it.
- Totem shield files that reference `keybeacon_kit/` paths (CMakeLists.txt, Kconfig.defconfig) MUST have those `include()`/`rsource` lines **removed** — the module auto-injects cmake and Kconfig via `zephyr/module.yml`; no path re-pointing is needed.
- ZMK's GitHub Actions CI must continue to pass for all `build.yaml` targets.

**Scale/Scope**: One module repo (3 source files + module metadata), one firmware repo update (remove wiring in 2 shield files + `config/west.yml` edit), one documentation update (`GETTING-STARTED.md`).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|-----------|------|--------|
| I. Interface Contract First | The GATT wire contract (service/char UUID, payload layout) is completely unchanged. This feature is packaging/distribution only — no contract version bump needed or taken. | PASS |
| II. Keyboard as Source of Truth | No change to reported state or ZMK API calls. `keybeacon.c` is moved, not modified. | PASS |
| III. Shield-Scoped, Minimal Footprint | The cmake guard (`CONFIG_ZMK_KEYBEACON AND CONFIG_ZMK_BLE AND CONFIG_ZMK_SPLIT_ROLE_CENTRAL`) is preserved verbatim. peripheral and settings_reset targets continue to exclude `keybeacon.c`. The Kconfig `depends on ZMK_BLE` guard is preserved. Zero on-air traffic or power change. | PASS |
| IV. MVP Discipline (YAGNI) | Bounded scope: extract kit → publish module → update Totem wiring. Explicit non-goals: module CI, auto-update tooling, multi-keyboard variant support. Semver reserved for future protocol changes, not pre-built here. | PASS |
| V. Hardware-Verified by CI | All existing `build.yaml` targets must build cleanly after the path change. Module integration is validated by the same build CI that currently validates `keybeacon_kit/` inline. On-device probe.py validation confirms runtime behavior is unchanged. | PASS |

No violations. **Complexity Tracking not required.**

**Post-Phase-1 re-check**: Re-evaluated after `research.md`, `data-model.md`, `contracts/`, and `quickstart.md`. The design keeps all cmake/Kconfig guards intact, removes the in-repo copy in favor of a single canonical source, and requires no changes to `keybeacon.c`. Gate remains **PASS**.

## Project Structure

### Documentation (this feature)

```text
specs/005-zmk-module-distribution/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── module-interface.md   # zephyr/module.yml contract + west.yml pinning convention
├── checklists/
│   └── requirements.md  # (from /speckit-specify)
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (two repositories)

**Module repository — NEW: `github.com/ykiewang/zmk-keybeacon`**:

```text
zmk-keybeacon/
├── zephyr/
│   └── module.yml          # Zephyr module declaration (cmake + Kconfig entry points)
├── keybeacon.c             # moved from config/keybeacon_kit/keybeacon.c (unchanged)
├── keybeacon.cmake         # moved from config/keybeacon_kit/keybeacon.cmake (path-adjusted)
├── Kconfig.keybeacon       # moved from config/keybeacon_kit/Kconfig.keybeacon (unchanged)
├── README.md               # module-level integration guide
└── CHANGELOG.md            # semver changelog (v1.0.0 initial release)
```

**Firmware repository — THIS repo (`zmk-config-totem`)**:

```text
zmk-config-totem/
├── config/
│   ├── west.yml                # EDITED: append the zmk-keybeacon project (ZMK manifest lives in config/)
│   ├── keybeacon_kit/          # SPLIT to module repo (history preserved) → then REMOVED from this repo
│   └── boards/shields/totem/
│       ├── CMakeLists.txt      # REMOVED: include() no longer needed (module auto-injects cmake)
│       └── Kconfig.defconfig   # EDITED: remove the rsource line (module auto-injects Kconfig)
└── scripts/migrate/
    ├── split-keybeacon-module.sh    # NEW: history-preserving split → module repo tree
    └── README-keybeacon-module.md   # NEW: manual push/tag steps (maintainer action)
```

**Structure Decision**: The module repo is the authoritative source for the kit files. The firmware repo appends a `zmk-keybeacon` entry to its `config/west.yml` (ZMK's manifest lives in `config/`, pinned by tag) and removes the in-repo `keybeacon_kit/` copy (after it is split out, preserving history). Totem shield wiring has its `include()` line (`CMakeLists.txt`, removed since the file is no longer needed) and `rsource` line (`Kconfig.defconfig`) **removed entirely** — the module auto-injects cmake and Kconfig via `zephyr/module.yml`, so no path re-pointing is needed. `GETTING-STARTED.md` is updated so step 1 becomes "add to `config/west.yml`" rather than "copy directory".

## Complexity Tracking

> No constitution violations — table intentionally omitted.
