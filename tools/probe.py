#!/usr/bin/env python3
# Copyright (c) 2026 The TOTEM ZMK Contributors
# SPDX-License-Identifier: MIT
#
# On-device probe for the status snapshot payload [idx][mods][name] defined in
# specs/001-ble-status-widget/contracts/status-snapshot.md.
#
# macOS / CoreBluetooth: an already-connected BLE HID keyboard stops
# advertising, so (per the contract Discovery note) this enumerates CONNECTED
# peripherals via retrieveConnectedPeripheralsWithServices: instead of scanning.
# Active scanning is kept only as a fallback for a keyboard that is not yet
# connected to this Mac.
#
# Usage: tools/.venv/bin/python tools/probe.py
# Requires (macOS): PyObjC CoreBluetooth — installed as a bleak dependency, or
#   `pip install pyobjc-framework-CoreBluetooth`.

import datetime
import sys

import objc
from Foundation import NSObject
import CoreBluetooth as CB
from PyObjCTools import AppHelper

SERVICE_UUID = CB.CBUUID.UUIDWithString_("AA440AA0-F5ED-4C48-84A1-8062D20D3D55")
CHAR_UUID = CB.CBUUID.UUIDWithString_("AA440AA1-F5ED-4C48-84A1-8062D20D3D55")
HID_UUID = CB.CBUUID.UUIDWithString_("1812")

POWERED_ON = getattr(CB, "CBManagerStatePoweredOn", 5)

MOD_NAMES = [
    ("LCtrl", 0x01), ("LShift", 0x02), ("LAlt", 0x04), ("LGui", 0x08),
    ("RCtrl", 0x10), ("RShift", 0x20), ("RAlt", 0x40), ("RGui", 0x80),
]


def _ts():
    return datetime.datetime.now().strftime("%H:%M:%S")


def _nsdata_to_bytes(d):
    if d is None:
        return b""
    try:
        return bytes(d)
    except Exception:
        n = int(d.length())
        return bytes(bytearray(d.bytes()[:n]))


def _uuid_eq(a, b):
    return a.UUIDString().lower() == b.UUIDString().lower()


def decode(data: bytes) -> str:
    if len(data) < 2:
        return "<short packet, %d bytes>" % len(data)
    idx, mods = data[0], data[1]
    name = data[2:].decode("utf-8", errors="replace")
    active = [n for n, bit in MOD_NAMES if mods & bit]
    return "layer_index=%d layer_name=%r mods=0x%02x active=%s" % (
        idx, name, mods, active
    )


class Probe(NSObject):
    def init(self):
        self = objc.super(Probe, self).init()
        if self is None:
            return None
        self.manager = None
        self.peripheral = None
        self.candidates = []
        self.cand_i = 0
        self.connected = False
        self.scanning = False
        return self

    # --- central manager delegate ---

    def centralManagerDidUpdateState_(self, central):
        if central.state() != POWERED_ON:
            print("Bluetooth not powered on (state=%s); waiting ..." % central.state())
            return
        conn = central.retrieveConnectedPeripheralsWithServices_(
            [HID_UUID, SERVICE_UUID]
        )
        self.candidates = list(conn)
        if self.candidates:
            print("found %d connected candidate(s): %s"
                  % (len(self.candidates),
                     [str(p.name()) for p in self.candidates]))
            self._try_next()
        else:
            print("no connected KeyBeacon keyboard found; falling back to scan "
                  "(connect the keyboard to this Mac for the reliable path) ...")
            self.scanning = True
            central.scanForPeripheralsWithServices_options_([SERVICE_UUID], None)
            AppHelper.callLater(15.0, self._scan_timeout)

    def _try_next(self):
        if self.cand_i >= len(self.candidates):
            print("exhausted candidates without finding the status service")
            return
        p = self.candidates[self.cand_i]
        self.cand_i += 1
        self.peripheral = p
        p.setDelegate_(self)
        print("connecting to %s ..." % (p.name() or p.identifier().UUIDString()))
        self.manager.connectPeripheral_options_(p, None)

    def _scan_timeout(self):
        if not self.connected:
            print("scan found nothing in 15s. Is the keyboard on and in range?")

    def centralManager_didDiscoverPeripheral_advertisementData_RSSI_(
        self, central, peripheral, adv, rssi
    ):
        if self.scanning:
            self.scanning = False
            central.stopScan()
            self.candidates = [peripheral]
            self.cand_i = 0
            self._try_next()

    def centralManager_didConnectPeripheral_(self, central, peripheral):
        self.connected = True
        print("connected; discovering status service ...")
        peripheral.discoverServices_([SERVICE_UUID])

    def centralManager_didFailToConnectPeripheral_error_(
        self, central, peripheral, error
    ):
        print("failed to connect: %s" % error)
        self.connected = False
        self._try_next()

    def centralManager_didDisconnectPeripheral_error_(
        self, central, peripheral, error
    ):
        print("disconnected: %s" % error)
        self.connected = False

    # --- peripheral delegate ---

    def peripheral_didDiscoverServices_(self, peripheral, error):
        if error is not None:
            print("service discovery error: %s" % error)
            self._try_next()
            return
        svc = None
        for s in (peripheral.services() or []):
            if _uuid_eq(s.UUID(), SERVICE_UUID):
                svc = s
                break
        if svc is None:
            print("status service not present on this peripheral; trying next")
            self._try_next()
            return
        print("status service confirmed on %r"
              % (peripheral.name() or peripheral.identifier().UUIDString()))
        peripheral.discoverCharacteristics_forService_([CHAR_UUID], svc)

    def peripheral_didDiscoverCharacteristicsForService_error_(
        self, peripheral, service, error
    ):
        if error is not None:
            print("characteristic discovery error: %s" % error)
            return
        ch = None
        for c in (service.characteristics() or []):
            if _uuid_eq(c.UUID(), CHAR_UUID):
                ch = c
                break
        if ch is None:
            print("status characteristic not found")
            return
        print("reading initial snapshot + subscribing to notifications ...")
        peripheral.readValueForCharacteristic_(ch)
        peripheral.setNotifyValue_forCharacteristic_(True, ch)

    def peripheral_didUpdateNotificationStateForCharacteristic_error_(
        self, peripheral, characteristic, error
    ):
        if error is not None:
            print("subscribe error: %s" % error)
        else:
            print("subscribed; switch layers / hold modifiers (Ctrl-C to quit)")

    def peripheral_didUpdateValueForCharacteristic_error_(
        self, peripheral, characteristic, error
    ):
        if error is not None:
            print("read error: %s" % error)
            return
        data = _nsdata_to_bytes(characteristic.value())
        print("  [%s] %s" % (_ts(), decode(data)))


def main() -> int:
    probe = Probe.alloc().init()
    probe.manager = CB.CBCentralManager.alloc().initWithDelegate_queue_(probe, None)
    print("starting probe (CoreBluetooth) ...")
    try:
        AppHelper.runConsoleEventLoop(installInterrupt=True)
    except KeyboardInterrupt:
        print("\nbye")
    return 0


if __name__ == "__main__":
    sys.exit(main())
