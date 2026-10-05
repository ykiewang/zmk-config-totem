# Interface Contract: Status Snapshot (Firmware ↔ Host)

**Status**: FROZEN (per Principle I). Both firmware and host are built against
this contract; the concrete identifiers and byte layout below MUST NOT change
without a coordinated version bump on both sides (MAJOR if the layout changes).
Amended by feature 002 with a backward-compatible **Discovery & Identity**
clarification (see section below): identity is by the custom service UUID and the
display name is the BLE GAP name — this changes no payload byte, so there is **no**
payload version bump.

## Transport: BLE GATT

A primary GATT service on the keyboard's central half exposing one
characteristic.

| Item | Value |
|------|-------|
| Service | `AA440AA0-F5ED-4C48-84A1-8062D20D3D55` |
| Characteristic | `AA440AA1-F5ED-4C48-84A1-8062D20D3D55` |
| Properties | `READ` \| `NOTIFY` |
| Descriptor | CCC (Client Characteristic Configuration) |
| Permission | readable |

**Discovery note**: An already-connected BLE HID device stops advertising. The
host MUST enumerate connected peripherals (filtering on the HID service `0x1812`
and the custom service above) and **identify a compatible keyboard by the presence
of the custom service, confirmed via GATT discovery — never by name**; active
scanning will not find an already-connected keyboard.

## Payload layout

Variable-length, little-endian where multi-byte (no multi-byte fields in v1).

| Offset | Size | Field | Meaning |
|--------|------|-------|---------|
| `[0]` | 1 | `layer_index` | Active layer index, `uint8`. Debug/fallback; host primarily shows the name. |
| `[1]` | 1 | `mods` | Standard HID modifier bitmask, `uint8` (layout below). |
| `[2..N]` | ≥0 | `layer_name` | Active layer name, UTF-8, **no** trailing `\0`. Length = total − 2. |

**Modifier bitmask** (collapsed to 4 logical indicators on the host):

| Bit | Mask | HID key |
|-----|------|---------|
| 0 | `0x01` | Left Control |
| 1 | `0x02` | Left Shift |
| 2 | `0x04` | Left Alt |
| 3 | `0x08` | Left Gui |
| 4 | `0x10` | Right Control |
| 5 | `0x20` | Right Shift |
| 6 | `0x40` | Right Alt |
| 7 | `0x80` | Right Gui |

## Behavior

- **READ**: returns the current snapshot (initial value on connect).
- **NOTIFY**: sent only when the snapshot changes (layer or modifier change);
  identical recomputations are suppressed by cache comparison.
- **Subscribe**: host enables notifications via the CCC; on reconnect it re-reads
  (READ) then re-subscribes.

## Consumer rules (host)

1. Reject payloads shorter than 2 bytes.
2. Decode `layer_name` as UTF-8; if empty or undecodable, display `L{layer_index}`.
3. Merge modifier halves: Shift = `0x02|0x20`, Control = `0x01|0x10`,
   Alt = `0x04|0x40`, Gui = `0x08|0x80`.
4. Treat absence of a live subscription as `not_connected`; do not display stale
   state as current.

## Producer rules (firmware)

1. Read state only from authoritative ZMK APIs (`highest_layer_active`,
   `layer_index_to_id` → `layer_name`, `hid_get_explicit_mods`).
2. Convert index→id before requesting the name (safe under reordering).
3. Emit no notification when the recomputed snapshot equals the cache.
4. Compile only for the central role and only when the feature symbol is enabled.

## Compatibility

- Adding trailing bytes after `layer_name` (new reserved fields) is
  backward-compatible for old hosts (they ignore the tail) and does not require a
  version bump.
- Reinterpreting existing byte positions or changing identifiers is breaking and
  requires a coordinated version bump on both sides.

## Discovery & Identity (feature 002 clarification — no layout change)

Introduced by feature 002 (multi-keyboard support). A backward-compatible refinement
of discovery/identity semantics only: the payload layout above is unchanged, so this
does **not** bump the payload version.

### Compatibility (identity by service, not by name)

- A device is a **compatible keyboard** if and only if it **exposes the custom
  service** `AA440AA0-…`. No name, make, or model may be used as a compatibility
  test.
- Hosts MUST enumerate connected peripherals filtering on the custom service **and**
  the HID service `0x1812`, then **confirm** the custom service via GATT service
  discovery after connecting. Active scanning is a fallback only for a keyboard not
  yet connected to the host.
- A device that does not expose the custom service after discovery MUST NOT be
  treated as a compatible keyboard, even if it is a keyboard.

### Keyboard name (self-reported identity)

- The keyboard's **display name is its BLE GAP device name** (`CBPeripheral.name` on
  macOS; `CONFIG_ZMK_KEYBOARD_NAME` on ZMK). No dedicated name characteristic exists
  in v1; the name is obtained **once at discovery/connection**, never on status
  changes (preserves the no-idle-traffic guarantee).
- Hosts MUST render the GAP name when present and non-empty; when it is absent/empty,
  hosts MUST show a generic fallback (e.g. `Keyboard <short-identifier>`) and still
  connect.
- Hosts MUST NOT maintain a registry/whitelist of models; identity comes only from
  the service (compatibility) and the GAP name (display).
- **Reserved extension** (not implemented): a future dedicated read-once name
  characteristic MAY be added, as an additive, backward-compatible change under the
  Compatibility rules above.

### Selection & persistence (host behavior)

- **Stable key**: `CBPeripheral.identifier` (UUID) identifies and disambiguates a
  keyboard and is the reconnect/remember key. Names are not unique and MUST NOT be
  used as the stable key.
- Auto-connect when exactly one compatible keyboard is present, or when a remembered
  identifier is among the candidates. With ≥ 2 candidates and none remembered, the
  host MUST await an explicit choice (no silent guess). The host tracks exactly one
  selected keyboard at a time.

### Firmware enablement (the KeyBeacon kit)

| Item | Value |
|------|-------|
| Kconfig symbol | `CONFIG_ZMK_KEYBEACON` (bool, `default n`) |
| Depends on | `ZMK_BLE` |
| Build gate | compiled only when the symbol is set **and** the build is the central role |
| Shared source | `keybeacon.c` (kit-provided; not edited to port) |

## Implementation notes (non-normative)

These describe the current build; they do **not** alter the frozen layout above.

- The firmware truncates `layer_name` to 32 bytes (`strnlen`, `LAYER_NAME_MAX`), so
  a snapshot fits comfortably within the default ATT MTU. This is an implementation
  limit, not a contract change — all four shipped layer names are far shorter.
- Both consumers follow the Discovery note: the macOS app and `tools/probe.py` find
  the keyboard by enumerating connected peripherals (CoreBluetooth
  `retrieveConnectedPeripherals`), not by scanning.
