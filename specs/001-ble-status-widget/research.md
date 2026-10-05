# Phase 0 Research: BLE Keyboard Status Widget

All Technical Context unknowns were resolved from the frozen design document and
the project's probe-phase findings. No open NEEDS CLARIFICATION remains.

## R1. Firmware placement: shield code vs standalone module

- **Decision**: Implement the feature as shield-scoped code inside
  `config/boards/shields/totem/`.
- **Rationale**: ZMK's internal headers (`<zmk/keymap.h>`, etc.) are declared
  `app PRIVATE` and are not exported to standalone modules. Shield code can add
  `zephyr_library_include_directories(${CMAKE_SOURCE_DIR}/include)` to reach them,
  and it inherits per-role build gating for free. This avoids the module-loading
  machinery entirely.
- **Alternatives considered**: Standalone ZMK module (rejected — cannot reach
  `app` headers); patching `zmk/app` directly (rejected — forks upstream, breaks
  clean builds).

## R2. How to obtain the active layer name and index

- **Decision**: Read `zmk_keymap_highest_layer_active()` for the layer index, then
  convert index→id via `zmk_keymap_layer_index_to_id()` and call
  `zmk_keymap_layer_name()` for the display name.
- **Rationale**: `highest_layer_active()` returns an *index*; `layer_name()` takes
  an *id*. They coincide by default but diverge under
  `CONFIG_ZMK_KEYMAP_LAYER_REORDERING`, so always convert. Names come from the
  devicetree `display-name`/`label`; all four layers (`BASE`/`NAVI`/`SYM`/`ADJ`)
  already have labels, so no keymap change is needed. `layer_name()` returns
  `NULL` for out-of-range and `""` for unnamed layers.
- **Alternatives considered**: Hardcoding layer names in firmware (rejected —
  duplicates the keymap as a second source of truth, violates Principle II).

## R3. How to obtain current modifier state

- **Decision**: Read `zmk_hid_get_explicit_mods()` (returns a `zmk_mod_flags_t`
  uint8), and drive re-reads from `zmk_keycode_state_changed`.
- **Rationale**: The apparently-correct `zmk_modifiers_state_changed` event is an
  empty stub that nothing raises (confirmed in `behavior_hold_tap.c` comments),
  so it cannot be a driver. `zmk_keycode_state_changed` fires on modifier key
  press/release; re-reading explicit mods in that callback yields the live state.
- **Alternatives considered**: Subscribing to `zmk_modifiers_state_changed`
  (rejected — never raised); polling on a timer (rejected — wastes power,
  violates Principle III's no-redundant-traffic intent).

## R4. Interface contract shape

- **Decision**: Reuse the probe's GATT service/characteristic UUIDs; payload is
  `[0]=layer index (uint8)`, `[1]=modifier bitmask (uint8)`,
  `[2..N]=layer name (UTF-8, no NUL)`. Characteristic is `READ | NOTIFY` with a
  CCC descriptor; READ returns the current snapshot, NOTIFY pushes changes.
- **Rationale**: UUIDs already proven discoverable on macOS during the probe
  phase, so no re-validation risk. Variable-length name segment lets the contract
  grow (reserved bytes) without re-versioning, per Principle IV.
- **Alternatives considered**: Fixed 8-byte name field (rejected — wastes
  bandwidth, still arbitrary); single-byte fake layer index from probe (rejected
  — insufficient for the spec's layer-name requirement).

## R5. When to notify

- **Decision**: Recompute the full payload on layer or modifier change, compare to
  a cached copy, and only call `bt_gatt_notify` when it differs.
- **Rationale**: Satisfies SC-002 (zero redundant updates when idle) and
  Principle III (no extra on-air traffic / power draw when state is unchanged).
- **Alternatives considered**: Notify on every subscribed event (rejected —
  redundant traffic); periodic notify (rejected — idle traffic).

## R6. Host discovery of an already-connected keyboard

- **Decision**: Discover via
  `retrieveConnectedPeripherals(withServices:)` filtering on the keyboard's HID
  service plus the custom service, then select by name; remember the peripheral
  identifier for fast reconnect.
- **Rationale**: A connected BLE HID device stops advertising, so a normal scan
  will not find it. The probe phase confirmed this behavior on macOS.
- **Alternatives considered**: Active scanning by name (rejected — the device is
  not advertising while connected).

## R7. Drag vs click-through conflict

- **Decision**: Expose a persistent menu-bar toggle between "unlocked"
  (draggable, may intercept clicks) and "locked" (click-through, not draggable).
- **Rationale**: A borderless window made click-through (`ignoresMouseEvents`)
  cannot simultaneously be grabbed to drag — the two behaviors are mutually
  exclusive. Making it an explicit user choice is the only coherent resolution.
- **Alternatives considered**: Always draggable (rejected — blocks clicks
  beneath); always click-through (rejected — cannot be repositioned).

## R8. Firmware test strategy

- **Decision**: Rely on the GitHub Actions build for all `build.yaml` targets
  plus real-hardware verification using a reworked probe script that parses
  `[idx][mods][name]`.
- **Rationale**: ZMK provides no in-tree unit-test framework for shield code;
  build success plus on-device value checks is the established project pattern
  (mirrors the probe phase's verification loop).
- **Alternatives considered**: Native unit tests in Zephyr (`ztest`) for the
  shield (rejected — no harness in this config, disproportionate for the scope).

## R9. Host payload parsing robustness

- **Decision**: Parse defensively — reject payloads shorter than 2 bytes; on
  missing/undecodable layer name, fall back to a `L{index}` indicator.
- **Rationale**: Satisfies FR-014 and the spec's edge cases without crashing;
  keeps the panel meaningful even for malformed input.
- **Alternatives considered**: Trusting payload length (rejected — one bad packet
  shows wrong state).
