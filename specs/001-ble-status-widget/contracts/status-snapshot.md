# Interface Contract: Status Snapshot (Firmware ↔ Host)

**Status**: FROZEN (per Principle I). Both firmware and host are built against
this contract; the concrete identifiers and byte layout below MUST NOT change
without a coordinated version bump on both sides (MAJOR if the layout changes).

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
host MUST enumerate connected peripherals (filtering on the HID service
`0x1812` and the custom service above) and select by name; active scanning will
not find it.

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

## Implementation notes (non-normative)

These describe the current build; they do **not** alter the frozen layout above.

- The firmware truncates `layer_name` to 32 bytes (`strnlen`, `LAYER_NAME_MAX`), so
  a snapshot fits comfortably within the default ATT MTU. This is an implementation
  limit, not a contract change — all four shipped layer names are far shorter.
- Both consumers follow the Discovery note: the macOS app and `tools/probe.py` find
  the keyboard by enumerating connected peripherals (CoreBluetooth
  `retrieveConnectedPeripherals`), not by scanning.
