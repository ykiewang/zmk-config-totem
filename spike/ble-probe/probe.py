#!/usr/bin/env python3
"""
BLE 共存探针（零固件 / 一次性丢弃物）
=====================================

纯 CoreBluetooth 同步版。CBCentralManager 的所有回调必须在主线程的 runloop 里触发，
所以本脚本完全同步：不用 asyncio，直接在主线程自旋 runloop 等待每一步完成。

目的：验证「键盘已被 macOS 系统当 HID 使用时，用户态程序能否同时读它的 GATT 特征」。

用法：
    python3 probe.py                     # 自动找名含 TOTEM 的已连接设备
    python3 probe.py --name TOTEM
    python3 probe.py --notify-seconds 15 # notify 观察窗口（期间请打字）

判定标准：
  打字正常 且 读到电量 => ✅ 成功，路线 A 可行
  连上后键盘掉线      => ❌ 失败，路线 A 需调整
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime

try:
    import objc
    from CoreBluetooth import CBCentralManager, CBUUID
    from Foundation import NSObject, NSRunLoop, NSDate
except ImportError:
    print("缺少依赖：pip install pyobjc-framework-CoreBluetooth", file=sys.stderr)
    raise

BATTERY_SERVICE = "180F"
BATTERY_LEVEL   = "2A19"
HID_SERVICE     = "1812"

CB_POWERED_ON = 5
CB_STATE_NAMES = {0:"Unknown",1:"Resetting",2:"Unsupported",
                  3:"Unauthorized",4:"PoweredOff",5:"PoweredOn"}


def ts():
    return f"[{datetime.now():%H:%M:%S}]"

def log(msg):
    print(f"{ts()} {msg}", flush=True)

def pump(seconds: float):
    """在当前（主）线程 pump runloop，持续 seconds 秒。"""
    deadline = time.time() + seconds
    while time.time() < deadline:
        NSRunLoop.currentRunLoop().runUntilDate_(
            NSDate.dateWithTimeIntervalSinceNow_(0.05)
        )

def pump_until(flag: dict, key: str, timeout: float) -> bool:
    """pump 直到 flag[key] 变为真值，或超时。返回是否成功。"""
    deadline = time.time() + timeout
    while not flag.get(key) and time.time() < deadline:
        NSRunLoop.currentRunLoop().runUntilDate_(
            NSDate.dateWithTimeIntervalSinceNow_(0.05)
        )
    return bool(flag.get(key))


class ProbeDelegate(NSObject):

    def init(self):
        self = objc.super(ProbeDelegate, self).init()
        if self is None:
            return None
        # 状态标志（供 pump_until 检查）
        self.bt_ready   = False
        self.bt_error   = None
        self.connected  = False
        self.conn_error = None
        self.svcs_done  = False
        self.svcs       = None
        self.chars_done = False
        self.chars      = None
        self.read_done  = False
        self.read_val   = None
        self.read_error = None
        self.notify_vals = []
        self._peripheral = None
        return self

    # ── CBCentralManagerDelegate ──────────────────────────────────────────────

    def centralManagerDidUpdateState_(self, mgr):
        s = int(mgr.state())
        log(f"  [CB] 蓝牙状态: {CB_STATE_NAMES.get(s, s)}")
        if s == CB_POWERED_ON:
            self.bt_ready = True
        elif s == 3:
            self.bt_error = "权限不足：系统设置 › 隐私与安全性 › 蓝牙 里勾上终端后重试"
            self.bt_ready = True  # 让 pump_until 退出

    def centralManager_didConnectPeripheral_(self, mgr, p):
        log(f"  [CB] 已连接：{p.name()}")
        self.connected = True

    def centralManager_didFailToConnectPeripheral_error_(self, mgr, p, err):
        self.conn_error = str(err) if err else "未知"
        log(f"  [CB] 连接失败：{self.conn_error}")
        self.connected = True  # 让 pump_until 退出

    def centralManager_didDisconnectPeripheral_error_(self, mgr, p, err):
        msg = str(err) if err else "正常断开"
        log(f"  [CB] 已断开：{p.name()} ({msg})")

    # ── CBPeripheralDelegate ──────────────────────────────────────────────────

    def peripheral_didDiscoverServices_(self, p, err):
        if err:
            log(f"  [CB] 发现服务失败：{err}")
        else:
            svcs = list(p.services() or [])
            log(f"  [CB] 服务列表：{[str(s.UUID().UUIDString()) for s in svcs]}")
            self.svcs = svcs
        self.svcs_done = True

    def peripheral_didDiscoverCharacteristicsForService_error_(self, p, svc, err):
        if err:
            log(f"  [CB] 发现特征失败：{err}")
        else:
            chars = list(svc.characteristics() or [])
            log(f"  [CB] 特征列表：{[str(c.UUID().UUIDString()) for c in chars]}")
            self.chars = chars
        self.chars_done = True

    def peripheral_didUpdateValueForCharacteristic_error_(self, p, char, err):
        if err:
            self.read_error = str(err)
            log(f"  [CB] 读/notify 失败：{err}")
        else:
            val = bytes(char.value()) if char.value() else b""
            if not self.read_done:
                self.read_val = val
                self.read_done = True
            self.notify_vals.append(val)

    def peripheral_didUpdateNotificationStateForCharacteristic_error_(self, p, char, err):
        if err:
            log(f"  [CB] notify 订阅失败：{err}")
        else:
            log(f"  [CB] notify 状态：{'已启用' if char.isNotifying() else '已停用'}")


def run_probe(args) -> bool:
    d = ProbeDelegate.alloc().init()

    # 1. 等 BT 就绪
    log("创建 CBCentralManager，等待蓝牙就绪...")
    mgr = CBCentralManager.alloc().initWithDelegate_queue_(d, None)
    if not pump_until(d.__dict__, "bt_ready", timeout=5.0):
        log("超时：蓝牙未就绪。")
        return False
    if d.bt_error:
        log(f"蓝牙错误：{d.bt_error}")
        return False

    # 2. 枚举已连接外设
    wanted = [CBUUID.UUIDWithString_(BATTERY_SERVICE),
              CBUUID.UUIDWithString_(HID_SERVICE)]
    peripherals = mgr.retrieveConnectedPeripheralsWithServices_(wanted)
    if not peripherals:
        log("未找到已连接的电量/HID 外设，请确认键盘已蓝牙连接。")
        return False
    log("已连接外设：")
    for p in peripherals:
        log(f"    {p.identifier().UUIDString()}  name={p.name()!r}")
    want = args.name.lower()
    target = next((p for p in peripherals if p.name() and want in p.name().lower()), peripherals[0])
    log(f"选用：{target.identifier().UUIDString()}  name={target.name()!r}")
    target.setDelegate_(d)

    # 3. connectPeripheral（对已连接设备，macOS 可能直接回调，也可能不回调）
    log("connectPeripheral_options_...")
    mgr.connectPeripheral_options_(target, None)
    if not pump_until(d.__dict__, "connected", timeout=6.0):
        log("连接回调超时——已连接设备在某些 macOS 版本不触发此回调，继续尝试 discoverServices。")
    elif d.conn_error:
        log(f"连接失败：{d.conn_error}")
        return False

    # 4. discoverServices
    log("discoverServices_ [180F]...")
    target.discoverServices_([CBUUID.UUIDWithString_(BATTERY_SERVICE)])
    if not pump_until(d.__dict__, "svcs_done", timeout=7.0):
        log("discoverServices 超时。")
        return False
    if not d.svcs:
        log("未发现电量服务（180F）。该 ZMK 固件可能没启用 BAS，或键盘未授权 GATT。")
        return False
    batt_svc = d.svcs[0]

    # 5. discoverCharacteristics
    log("discoverCharacteristics_ [2A19]...")
    target.discoverCharacteristics_forService_(
        [CBUUID.UUIDWithString_(BATTERY_LEVEL)], batt_svc
    )
    if not pump_until(d.__dict__, "chars_done", timeout=7.0):
        log("discoverCharacteristics 超时。")
        return False
    if not d.chars:
        log("未找到电量特征（2A19）。")
        return False
    batt_char = d.chars[0]

    # 6. READ
    log("readValueForCharacteristic_ [2A19]...")
    target.readValueForCharacteristic_(batt_char)
    if not pump_until(d.__dict__, "read_done", timeout=7.0):
        log("  [READ] 读取超时。")
        return False
    if d.read_error:
        log(f"  [READ] 失败：{d.read_error}")
        return False
    level = d.read_val[0] if d.read_val else None
    log(f"  [READ] 电量 = {level}%  (raw={d.read_val.hex()})")

    # 7. NOTIFY
    target.setNotifyValue_forCharacteristic_(True, batt_char)
    log(f"  [NOTIFY] 已发起订阅，观察 {args.notify_seconds:.0f}s ——"
        f" 请现在手动打字，确认 HID 照常工作！")
    n_before = len(d.notify_vals)
    pump(args.notify_seconds)
    n_got = len(d.notify_vals) - n_before
    for v in d.notify_vals[n_before:]:
        log(f"  [NOTIFY] 推送 = {v[0] if v else '?'}%  (raw={v.hex()})")
    log(f"  [NOTIFY] 结束，收到 {n_got} 次"
        f"（电量很少变化，0 次≠失败，READ 成功即可）。")
    target.setNotifyValue_forCharacteristic_(False, batt_char)
    return True


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="零固件 BLE 共存探针（纯 CoreBluetooth 同步版）"
    )
    p.add_argument("--name", default="TOTEM")
    p.add_argument("--notify-seconds", type=float, default=12.0)
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    log("=" * 70)
    log("BLE 共存探针启动。请确保 Totem 已作为蓝牙键盘连在这台 Mac 上。")
    log("=" * 70)
    try:
        ok = run_probe(args)
    except KeyboardInterrupt:
        log("用户中断。")
        return 130
    log("=" * 70)
    if ok:
        log("探针结果：✅ 成功读到 GATT 电量。")
        log("若刚才打字全程正常 => HID+GATT(CoreBluetooth) 共存成立，路线 A 基础验证通过。")
        log("下一步：写自定义 GATT 服务固件（<100 行），用同一脚本验自定义 UUID。")
    else:
        log("探针结果：❌ 未能读到 GATT 电量。请对照日志判断卡在哪一环。")
    log("=" * 70)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
