# BLE 共存探针（零固件 · 一次性丢弃物）

一个只用来回答**一个问题**的最小脚本：

> 在这台 Mac 上，当 Totem 正作为蓝牙 **HID 键盘**使用时，用户态程序（`bleak`）
> 还能不能同时连上它的 **GATT**、读到数据，而**打字不受影响**？

它**不改任何固件**，连的是键盘**现成就有的标准电量服务**（Battery `0x180F` /
Battery Level `0x2A19`）。链路一旦走通，就等于证明了设计方案里路线 A 的核心前提
（HID 与自定义 GATT 共存）在 macOS + `bleak` 上成立。产物用完即弃。

> 这一步覆盖"标准服务"。"自定义 128-bit 服务能否同样被发现"留给下一步（step-1，
> 写 <100 行固件再用**同一个脚本**验证）。

---

## 1. 环境要求

- **macOS**（本机 CoreBluetooth）。
- **Python 3.9+**。
- 键盘：Totem 的**中央半（左半）**已开机，并作为蓝牙键盘**正常连在这台 Mac 上**
  （系统设置里显示已连接、能打字）。
- 依赖：`bleak`。macOS 上安装 `bleak` 会自动带入所需的 `pyobjc` 框架，所以
  `requirements.txt` 里只有它一条。

## 2. 安装

```bash
cd spike/ble-probe
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. ⚠️ 必做：给终端蓝牙权限（最常见的"假性失败"来源）

macOS 要求 App 显式获得蓝牙权限，否则 `bleak` **扫不到任何设备且不报错**。

**系统设置 › 隐私与安全性 › 蓝牙** → 打开你运行脚本的那个终端
（Terminal / iTerm / VS Code）。首次运行可能弹窗授权，允许即可；授权后**重启终端**。

脚本若探测到 `Unauthorized` 状态，会在日志里直接提示这一条。

## 4. 运行

```bash
python probe.py                     # 默认按名字 "TOTEM" 查找
python probe.py --notify-seconds 15 # 把 notify 观察窗拉长到 15s
python probe.py --name totem        # 名字子串匹配，忽略大小写
python probe.py --address <CBUUID>  # 直接指定 macOS 的 CoreBluetooth UUID
```

**运行期间最关键的动作：在 `[NOTIFY] 已订阅…请现在手动打字` 出现后，立刻在任意
输入框里持续打字几秒**，确认键盘 HID 没有因为这条 GATT 连接而卡顿或掉线。

## 5. 脚本做了什么（三段式，对应方案 §6 的三问）

1. **发现**：先 `BleakScanner` 扫描，并把看到的**每个**设备（名字 / 地址 /
   RSSI / 广播的服务 UUID）全部打出来。
   —— 已连接的 HID 设备通常**不再广播**，扫不到属正常，不等于失败。
2. **兜底**：扫不到时，走 CoreBluetooth 的
   `retrieveConnectedPeripheralsWithServices:` 枚举**系统已连接**、且暴露
   电量/HID 服务的外设，拿到它的 CoreBluetooth UUID 再交给 `bleak` 连。
   —— "能否用这条路连上"本身就是问题①要的答案。
3. **读取 + 订阅**：连上后列出全部服务/特征，`read` 电量 `0x2A19`，并
   `start_notify` 订阅一个观察窗（期间你打字）。

## 6. 判定标准（抄自设计方案 §7）

| 现象 | 结论 |
|---|---|
| 打字正常 **且** 脚本读到电量（notify 能收到更好，但电量很少变，0 次不算失败） | ✅ **成功**：HID+GATT 可共存，`bleak` 走得通 |
| 连上后键盘掉线 / 打不了字 | ❌ **失败**：路线 A 需调整（第二条连接或换传输） |
| 扫描 + 兜底都定位不到设备 | ⚠️ **发现方式存疑**：先查第 3 节权限；仍不行则发现策略要再想办法 |

脚本结尾会打印一句明确的 ✅/❌/⚠️ 结论，退出码：`0`=读到电量，`1`=定位到但没读到，
`2`=没定位到设备。

## 7. macOS 常见坑

- **权限**（见第 3 节）—— 排第一，十有八九是它。
- **已连接设备不广播** —— 所以才有 CoreBluetooth 兜底；别靠"扫到"来判断成败。
- **地址不是 MAC** —— macOS 下设备地址是**本机专属的 CoreBluetooth UUID**，换台
  Mac 会变，不要跨机器复用 `--address`。
- **GATT 缓存**（**下一步**测自定义服务时才会踩）—— 给固件加了新服务后 macOS 常
  继续吃旧缓存导致发现不到；届时在系统蓝牙里**移除该键盘重连**，或改设备名。本步只
  读标准服务，不涉及。

## 8. 清理

一次性产物。结论拿到后，直接删掉 `spike/ble-probe/`（及其 `.venv`）即可，不影响键盘配置。
