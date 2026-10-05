# Interface Contract: Discovery & Identity (amends Status Snapshot)

**Status**: PROPOSED for feature 002. This **amends** (does not replace)
`specs/001-ble-status-widget/contracts/status-snapshot.md`. The status **payload layout is
unchanged**; this document fixes how a host *finds* and *names* a keyboard, and how firmware
is *enabled*. Per Principle I these rules are frozen before implementation; both the macOS app
and `tools/probe.py` are built against them. During implementation the normative text here is
folded into the canonical `status-snapshot.md` (a backward-compatible clarification, not a
layout change → no payload version bump).

## 1. Transport & service (unchanged)

| Item | Value |
|------|-------|
| Service | `AA440AA0-F5ED-4C48-84A1-8062D20D3D55` |
| Characteristic | `AA440AA1-F5ED-4C48-84A1-8062D20D3D55` (`READ` \| `NOTIFY`, CCC) |
| HID service (discovery aid) | `0x1812` |

## 2. Compatibility (identity by service, not by name)

- A device is a **compatible keyboard** if and only if it **exposes the custom service**
  `AA440AA0-…`. No name, make, or model may be used as a compatibility test.
- **Discovery**: because a connected BLE HID keyboard stops advertising, hosts MUST enumerate
  **connected** peripherals filtering on the custom service **and** the HID service `0x1812`
  (`retrieveConnectedPeripherals(withServices:)` on macOS), then **confirm** the custom service
  via GATT service discovery after connecting. Active scanning is a fallback only for a keyboard
  not yet connected to the host.
- A device that does not expose the custom service after discovery MUST NOT be treated as a
  compatible keyboard, even if it is a keyboard.

## 3. Keyboard name (self-reported identity)

- The keyboard's **display name is its BLE GAP device name** (`CBPeripheral.name` on macOS),
  which on ZMK is `CONFIG_ZMK_KEYBOARD_NAME`. No dedicated name characteristic exists in v1; the
  name is obtained **once at discovery/connection**, never on status changes.
- Hosts MUST render the GAP name when present and non-empty; when it is absent/empty, hosts MUST
  show a generic fallback (e.g. `Keyboard <short-identifier>`) and still connect.
- Hosts MUST NOT maintain a registry/whitelist of models; identity comes only from the service
  (compatibility) and the GAP name (display).
- **Reserved extension** (not implemented): a future dedicated read-once name characteristic MAY
  be added for keyboards needing a display name distinct from their BT name. This is an additive,
  backward-compatible change under the status-snapshot compatibility rules.

## 4. Selection & persistence (host behavior)

- **Stable key**: `CBPeripheral.identifier` (UUID) identifies and disambiguates a keyboard and is
  the reconnect/remember key. Names are not unique and MUST NOT be used as the stable key.
- Auto-connect when exactly one compatible keyboard is present, or when a remembered identifier
  is among the candidates. With ≥ 2 candidates and none remembered, the host MUST await an
  explicit choice (no silent guess). The host tracks exactly one selected keyboard at a time.

## 5. Firmware enablement contract (the KeyBeacon kit)

The firmware side of the contract is enabled by a **generic, keyboard-independent** symbol —
this is the stable name keyboards and docs depend on:

| Item | Value |
|------|-------|
| Kconfig symbol | `CONFIG_ZMK_KEYBEACON` (bool, `default n`) |
| Depends on | `ZMK_BLE` |
| Build gate | compiled only when the symbol is set **and** the build is the central role |
| Shared source | `keybeacon.c` (renamed from `gatt_status.c`; kit-provided; not edited to port) |

A conforming keyboard enables the feature by making the kit available to its shield, wiring the
kit's CMake and Kconfig snippets, and setting `CONFIG_ZMK_KEYBEACON=y`. Producer behavior
(state sources, change-detection, notify-on-change) is unchanged from the status-snapshot
contract §"Producer rules".

## 6. Conformance checklist (verifiable items)

1. Device exposes service `AA440AA0-…` with characteristic `AA440AA1-…` (`READ`+`NOTIFY`, CCC).
2. Characteristic READ returns a snapshot ≥ 2 bytes; payload matches the status-snapshot layout.
3. NOTIFY fires on layer/modifier change and is suppressed when unchanged.
4. The GAP device name is set (non-empty) — else the host falls back to a generic label.
5. Feature is absent from peripheral and `settings_reset` builds (central-only).

(These items are what `tools/probe.py` checks on-device for feature 002, and are the seed for
feature 003's conformance tool.)
