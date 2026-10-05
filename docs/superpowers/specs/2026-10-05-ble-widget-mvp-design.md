# ZMK BLE 桌面悬浮窗 — MVP 实现设计

- 日期：2026-10-05
- 状态：设计定稿，待实现
- 分支：`feature/ble-status-widget`（从 `master` 新建）
- 前置：探针阶段（step-0 / step-1）已验证"路线 A"可行 —— 详见调研文档
  `2026-10-04-zmk-ble-desktop-widget-design.md`（位于 `feature/gatt-layer-probe` 分支）。
  关键已验证结论（内联，避免悬空引用）：
  - macOS 用户态程序能发现/读取/订阅一个 **BLE HID 键盘上的自定义 128-bit UUID GATT 服务**，且**不影响打字**。
  - 已连接的 BLE HID 设备**不再广播**，必须用 `retrieveConnectedPeripheralsWithServices:` 枚举。
  - ZMK 内部头（`zmk/keymap.h` 等）是 `app PRIVATE`，**不导出给独立 module** → 正式版固件改用 **shield 内代码**形态。

---

## 1. 目标与范围

把原本显示在键盘 OLED 上的状态搬到电脑上的一个**常驻悬浮窗**（位置可拖动、持久化）。

**MVP（本期）**：实时显示
1. 当前最高激活层的**层名**（如 `BASE`/`NAVI`/`SYM`/`ADJ`）
2. 当前激活的**修饰键**（⇧⌃⌥⌘，左右合并）

**非目标（本期不做，payload 预留可扩展）**：电量、输出状态/BLE profile、WPM、
HID 指示灯（Caps/Num/Scroll）、Bongo Cat、开机自启、可配置 UI、设置界面。

**范围依据**：层是 PC 唯一无法自力获取的信息，是项目立身之本；修饰键虽然 macOS
本地（`NSEvent.modifierFlags`）也能拿，但由键盘上报更"以键盘为准"、无需输入监控权限，
且 payload 成本仅 1 字节，故纳入 MVP。其余信息 PC 能自得或非必要，YAGNI 后置。

## 2. 架构总览

三个单元，通过一个明确的接口契约解耦：

```
┌─ 固件（totem shield 内 gatt_status.c，仅 central 半编译）
│    订阅 ZMK 事件 → 读层名/修饰键 → 打包 payload → 自定义 GATT 特征 READ|NOTIFY
│
├─ GATT 接口契约（§3）  ← 固件与 PC 的唯一耦合点；定好后两侧可并行开发
│
└─ PC（Swift + AppKit app）
     BLEClient 连接订阅 → KeyboardStatus 解析 payload → FloatingPanel 悬浮窗渲染
```

## 3. GATT 接口契约（核心，固件↔PC 唯一耦合点）

- **Service UUID**：`AA440AA0-F5ED-4C48-84A1-8062D20D3D55`（复用探针，已验证 macOS 可发现）
- **Characteristic UUID**：`AA440AA1-F5ED-4C48-84A1-8062D20D3D55`，属性 `READ | NOTIFY` + CCC
- **Payload（变长字节，小端）**：

| 字节 | 含义 | 说明 |
|------|------|------|
| `[0]` | 层号 index | `uint8`，调试/备用；PC 主要显示层名 |
| `[1]` | 修饰键 bitmask | `uint8`，标准 HID：`0x01`=LCtrl, `0x02`=LShift, `0x04`=LAlt, `0x08`=LGui, `0x10`=RCtrl, `0x20`=RShift, `0x40`=RAlt, `0x80`=RGui |
| `[2..N]` | 当前层名 | UTF-8，无结尾 `\0`，长度 = 特征值总长 − 2 |

- **更新机制**：层变化 或 修饰键变化 → 固件重算整包 → 与缓存比较 → **有变化才** `bt_gatt_notify`。
- **读取**：PC 连上先 READ 拿初始快照，之后靠 NOTIFY 增量。

## 4. 固件侧设计（totem shield 内）

**落点与编译**
- 新文件：`config/boards/shields/totem/gatt_status.c`
- 新文件：`config/boards/shields/totem/CMakeLists.txt`
  ```cmake
  if(CONFIG_ZMK_TOTEM_GATT_STATUS AND CONFIG_ZMK_SPLIT_ROLE_CENTRAL)
    zephyr_library()
    zephyr_library_include_directories(${CMAKE_SOURCE_DIR}/include)  # 访问 ZMK 内部头
    zephyr_library_sources(gatt_status.c)
  endif()
  ```
  `zephyr_library_include_directories(${CMAKE_SOURCE_DIR}/include)` 是关键——`CMAKE_SOURCE_DIR`=`zmk/app`，
  这行让 shield 代码能 `#include <zmk/keymap.h>`（独立 module 拿不到，shield 可以）。
- 新文件：`config/boards/shields/totem/Kconfig`（shield 级，追加或新建）
  ```kconfig
  config ZMK_TOTEM_GATT_STATUS
      bool "Expose keyboard status (layer+mods) over custom GATT"
      depends on ZMK_BLE
      default n
  ```
  （若 shield 已有 `Kconfig.defconfig`/`Kconfig.shield`，按 ZMK 约定在合适的 Kconfig 文件加此 symbol。）
- 开启：`config/totem.conf` 加 `CONFIG_ZMK_TOTEM_GATT_STATUS=y`
  （`totem.conf` 经 `totem.zmk.yml` 的 keyboard id 对 totem_left/right 生效；settings_reset 不加载，
  且 `depends on ZMK_BLE` + central 守卫双保险，外设半/reset 不编译。）

**GATT 服务**
- `BT_GATT_SERVICE_DEFINE`：primary service `AA440AA0`，characteristic `AA440AA1`
  （`BT_GATT_CHRC_READ | BT_GATT_CHRC_NOTIFY`，`BT_GATT_PERM_READ`），`BT_GATT_CCC`。
- READ callback：`bt_gatt_attr_read(... payload, payload_len ...)` 返回当前快照。

**状态来源（复用 dongle_display 逻辑，均来自 `app/include/zmk/`）**
- 层号 index：`zmk_keymap_highest_layer_active()` → `zmk_keymap_layer_index_t`
- 层名：`zmk_keymap_layer_name(zmk_keymap_layer_index_to_id(idx))` → `const char *`
  （越界返回 `NULL`，未命名返回 `""`；判空用 `name && name[0]`）
- 修饰键：`zmk_hid_get_explicit_mods()` → `zmk_mod_flags_t`(uint8)，位定义见 `<dt-bindings/zmk/modifiers.h>`

**更新与 notify（事件驱动）**
- `ZMK_LISTENER(totem_gatt, cb)` + 订阅：
  - `ZMK_SUBSCRIPTION(totem_gatt, zmk_layer_state_changed)`（`<zmk/events/layer_state_changed.h>`）
  - `ZMK_SUBSCRIPTION(totem_gatt, zmk_keycode_state_changed)`（`<zmk/events/keycode_state_changed.h>`）
    —— **修饰键的驱动源**：`zmk_modifiers_state_changed` 事件存在但是空 stub、无人 raise，不可用；
    故用 keycode 事件，每次在回调里重读 `zmk_hid_get_explicit_mods()`。
- 回调：重算 payload → 与缓存比较 → 变化才 `bt_gatt_notify(NULL, &svc.attrs[1], payload, len)` → 返回 `ZMK_EV_EVENT_BUBBLE`。
- `SYS_INIT(..., APPLICATION, CONFIG_APPLICATION_INIT_PRIORITY)`：开机读一次初值填缓存。

## 5. PC 侧设计（Swift + AppKit）

**组件（职责单一，各一文件）**
- `BLEClient`：CoreBluetooth 连接与订阅
- `KeyboardStatus`：payload 解析 → `{ layerName: String, mods: UInt8, connected: Bool }`
- `FloatingPanel`：NSWindow 悬浮窗
- `AppDelegate`：菜单栏图标 + 生命周期

**BLE 连接（探针经验翻译为 Swift）**
- `CBCentralManager`（主队列 delegate）。
- 发现设备：`retrieveConnectedPeripherals(withServices: [CBUUID(0x1812), CBUUID(AA440AA0)])`；
  按名称含 `TOTEM` 筛选，并记住其 `identifier` 供重连。
- 连接 → `discoverServices([AA440AA0])` → `discoverCharacteristics([AA440AA1])` →
  READ 初值 + `setNotifyValue(true)`。
- `peripheral(_:didUpdateValueFor:error:)` → `KeyboardStatus.parse(data)` → 刷新窗口。
- Swift 原生回调走指定 queue，无需探针那套手动 pump runloop。

**连接管理 / 重连**
- `didDisconnectPeripheral` → 置"未连接"态 → 定时（如每 3s）`retrieveConnectedPeripherals` 重连。
- `centralManagerDidUpdateState` 非 `.poweredOn`（蓝牙关/无权限）→ 菜单栏提示。
- 键盘重上线自动恢复订阅。

**悬浮窗（NSWindow 技术属性）**
- `styleMask = .borderless`；`level = .floating`；`isOpaque = false`；`backgroundColor = .clear`；半透明圆角背景。
- **可拖动**：`isMovableByWindowBackground = true`（borderless 窗口靠此才能拖）；拖动后把 `frame` 存
  `UserDefaults`（key 含屏幕标识），下次启动/换屏恢复；首次启动默认右上角 + 边距。
- **点击穿透 vs 可拖动的冲突与解法**：`ignoresMouseEvents = true`（穿透，不挡下层）会同时让窗口**抓不住、无法拖**。
  二者互斥，故做成**菜单栏开关**：
  - 「锁定/穿透」关闭（默认）：可拖动，但会挡住下层点击；
  - 「锁定/穿透」开启：`ignoresMouseEvents = true`，不挡下层，但不可拖。
  - 两种状态都持久化；拖动请先确保开关处于"未锁定"。
- 不抢焦点：`canBecomeKey = false`；`collectionBehavior = [.canJoinAllSpaces, .stationary]`（切桌面/全屏仍可见）。

**app 形态 / 菜单栏**
- `LSUIElement = true`（Info.plist）：无 dock 图标，纯菜单栏 + 悬浮窗。
- `NSStatusItem`：显示连接状态；菜单项 = 重连 / 锁定·穿透(开关) / 退出。MVP 无设置界面。
- 开机自启：本期不做（后续 `SMAppService`）。

**渲染布局（已选：单行·合并四符）**
```
常驻（未按修饰键）        按住 ⇧ + ⌘
┌─────────────────┐     ┌─────────────────┐
│ NAVI   ⇧ ⌃ ⌥ ⌘ │     │ NAVI  [⇧]⌃ ⌥[⌘]│
└─────────────────┘     └─────────────────┘
```
- 层名 + 四个修饰键符号 ⇧⌃⌥⌘ 同一行。
- 左右合并：`mods & (MOD_LSFT|MOD_RSFT)` → ⇧ 高亮；Ctrl/Alt/Gui 同理。
- 激活=高亮（亮色/实心），未激活=灰显；布局槽位固定不跳动。

## 6. 错误处理与边界

**固件**
- 层名 `NULL`/`""`：payload 层名段留空；由 PC 回退显示 `L{层号}`。
- notify 仅"已订阅且值变化"才发（省流/省电）。
- 仅 central 半编译；外设半、settings_reset 不含此代码。

**PC**
- 键盘未连 Mac / 未发现：窗口"未连接"态 + 定时重连。
- 蓝牙关闭 / 无权限：菜单栏提示，不崩溃。
- payload 长度 < 2：防御性丢弃。
- 层名 UTF-8 解码失败：回退显示层号。

## 7. 测试策略

**固件**：ZMK 无单测框架 → CI 编译通过 + 真机验证。真机**复用探针 `probe.py`**
（从 `feature/gatt-layer-probe` 取来，改 payload 解析为 `[idx][mods][name]`），确认切层/按修饰键时值正确变化。

**PC**：
- `KeyboardStatus.parse` 做 XCTest 单测：给定字节数组 → 断言 `{层名, mods}`（含空层名、超短包、UTF-8 等边界）。
- 悬浮窗手动验证：切层/按修饰键实时刷新；拔连重连；蓝牙关开。

## 8. 实现顺序与里程碑

1. **固件先行**：`gatt_status.c` + `CMakeLists.txt` + Kconfig + `totem.conf` 开启 →
   GitHub Actions 出 `.uf2` → 刷 central（左）半 → 用改版 `probe.py` 验证真实层名+修饰键
   （复用 step-1 的验证闭环）。
2. **PC 分层**：Swift app 骨架（`LSUIElement`）→ `BLEClient` 连接订阅（先命令行打印验证）→
   `KeyboardStatus` 解析 + 单测 → `FloatingPanel` 渲染 → 菜单栏/重连打磨。
3. **端到端联调**：切层/按修饰键 → 悬浮窗实时更新；断连重连；长时间挂机稳定性。

**探针残留清理说明**：本分支基于 `master`，不含探针代码。探针的 `modules/zmk-gatt-layer-probe`、
`zephyr/module.yml`、`totem.conf` 探针开关、`spike/` 仅存在于 `feature/gatt-layer-probe` 分支，
作为历史备查，不并入本分支；`spike/ble-probe/probe.py` 在里程碑 1 按需取来改造复用。

## 9. 关键技术依据（实现参考）

- **层名来源**：编译期由 devicetree `display-name` → `label` → `""`（宏 `LAYER_NAME`，`zmk/app/src/keymap.c`）。
  本键盘 4 层均已有 `label`（`BASE`/`NAVI`/`SYM`/`ADJ`），无需改 keymap。
- **index vs id**：`highest_layer_active()` 返回 index，`layer_name()` 收 id；默认二者相等，
  开启 `CONFIG_ZMK_KEYMAP_LAYER_REORDERING` 时须经 `zmk_keymap_layer_index_to_id()` 转换（故实现一律转换，稳妥）。
- **修饰键事件坑**：`zmk_modifiers_state_changed` 是空 stub（源码零 raise，`behavior_hold_tap.c` 注释佐证）→ 用 `zmk_keycode_state_changed` 驱动。
- **shield vs 独立 module**：独立 module 默认拿不到 `app/include`（CMake target include 不反向传播 + `PRIVATE` 声明）；
  shield 代码加 `zephyr_library_include_directories(${CMAKE_SOURCE_DIR}/include)` 即可访问，且省掉 module 加载机制。
- **UUID 复用**：沿用探针 UUID，payload 从"单字节假层号"升级为 `[idx][mods][name]` 打包格式。
