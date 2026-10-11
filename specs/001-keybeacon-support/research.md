# Phase 0 Research: Totem KeyBeacon Support

**Feature**: 001-keybeacon-support | **Date**: 2026-10-11

All technical unknowns from the plan's Technical Context are resolved below. Sources: the zmk-keybeacon `GETTING-STARTED.md` and repo tree (`main`), and the current Totem config files.

## R1. Module dependency declaration (west.yml)

- **Decision**: Add the `ykiewang` remote and a `zmk-keybeacon` project entry to the existing `config/west.yml`, leaving the `zmkfirmware`/`zmk` project and `self` untouched. Set `revision: main`.
- **Rationale**: Totem already has a manifest (Scenario B in the guide — "additions only"). The module's `zephyr/module.yml` auto-registers its CMake/Kconfig, so only a remote + project entry is required. `import: app/west.yml` on the `zmk` project already pulls in all transitive Zephyr/ZMK dependencies.
- **Resulting manifest**:
  ```yaml
  manifest:
    remotes:
      - name: zmkfirmware
        url-base: https://github.com/zmkfirmware
      - name: ykiewang
        url-base: https://github.com/ykiewang
    projects:
      - name: zmk
        remote: zmkfirmware
        revision: main
        import: app/west.yml
      - name: zmk-keybeacon
        remote: ykiewang
        revision: main
    self:
      path: config
  ```
- **Alternatives considered**:
  - *Pin to `v1.0.0`* (guide's recommendation for reproducibility) — rejected per explicit user request to track `main`.
  - *Vendor/copy the module into the repo* — rejected; the guide explicitly says no files are copied and west fetches the module.

## R2. Revision `main` vs pinned tag — availability and tradeoff

- **Decision**: Use `revision: main`.
- **Rationale**: The `main` branch exists and is the module's default branch (confirmed via the repo tree at `main`, which contains `Kconfig.keybeacon`, `keybeacon.c`, `keybeacon.cmake`, `CMakeLists.txt`, `zephyr/module.yml`). The user explicitly asked to "pull the latest from main."
- **Tradeoff / risk**: The guide calls pinning a released semver tag a "critical rule … never `main`" for reproducible builds. Tracking `main` means a future `west update` can fetch changed module code, so two builds from the same config can differ. Accepted and documented (spec FR-002, plan Complexity Tracking). Easily reversible: change one `revision:` line to a tag later (FR-011).
- **Alternatives considered**: `v1.0.0` tag (reproducible) — rejected only because it contradicts the instruction.

## R3. Enabling symbol and placement (central-only)

- **Decision**: Add `CONFIG_ZMK_KEYBEACON=y` to `config/boards/shields/totem/totem_left.conf`.
- **Rationale**: The guide: "In the `.conf` that controls the central target, add `CONFIG_ZMK_KEYBEACON=y`" and "For a split keyboard this goes in the central half's conf only." In Totem, `Kconfig.defconfig` sets `CONFIG_ZMK_SPLIT_ROLE_CENTRAL=y` for `SHIELD_TOTEM_LEFT`, so the left half is the central target and `totem_left.conf` is its conf file (currently empty).
- **Alternatives considered**:
  - *Put it in shared `config/totem.conf`* — functionally safe because the module's cmake guard also requires `CONFIG_ZMK_SPLIT_ROLE_CENTRAL`, so the right/settings_reset targets would still compile it out. Rejected as less precise than the guide's "central half's conf only" guidance; keeping it in `totem_left.conf` documents intent clearly.
  - *Put it in `totem_right.conf`* — wrong; the right half is the peripheral and has no host link.

## R4. Scoping to central role only (peripheral/reset compile-out)

- **Decision**: Rely on the module's built-in cmake guard; make no changes to shield `CMakeLists.txt` or `Kconfig*`.
- **Rationale**: The module guards its source with `if(CONFIG_ZMK_KEYBEACON AND CONFIG_ZMK_BLE AND CONFIG_ZMK_SPLIT_ROLE_CENTRAL)`. The right half lacks `CONFIG_ZMK_SPLIT_ROLE_CENTRAL`; the `settings_reset` target is a bare reset image without the shield's central role — both silently exclude `keybeacon.c`. The guide confirms no `include(...)`/`rsource ...` lines are needed because `zephyr/module.yml` injects the entry points.
- **Alternatives considered**: Manually gating via shield files — rejected; redundant and contrary to the guide (FR-008).

## R5. BLE prerequisite

- **Decision**: No action needed.
- **Rationale**: KeyBeacon requires `CONFIG_ZMK_BLE=y`. The `xiao_ble` board (nRF52840) is a BLE board and sets this automatically, as the guide notes for SEEED XIAO BLE. Totem's `build.yaml` uses `board: xiao_ble//zmk` for all targets.
- **Alternatives considered**: Explicitly forcing `CONFIG_ZMK_BLE=y` — unnecessary; already implied by the board.

## R6. Layer names (human-readable labels)

- **Decision**: No keymap changes.
- **Rationale**: The "empty layer name (2-byte payload)" pitfall only occurs when layers lack a `label`. Totem's `config/totem.keymap` already defines `label = "BASE"`, `"NAVI"`, `"SYM"`, `"ADJ"`, so the companion receives proper names (FR-010, SC-005).
- **Alternatives considered**: Adding/renaming labels — not required; existing labels are already present and sensible.

## R7. Build & CI impact

- **Decision**: Leave `build.yaml` and `.github/workflows/build.yml` unchanged.
- **Rationale**: The workflow uses `zmkfirmware/zmk/.github/workflows/build-user-config.yml@main`, which runs `west update` (fetching the newly declared module) and builds every target in `build.yaml` (left, right, settings_reset). No matrix or dependency changes are needed; artifacts and the drag-and-drop UF2 flashing flow are unchanged (FR-009, SC-002).
- **Alternatives considered**: Adding a dedicated job or changing targets — unnecessary.

## R8. Functional verification method

- **Decision**: Verify with a BLE probe using `bleak` and/or the `BleWidget.dmg` macOS app.
- **Rationale**: The guide offers both; note that `tools/probe.py` is **not present** in the module repo tree, so a probe script must be written locally from the guide (or the macOS app used instead). The keyboard stops advertising once connected, so the consumer must enumerate already-connected peripherals rather than scan.
- **Alternatives considered**: Relying solely on the app — fine, but a probe is useful for headless confirmation. Either satisfies SC-001/SC-005.

## R9. Module `main` compatibility with ZMK `main` (implementation finding)

- **Decision**: Keep `revision: main` (R2) but disable the KBP 1.1 sub-options `CONFIG_ZMK_KEYBEACON_CONNECTIVITY` and `CONFIG_ZMK_KEYBEACON_BATTERY` (both default `y` upstream) in the central conf.
- **Rationale**: CI evidence (a prior `feat/keybeacon-v1.1.3` run) and inspection of the module at `main` (HEAD `76378f42`) show `keybeacon.c:249` calls `zmk_endpoints_selected()`, which was removed from ZMK `main` (renamed `zmk_endpoint_get_selected()`), causing `error: invalid initializer`. That call is the **only** occurrence and is wrapped entirely in `#if IS_ENABLED(CONFIG_ZMK_KEYBEACON_CONNECTIVITY)` (lines 187–279). The core layer/modifier path (`build_payload`, `keybeacon_cb`) does not use it. Disabling the two 1.1 sub-options compiles out the broken/out-of-scope code while preserving the feature required by FR-006.
- **Scope impact**: None against this spec — US1 only requires active layer name, layer index, and modifier state, all delivered by the core characteristic. Connectivity/battery characteristics were never in scope.
- **Alternatives considered**:
  - *Pin `revision: v1.0.0`* (predates the Connectivity feature, builds clean) — rejected because it contradicts the explicit `main` request; disabling the sub-options achieves a green `main` build without pinning.
  - *Patch the module* — rejected; violates FR-008 (no module source edits) and the upstream fix is not ours to make here.
  - *Leave sub-options at default `y`* — rejected; guaranteed build failure against ZMK `main`.

## Resolved unknowns summary

| Item | Resolution |
|------|-----------|
| Where to declare the module | `config/west.yml` (ykiewang remote + zmk-keybeacon project) |
| Revision | `main` (explicit request; reproducibility tradeoff documented) |
| Enable symbol | `CONFIG_ZMK_KEYBEACON=y` |
| Where to enable | `config/boards/shields/totem/totem_left.conf` (central) |
| Central-only scoping | Module cmake guard; no shield edits |
| BLE prerequisite | Satisfied automatically by `xiao_ble` |
| Layer names | Already labeled in keymap; no change |
| CI/build | Unchanged; `west update` fetches module |
| Verification | `bleak` probe (written locally) and/or BleWidget app |

No `NEEDS CLARIFICATION` items remain.
