# Architecture

## Repository layout

```
config/
  totem.keymap                     # the user's keymap (layers) — edit this
  totem.conf                       # global Kconfig overrides
  west.yml                         # west manifest: pulls zmkfirmware/zmk@main
  boards/shields/totem/            # the "totem" shield definition
    totem.dtsi                     # shared: kscan matrix + matrix transform
    totem_left.overlay             # left-half column GPIOs
    totem_right.overlay            # right-half column GPIOs (+ col-offset)
    Kconfig.shield                 # SHIELD_TOTEM_LEFT / _RIGHT symbols
    Kconfig.defconfig              # split + central-role defaults
    totem.zmk.yml                  # shield metadata (requires seeeduino_xiao_ble)
    totem.conf / _left.conf / _right.conf   # Kconfig (currently empty)
build.yaml                         # CI build matrix
.github/workflows/build.yml        # delegates to ZMK reusable workflow
docs/                              # images + agent docs
```

## Shield model

TOTEM is one shield (`id: totem`) with two siblings, `totem_left` and `totem_right`,
both targeting the `seeeduino_xiao_ble` board. `totem.dtsi` holds everything both
halves share; each `.overlay` includes it and then specializes.

`totem.zmk.yml` declares `requires: [seeeduino_xiao_ble]` and lists the siblings —
this is the metadata ZMK's board/shield tooling reads.

## Matrix and transform (the part that is easy to get wrong)

The physical matrix is 4 rows × 10 columns, wired on the XIAO's `xiao_d` GPIOs:

- `totem.dtsi` defines `kscan0` (`zmk,kscan-gpio-matrix`, `diode-direction = col2row`)
  with the four shared **row** GPIOs (`xiao_d 0..3`).
- Each overlay defines the five **column** GPIOs for its half. The right half reverses
  its column order (`8,9,10,5,4` vs. left's `4,5,10,9,8`).
- `default_transform` maps matrix rows/cols to a linear key index. It uses a custom
  `RC(r,c)` `map` because the bottom row is offset (thumbs). The right half sets
  `col-offset = <5>` so its columns land in indices 5–9.

So the key index order is fixed by `totem.dtsi`; the keymap's `bindings` list must
follow that same order (row 0 → row 1 → row 2 → bottom/thumb row, left half then right).

## Keymap model (`config/totem.keymap`)

Standard ZMK devicetree keymap:

- **Layers** are numbered by `#define`: `BASE 0`, `NAV 1`, `SYM 2`, `ADJ 3`.
- **Combos**: `combo_esc` fires `ESC` when key positions 0+1 are pressed within 50ms.
- **Macros**: `gif` types `G` `I` `F`.
- **Behaviors used**: `&kp` (key press), `&mt` (hold-mod / tap), `&lt` (layer-tap),
  `&bt` (Bluetooth), `&trans` (transparent). Reference keycodes at
  https://zmk.dev/docs/codes/.
- Layer names are set via `label = "BASE"/"NAVI"/"SYM"/"ADJ"` on each layer node.

Note the ASCII-art comments above each layer show the intended physical layout; keep
them in sync with the `bindings` when editing, as they are the human-readable spec.

## Split roles

`Kconfig.defconfig` sets `ZMK_SPLIT=y` for both halves and
`ZMK_SPLIT_ROLE_CENTRAL=y` (plus keyboard name `TOTEM`) **only for the left half**.
The left half is the central: it holds the Bluetooth profiles and pairs with the host.

## Related / external

- Hardware & build guide: https://github.com/GEIGEIGEIST/totem
- QMK equivalent: `GEIGEIGEIST/qmk-config-totem`
- There is a sibling design doc, `2026-10-04-zmk-ble-desktop-widget-design.md`, proposing
  a custom GATT service to mirror keyboard state (active layer / modifiers) to a desktop
  floating window. That is a *design proposal only* — no code for it exists in this repo
  yet. Implementation would live in a separate project (see the doc's "待定项").
