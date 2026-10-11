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



## KEYBEACON (LAYER + MODIFIER STATUS OVER BLE)

This config enables [zmk-keybeacon](https://github.com/ykiewang/zmk-keybeacon): the
central (left) half reports the active layer (name + index) and modifier state over
its host BLE connection, so a macOS companion app / BLE probe can show your current
layer and mods.

- Enabled on the central half only via `CONFIG_ZMK_KEYBEACON=y` in
  `config/boards/shields/totem/totem_left.conf`; the right half and `settings_reset`
  compile it out automatically.
- The module is pinned at `revision: v1.1.3` in `config/west.yml` for reproducible
  builds. To move to a newer release, change that single `revision:` line to the new
  tag and let the build run again.
- The KBP 1.1 `CONNECTIVITY`/`BATTERY` sub-characteristics are intentionally disabled
  (they are out of scope and the Connectivity path does not build against ZMK `main`).



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