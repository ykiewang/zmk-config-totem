# 方案：ZMK 键盘状态在电脑上的悬浮窗显示

- 日期：2026-10-04
- 状态：方案草案（探针待执行）
- 目标仓库（PC 侧与探针脚本）：`zmk-dongle-display`
- 键盘配置仓库：`GEIGEIGEIST/zmk-config-totem`

---

## 1. 目标

把原本显示在键盘 OLED 上的状态（当前最高层名、激活的修饰键），改为显示
在电脑上的一个**置顶悬浮窗口**里。

MVP 范围（第一版）：**当前最高层名 + 激活修饰键（Shift/Ctrl/Alt/Gui）**。
WPM、输出状态、外设电量等留待后续。

## 2. 使用场景与约束

- **无 dongle**：键盘（Totem，分体）的中央半直接连电脑，没有独立接收器。
- **BLE 为主**：平时以蓝牙连接电脑，键盘在系统里表现为一个普通 BLE HID 键盘。
- **平台**：先在 macOS（本机 CoreBluetooth）验证。
- **硬件**：Totem 分体键盘，配置来自 `GEIGEIGEIST/zmk-config-totem`。

## 3. 核心技术现实（决定整个方案的关键点）

屏幕上那些内容（层名、修饰键、WPM、电量）**目前只存在于键盘固件里，从未发给电脑**。
电脑把键盘当标准 HID 键盘，只能拿到按键与 CapsLock/NumLock 这类标准指示灯。

因此"把屏幕搬到电脑"本质上是两件事：

1. **固件侧**：让键盘把状态**广播给电脑**（需要改/新增固件）。
2. **PC 侧**：写一个程序**接收并渲染**成悬浮窗。

- **HID**：键盘本来就在用的、只送按键的标准协议，**送不了"层名"**。
- **GATT**：BLE 设备向电脑暴露自定义数据的通用机制（Service + Characteristic
  + Notify/Read）。我们正是要在 HID 之外**叠加**一个自定义 GATT 服务。

## 4. 路线选择

### 路线 A（选定）：自定义 GATT 服务 + PC 端订阅
- 固件：新增一个独立 ZMK module，注册自定义 128-bit UUID 的 GATT 服务，含一个
  特征（`READ | NOTIFY`）。订阅 ZMK 事件（`zmk_layer_state_changed`、
  `zmk_modifiers_state_changed`、`zmk_keycode_state_changed`），把状态打包发送。
- PC：Python + `bleak` 订阅该特征，Qt(PySide6) 悬浮窗渲染。
- 优点：链路解耦、固件改动小、状态变化才推送、与 HID 共存不影响打字。
- 风险：macOS 上"已被系统当 HID 的键盘"能否被用户态程序再连 GATT（见第 6 节）。

### 路线 B（否决）：复用 ZMK Studio 的 RPC 通道
- 消息定义在 `zmk-studio-messages` 仓库，需改官方协议、跟上游同步，**过重**。

### 路线 C（否决）：不改固件，PC 端从按键推断
- 电脑看不到"层"这个概念，固件不发永远不知道，**不可行**。

## 5. 关键先例：`maxistar/zmk-gatt-layer`

一个已被验证可编译可跑的 PoC，功能 = **把"当前激活层号"一个整数通过自定义 GATT
发给电脑**。

**固件侧**（`zmk-gatt-scalar` 模块，<100 行）：
- `BT_GATT_SERVICE_DEFINE` 注册服务，UUID `12341234-1234-5678-7856-123412345678`；
- 一个特征 `...5679`，属性 `READ | NOTIFY`，暴露一个 32-bit 整数（层号）；
- 订阅 `zmk_layer_state_changed`，层变则写值并（若已订阅）`bt_gatt_notify`；
- `SYS_INIT` 开机时读一次当前层号作初值；
- 特征权限仅 `BT_GATT_PERM_READ`（普通读，**不要求配对/加密**）——这正是
  macOS 上能与系统 HID 共存的可行原因。

**PC 侧**（Rust CLI，`btleplug` + tokio）：
- 扫描 → 按广播名或 service UUID 找键盘 → 连接 → 发现服务 → 定位特征；
- **每 500ms 轮询读一次**（注意：实际用轮询，不是 notify），值变才打印。

**对本项目的意义**：它给出了可直接照抄的最小骨架（GATT 服务定义、事件订阅、
小端编码、BLE 客户端连接读取）。

**它的局限**：
- 只是 PoC，**未测 macOS**，未讨论 HID 共存；
- **只传层号一个整数**，不含层名、修饰键、WPM；
- 客户端只有 Rust 命令行版，无 Python/悬浮窗。

## 6. 不确定性 / 探针要回答的问题

1. 这台 Mac 上，键盘当 HID 用的同时，`bleak` 能否连上它的自定义 GATT 服务？
2. 扫描能否发现它？（已连接的 BLE HID 设备通常停止广播，可能需走 macOS 的
   `retrieveConnectedPeripheralsWithServices`，`bleak` 中对应
   `retrieve_connected_peripherals`。）
3. 读特征、订阅 notify 在 macOS 上各自是否稳定？

**已有的正面证据**：
- `maxistar/zmk-gatt-layer` 证明"键盘 HID + 自定义 GATT 服务"架构成立；
- ZMK 官方 Studio 的原生 app 支持 macOS，且支持在 BLE 连接下改键位——
  这是"macOS 上能同时用 HID 与自定义 GATT"的最强背书。

**仍缺的确认**：`bleak` 具体库 + ZMK 键盘组合在 macOS 上无公开确证，故探针仍值得做。

## 7. 探针方案（下一步执行）

产物皆为**一次性丢弃物**。

**固件侧** —— 基于 `zmk-gatt-scalar` 骨架，几乎原样：
- 自定义 GATT 服务 + 一个 `READ | NOTIFY` 特征，暴露当前最高层号
  （`zmk_keymap_highest_layer_active()`），订阅 `zmk_layer_state_changed`。
- 用 **Totem 的配置**编译（挂 `-DZMK_EXTRA_MODULES`），而非原仓库测试配置。

**PC 侧** —— 一个 Python `bleak` 脚本：
- 两种发现方式都试：先扫描；扫不到再用 `retrieve_connected_peripherals`。
- 连上后**分别测 read 和 start_notify**，打日志证明是否通。
- 同时手动打字，确认 HID 照常工作。

**判定标准**：
- 打字正常 **且** 脚本能读到层号（并尽量订阅成功）= **成功**；
- 连上后键盘掉线 / 打不了字 = **失败**，路线 A 需调整
  （例如改用第二条连接或换传输方案）。

**编译方式**：倾向用键盘仓库的 GitHub Actions 出 `.uf2`，本地无需搭 west 环境，
下载后刷入键盘。

## 8. 待定项（执行前需拍板）

1. 探针代码落点：
   - A（推荐）：单独放本仓库 `zmk-dongle-display`（spike 分支/目录），不污染键盘仓库；
   - B：直接加到 `GEIGEIGEIST/zmk-config-totem`。
2. 编译方式确认：走 GitHub Actions（推荐）还是本地 west。

## 9. 里程碑

1. 执行探针 → 拿到"macOS 上 HID 与自定义 GATT 能否共存 + `bleak` 走通方式"的结论。
2. 依据结论完成正式设计（固件 payload 格式、轮询 vs 订阅、PC 应用架构）。
3. 写实施计划 → 实现固件模块 + PC 悬浮窗。
