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



<a id="en"></a>
## BLE STATUS WIDGET (macOS)

**English** · [中文](#zh)

An optional desktop companion that shows the keyboard's **live active layer** and
**modifiers** in an always-on-top floating panel, driven over a custom BLE GATT
characteristic from the central (left) half. It works with **any ZMK keyboard that
implements the KeyBeacon contract**, not just Totem. See
[`specs/001-ble-status-widget/`](/specs/001-ble-status-widget) for the full design
and the frozen interface contract, and
[`specs/002-multi-keyboard-support/`](/specs/002-multi-keyboard-support) for the
multi-keyboard decoupling.

### firmware

- Enabled by `CONFIG_ZMK_KEYBEACON` (already set in
  [`config/totem.conf`](/config/totem.conf)); compiled on the **central (left) role
  only** and gated on BLE, so the right half and `settings_reset` are unaffected.
- The shared logic ships as a portable **KeyBeacon kit**
  ([`config/keybeacon_kit/`](/config/keybeacon_kit)); its `README.md` is a porting
  guide for adding the feature to another keyboard without editing the shared logic.
- Publishes a notify-on-change snapshot `[layer_index][modifiers][layer_name]`.
  Nothing is sent while the state is unchanged, so there is no idle traffic.
- Build and flash it exactly as above — the feature rides along in
  `totem_left`.

### macOS app

The desktop app, the **KeyBeacon Protocol (KBP)** standard, and the conformance kit now live in
their own repository: **<https://github.com/ykiewang/keybeacon>**.

- **Download & run**: grab the latest `BleWidget-<version>.dmg`/`.zip` from the app repo's
  [Releases](https://github.com/ykiewang/keybeacon/releases) — no terminal or build tools needed.
  (The first builds are unsigned; the app repo's README has the one-time Gatekeeper first-open step.)
- **Protocol**: the authoritative, versioned KBP standard is `protocol/` in the app repo; this
  firmware pins an exact version under [`protocol-pinned/`](/protocol-pinned) and CI verifies the
  snapshot has not diverged from the published tag.
- **Make another keyboard conform**: use the app repo's `conformance/` kit (guide + checklist +
  self-test tool).

The panel shows the active layer name plus four merged modifier indicators (⇧ ⌃ ⌥ ⌘). Full app
usage — menu-bar controls, lock / click-through, and the multi-keyboard picker — is documented in
the app repo.

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

<a id="zh"></a>
## BLE 状态悬浮窗 (macOS)

[English](#en) · **中文**

一个可选的桌面伴侣:在置顶悬浮窗中实时显示键盘的**当前层**与**修饰键**,数据由中央
(左)半通过自定义 BLE GATT 特征推送。它适用于**任何实现 KeyBeacon 契约的 ZMK 键盘**,
而不仅限于 Totem。完整设计与冻结的接口契约见
[`specs/001-ble-status-widget/`](/specs/001-ble-status-widget),多键盘解耦见
[`specs/002-multi-keyboard-support/`](/specs/002-multi-keyboard-support)。

### 固件

- 由 `CONFIG_ZMK_KEYBEACON` 开关控制(已在
  [`config/totem.conf`](/config/totem.conf) 中启用);**仅在中央(左)角色**编译并依赖
  BLE,因此右半与 `settings_reset` 不受影响。
- 共享逻辑以可移植的 **KeyBeacon 套件**([`config/keybeacon_kit/`](/config/keybeacon_kit))
  形式提供;其 `README.md` 是移植指南,无需改动共享逻辑即可将该特性加到别的键盘上。
- 推送「仅变化才通知」的快照 `[层索引][修饰位][层名]`;状态不变时不发送,无空闲流量。
- 构建与烧录方式同上 —— 该特性随 `totem_left` 一起编入。

### macOS 应用

桌面应用、**KeyBeacon 协议(KBP)** 标准与一致性套件现已迁出到独立仓库:
**<https://github.com/ykiewang/keybeacon>**。

- **下载即用**:到应用仓的 [Releases](https://github.com/ykiewang/keybeacon/releases) 下载最新
  `BleWidget-<版本>.dmg`/`.zip`,无需终端或构建工具。(首批为未签名构建,应用仓 README 有
  一次性的 Gatekeeper 首次打开步骤。)
- **协议**:权威、带版本的 KBP 标准为应用仓的 `protocol/`;本固件在
  [`protocol-pinned/`](/protocol-pinned) 固定一个确切版本,CI 校验该快照未偏离已发布的标签。
- **让别的键盘兼容**:使用应用仓的 `conformance/` 套件(指南 + 清单 + 自测工具)。

面板显示当前层名,以及四个合并后的修饰指示(⇧ ⌃ ⌥ ⌘)。应用的完整用法 —— 菜单栏控制、
锁定 / 穿透、多键盘选择 —— 记录在应用仓中。

### 真机探针(可选)

[`tools/probe.py`](/tools/probe.py) 可在不启动应用的情况下验证固件。macOS 上它用
CoreBluetooth 查找**已连接**的键盘(处于连接态的 BLE HID 设备会停止广播,普通扫描找不到),
并逐条打印快照的 `layer_index` / `layer_name` / `mods`:

```bash
python3 -m venv tools/.venv
tools/.venv/bin/pip install bleak        # macOS 上会一并装好 pyobjc
tools/.venv/bin/python tools/probe.py
```