# 方案：ZMK 键盘状态在电脑上的悬浮窗显示

- 日期：2026-10-04（2026-10-05 更新：探针完成，路线 A 验证通过）
- 状态：**探针阶段完成，路线 A 已验证可行 → 进入正式实现设计**
- 代码落点：探针脚本与固件模块均在 `zmk-config-totem`（`spike/`、`modules/`，分支 `feature/gatt-layer-probe`）
- 键盘配置仓库：`ykiewang/zmk-config-totem`（硬件来自 `GEIGEIGEIST/totem`）

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
- **硬件**：Totem 分体键盘，配置来自 `ykiewang/zmk-config-totem`。

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

### 路线 A（选定，已验证）：自定义 GATT 服务 + PC 端订阅
- 固件：注册自定义 128-bit UUID 的 GATT 服务，含一个特征（`READ | NOTIFY`），
  把状态打包发送。
- PC：订阅该特征，悬浮窗渲染。
- 优点：链路解耦、固件改动小、状态变化才推送、与 HID 共存不影响打字。
- 风险（第 6 节）：macOS 上"已被系统当 HID 的键盘"能否被用户态程序再连 GATT。
  → **已由探针验证通过，见第 7 节。**
- 固件形态注记：探针用**独立 module** 跑通；但正式版要读**真实**层名/修饰键需调用
  ZMK 内部 API，而独立 module 拿不到其 PRIVATE 头（见 §7 关键技术发现），形态待重新拍板。

### 路线 B（否决）：复用 ZMK Studio 的 RPC 通道
- 消息定义在 `zmk-studio-messages` 仓库，需改官方协议、跟上游同步，**过重**。

### 路线 C（否决）：不改固件，PC 端从按键推断
- 电脑看不到"层"这个概念，固件不发永远不知道，**不可行**。

## 5. 关键先例：`maxistar/zmk-gatt-layer`

一个已被验证可编译可跑的 PoC，功能 = **把"当前激活层号"一个整数通过自定义 GATT
发给电脑**。作为固件骨架参考（`BT_GATT_SERVICE_DEFINE` + `READ | NOTIFY` 特征 +
事件订阅 + 小端编码），本项目 step-1 即照此最小骨架起步。

局限：只是 PoC、未测 macOS、只传层号一个整数、客户端仅 Rust 命令行。

## 6. 不确定性 / 探针要回答的问题（历史背景）

1. 这台 Mac 上，键盘当 HID 用的同时，用户态程序能否连上它的自定义 GATT 服务？
2. 扫描能否发现它？（已连接的 BLE HID 设备通常停止广播。）
3. 读特征、订阅 notify 在 macOS 上各自是否稳定？

→ 以上三问均在第 7 节得到肯定答复。

## 7. 探针执行结果（2026-10-05，已完成）

两步探针，产物在 `spike/ble-probe/`（PC 侧）与 `modules/zmk-gatt-layer-probe/`（固件）。

### Step-0：标准电量 GATT（零固件）
- 不改固件，直接读键盘已有的标准电量服务 `0x180F` / 特征 `0x2A19`。
- 结果：✅ 读到电量值，订阅 NOTIFY 成功，**全程打字正常**。
- 结论：macOS 上 **HID 与 GATT 可共存**，用户态程序能读被系统当 HID 的键盘的 GATT。

### Step-1：自定义 128-bit UUID 服务（需固件）
- 新增固件模块暴露自定义服务 `AA440AA0-…` / 特征 `AA440AA1-…`（`READ | NOTIFY`）。
- 结果：✅ **发现** 自定义服务与特征、✅ **READ** 成功、✅ **NOTIFY** 收到定时推送，
  **全程打字正常**。
- 结论：自定义 128-bit UUID 服务同样可被 macOS 发现/读取/订阅。**路线 A 完全成立。**

### 实现要点与踩坑（固化经验）

**PC 侧**：
- **放弃 `bleak`，改用纯 CoreBluetooth（pyobjc）**。bleak 3.x 在 macOS 对"已连接
  HID 设备"处理有坑（`BLEDevice.details` 需 `(CBPeripheral, delegate)` 元组等），
  难以稳定复现。
- CoreBluetooth 回调必须在**主线程 runloop** 触发；脚本做成**全同步、主线程自旋
  runloop**，否则 `centralManagerDidUpdateState_` 等回调不触发。
- 已连接的 BLE HID 设备**不再广播**，扫描发现不到；改用
  `retrieveConnectedPeripheralsWithServices:` 直接枚举。
- 其它：GATT 缓存（必要时移除配对避免读到旧值）、终端需在"系统设置›隐私›蓝牙"授权、
  用 venv 的 `python3`。

**固件侧**：
- 本地模块加载：**仓库根放 `zephyr/module.yml`**，ZMK `build-user-config.yml` 检测到后
  经 `-DZMK_EXTRA_MODULES` 把整个 config 仓库当 Zephyr module 编译。
- `west.yml` **不能**把本地 `modules/` 目录当 project 列（project 必须可 fetch，
  否则报 "Malformed manifest file"）。
- 用 `depends on ZMK_BLE` + `if(CONFIG_…)` 守卫，使无蓝牙栈的 `settings_reset` 自动跳过编译。
- GitHub Actions 出 `.uf2`，本地无需 west 环境。

**关键技术发现（决定正式版形态）**：
- ZMK 内部头（`zmk/keymap.h` 等）在 `app/include`，以
  **`target_include_directories(app PRIVATE)`** 暴露，**不导出给独立 module**。
  独立 module `#include <zmk/keymap.h>` 会编译失败（`fatal error: zmk/keymap.h: No such file`）。
- 故探针改用**纯 Zephyr BT API + 假层号**（定时器 0..7 循环推送）验证链路，不依赖 ZMK API。
- **正式版要真实层名/修饰键，必须能访问 ZMK 内部 API** → 固件不宜是独立 module，
  需把代码放进 **shield 内**（`config/boards/shields/totem/`，被 app 直接编译、可访问内部头）
  或其他能拿到内部头的形态。这是正式版的**第一个待决策点**。

## 8. 已拍板的决策

1. **代码落点**：全部放 `zmk-config-totem`（否决原"放 `zmk-dongle-display`"草案）。
   探针是一次性验证物，不值得独立建仓；正式版再评估是否提取。
2. **编译方式**：GitHub Actions 出 `.uf2`（已验证可行）。
3. **不以 ZMK Studio 作探针/方案**：会强制 physical-layout 迁移 + 删除现有 `chosen`
   matrix-transform，改动过大。
4. **分支**：spike 在 `feature/gatt-layer-probe`，不直接提交主干。

## 9. 里程碑

1. ✅ 执行探针 → 已确认"macOS 上 HID 与自定义 GATT 可共存，且自定义 128-bit UUID
   可发现/读取/订阅"。走通方式 = 纯 CoreBluetooth + `retrieveConnectedPeripheralsWithServices`。
2. ⏳ 正式设计：
   - **固件形态**（独立 module 不行 → shield 内代码 or 其他能访问内部头的方式）；
   - **payload 格式**（层名字符串 + 修饰键位掩码，`READ` + `NOTIFY`）；
   - **PC 应用架构**（常驻连接 + 悬浮窗渲染）。
3. ⏳ 写实施计划 → 实现固件（真实层名/修饰键）+ PC 悬浮窗。
