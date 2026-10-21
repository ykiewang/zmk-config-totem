# Contract: Build Artifacts

**Feature**: 001-keybeacon-support | **Type**: CI/build output contract

This defines what a successful build must produce after the integration. It is the verifiable "interface" between this config repo and anyone retrieving firmware.

## Trigger

- GitHub Actions workflow (`.github/workflows/build.yml`) on push/PR/manual dispatch, OR
- Local `west update && west build`.

## Preconditions

- `config/west.yml` declares the `zmk-keybeacon` project (remote `ykiewang`, `revision: v1.1.3`).
- `config/boards/shields/totem/totem_left.conf` contains `CONFIG_ZMK_KEYBEACON=y`.
- `west update` has fetched both `zmk` and `zmk-keybeacon`.

## Expected outputs (all MUST hold)

| # | Expectation | Maps to |
|---|-------------|---------|
| B1 | Workflow completes successfully (no build error). | SC-002, FR-009 |
| B2 | Firmware artifact produced for `totem_left` (central). | SC-002 |
| B3 | Firmware artifact produced for `totem_right` (peripheral). | SC-002, FR-005 |
| B4 | Firmware artifact produced for `settings_reset`. | SC-002, FR-005 |
| B5 | `keybeacon.c` is compiled into the `totem_left` build. | SC-003, FR-004 |
| B6 | `keybeacon.c` is NOT compiled into `totem_right` or `settings_reset`. | SC-003, FR-005 |
| B7 | No edits were required to module source or shield `CMakeLists.txt`/`Kconfig*`. | SC-004, FR-008 |

## Verification

- B1–B4: observe the Actions run / local build exit status and the produced `*.uf2` set.
- B5–B6: inspect build logs for `keybeacon.c` compilation under each target's build directory, or confirm the cmake guard outcome per target.
- B7: `git diff` touches only `config/west.yml` and `config/boards/shields/totem/totem_left.conf`.
