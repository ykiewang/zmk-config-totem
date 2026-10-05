# Development Commands

This repo contains no build scripts of its own — it is consumed by ZMK's build system.

## CI build (primary workflow)

`.github/workflows/build.yml` delegates every build to the upstream reusable workflow
`zmkfirmware/zmk/.github/workflows/build-user-config.yml@main`. It triggers on
`push`, `pull_request`, and `workflow_dispatch`.

What gets built is controlled by `build.yaml`:

```yaml
include:
  - board: xiao_ble//zmk
    shield: totem_left
  - board: xiao_ble//zmk
    shield: totem_right
  - board: xiao_ble//zmk
    shield: settings_reset
```

To build firmware: commit and push. Then on GitHub → **Actions** → latest run →
download the `firmware` artifact (`firmware.zip`), which contains:

- `totem_left-seeeduino_xiao_ble-zmk.uf2`
- `totem_right-seeeduino_xiao_ble-zmk.uf2`

Add or change a target by editing `build.yaml` (one `board`+`shield` pair per entry).

## Local build (west)

Only needed if you want to iterate without CI. Requires the `west` toolchain and ZMK
dependencies installed.

```bash
# One-time: init and update the west workspace (uses config/west.yml manifest)
west init -l config
west update

# Build both halves
west build -s zmk/app -d build/left  -b xiao_ble -- -DZMK_CONFIG="$PWD/config" -DSHIELD=totem_left
west build -s zmk/app -d build/right -b xiao_ble -- -DZMK_CONFIG="$PWD/config" -DSHIELD=totem_right
```

Output `.uf2` files land under `build/<halve>/zephyr/zmk.uf2`.

`config/west.yml` pins ZMK to `zmkfirmware/zmk` revision `main`. Note the pin is a
moving target — an upstream change can break a build that previously passed.

## Flash to keyboard

1. Connect one half to the PC over USB.
2. Press the reset button twice quickly — the half mounts as a USB mass-storage device.
3. Drag the matching `.uf2` onto the drive.
4. Repeat for the other half.

The `settings_reset` firmware (kept in `build.yaml`) is used to wipe stored
Bluetooth pairings when a half misbehaves.

## Kconfig / config precedence

ZMK merges several `.conf` files, in this repo:

- `config/totem.conf` — applies to the whole config (currently just `CONFIG_ZMK_USB_LOGGING=n`)
- `config/boards/shields/totem/totem.conf` — shield-wide (empty)
- `config/boards/shields/totem/totem_left.conf` / `totem_right.conf` — per half (empty)

Put shared overrides in `config/totem.conf`; only split-specific ones need to go into
the per-half files.
