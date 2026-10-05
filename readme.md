<picture>
  <source media="(prefers-color-scheme: dark)" srcset="/docs/images/TOTEM_logo_dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="/docs/images/TOTEM_logo_bright.svg">
  <img alt="TOTEM logo font" src="/docs/images/TOTEM_logo_bright.svg">
</picture>

# ZMK CONFIG FOR THE TOTEM SPLIT KEYBOARD

[Here](https://github.com/GEIGEIGEIST/totem) you can find the hardware files and build guide.\
[Here](https://github.com/GEIGEIGEIST/qmk-config-totem) you can find the QMK config for the TOTEM.

TOTEM is a 38 key column-staggered split keyboard running [ZMK](https://zmk.dev/) or [QMK](https://docs.qmk.fm/). It's meant to be used with a SEEED XIAO BLE or RP2040.


![TOTEM layout](/docs/images/TOTEM_layout.svg)



## HOW TO USE

- fork this repo
- `git clone` your repo, to create a local copy on your PC (you can use the [command line](https://www.atlassian.com/git/tutorials) or [github desktop](https://desktop.github.com/))
- adjust the totem.keymap file (find all the keycodes on [the zmk docs pages](https://zmk.dev/docs/codes/))
- `git push` your repo to your fork
- on the GitHub page of your fork navigate to "Actions"
- scroll down and unzip the `firmware.zip` archive that contains the latest firmware
- connect the left half of the TOTEM to your PC, press reset twice
- the keyboard should now appear as a mass storage device
- drag'n'drop the `totem_left-seeeduino_xiao_ble-zmk.uf2` file from the archive onto the storage device
- repeat this process with the right half and the `totem_right-seeeduino_xiao_ble-zmk.uf2` file.



## BLE STATUS WIDGET (macOS)

An optional desktop companion that shows the keyboard's **live active layer** and
**modifiers** in an always-on-top floating panel, driven over a custom BLE GATT
characteristic from the central (left) half. See
[`specs/001-ble-status-widget/`](/specs/001-ble-status-widget) for the full design
and the frozen interface contract.

### firmware

- Enabled by `CONFIG_ZMK_TOTEM_GATT_STATUS` (already set in
  [`config/totem.conf`](/config/totem.conf)); compiled on the **central (left) role
  only** and gated on BLE, so the right half and `settings_reset` are unaffected.
- Publishes a notify-on-change snapshot `[layer_index][modifiers][layer_name]`.
  Nothing is sent while the state is unchanged, so there is no idle traffic.
- Build and flash it exactly as above — the feature rides along in
  `totem_left`.

### macOS app

A menu-bar app (no Dock icon) lives under [`host/macos/`](/host/macos):

```bash
cd host/macos
swift build -c release
.build/release/BleWidget
```

The panel shows the active layer name plus four fixed modifier indicators
(**⇧ Shift · ⌃ Control · ⌥ Option · ⌘ Command**); the left and right halves of each
modifier are merged into one indicator, and the slots never reflow.

Menu-bar controls:

| item | shortcut | action |
|------|----------|--------|
| 重连 (Reconnect) | `r` | re-run discovery and reconnect |
| 锁定 / 穿透 (Lock / click-through) | `l` | toggle the panel between draggable and click-through |
| 退出 (Quit) | `q` | quit the app |

- **unlocked** (default): drag the panel anywhere; its position is remembered per
  screen and restored on the next launch.
- **locked**: the panel becomes click-through (mouse events pass to whatever is
  beneath it) and can no longer be dragged. The lock state persists across restarts.
- The menu-bar icon reflects the connection state (connected / connecting / not
  connected / Bluetooth unavailable) and the app reconnects on its own when the
  keyboard reappears.

### on-device probe (optional)

[`tools/probe.py`](/tools/probe.py) checks the firmware without the app. On macOS it
uses CoreBluetooth to find the already-connected keyboard (an active BLE HID device
stops advertising, so a plain scan won't find it) and prints each snapshot as
`layer_index` / `layer_name` / `mods`:

```bash
python3 -m venv tools/.venv
tools/.venv/bin/pip install bleak        # also pulls in pyobjc on macOS
tools/.venv/bin/python tools/probe.py
```