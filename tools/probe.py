#!/usr/bin/env python3
# Copyright (c) 2026 The TOTEM ZMK Contributors
# SPDX-License-Identifier: MIT
#
# Reworked from the probe phase to decode the status snapshot payload
# [idx][mods][name] defined in specs/001-ble-status-widget/contracts/status-snapshot.md.
#
# Usage: python3 tools/probe.py
# Requires: pip install bleak

import asyncio
import struct
import sys

from bleak import BleakClient, BleakScanner

SERVICE_UUID = "aa440aa0-f5ed-4c48-84a1-8062d20d3d55"
CHAR_UUID = "aa440aa1-f5ed-4c48-84a1-8062d20d3d55"

MOD_NAMES = [
    ("LCtrl", 0x01), ("LShift", 0x02), ("LAlt", 0x04), ("LGui", 0x08),
    ("RCtrl", 0x10), ("RShift", 0x20), ("RAlt", 0x40), ("RGui", 0x80),
]


def decode(data: bytes) -> str:
    if len(data) < 2:
        return f"<short packet, {len(data)} bytes>"
    idx, mods = data[0], data[1]
    name = data[2:].decode("utf-8", errors="replace")
    active = [n for n, bit in MOD_NAMES if mods & bit]
    return f"layer_index={idx} layer_name={name!r} mods=0x{mods:02x} active={active}"


async def main() -> int:
    print("scanning for TOTEM ...")
    device = await BleakScanner.find_device_by_filter(
        lambda d, adv: d.name is not None and "TOTEM" in d.name.upper()
    )
    if device is None:
        print("no TOTEM device found (is the keyboard connected to this machine?)")
        return 1

    print(f"found {device.name} ({device.address})")
    async with BleakClient(device) as client:
        print("connected, reading initial snapshot")
        value = await client.read_gatt_char(CHAR_UUID)
        print("  " + decode(bytes(value)))

        def on_notify(_sender, data: bytearray) -> None:
            print("  " + decode(bytes(data)))

        await client.start_notify(CHAR_UUID, on_notify)
        print("subscribed; switch layers / hold modifiers (Ctrl-C to quit)")
        while True:
            await asyncio.sleep(1)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        print("\nbye")
        sys.exit(0)
