# Phase 0 Research: Multi-Keyboard Support

All decisions below resolve the Technical Context unknowns for feature 002. They build on
feature 001's research (R1–R9) and the as-built code. No open NEEDS CLARIFICATION remains.

## MR1. Keyboard name transport (self-reported identity)

- **Decision**: Use the keyboard's **BLE GAP device name** (ZMK `CONFIG_ZMK_KEYBOARD_NAME`,
  surfaced on macOS as `CBPeripheral.name`) as the self-reported display name. Document it in
  the contract as the identity source. **Do not** add a new GATT characteristic and **do not**
  change the status payload.
- **Rationale**:
  - Every ZMK keyboard already has a GAP name; reusing it means **zero per-keyboard porting
    burden** for the name (directly serves "easy to adapt" and keeps conformance trivial for
    feature 003).
  - The name arrives **free at discovery** (`retrieveConnectedPeripherals` returns `.name`),
    so FR-007 (no added per-change traffic) is satisfied with no read at all, and Principle III
    (no extra on-air traffic / power) holds.
  - It is literally the mechanism the current code already relies on to match `"TOTEM"`, so it
    is proven to work on macOS; we only remove the hardcoded match.
  - Keeps the payload frozen (spec "Payload unchanged" assumption) and avoids a breaking
    contract bump.
- **Alternatives considered**:
  - *Dedicated read-once "keyboard name" characteristic* — rejected for the MVP: adds firmware
    code, a coordinated contract change, and porting burden for every keyboard, for a name that
    the GAP name already provides. **Reserved** as a documented future extension if a keyboard
    ever needs a display name distinct from its BT name (fits the contract's reserved-growth
    rule, Principle IV).
  - *Appending the name to the status payload* — rejected: it would resend a static string on
    every change (violates FR-007 / Principle III).

## MR2. Host identification of a compatible keyboard (service UUID, not name)

- **Decision**: A device is a *compatible keyboard* iff it **exposes the custom status service
  UUID** (`AA440AA0-…`). Enumerate candidates with
  `retrieveConnectedPeripherals(withServices: [customServiceUUID, hidServiceUUID])`, then
  **confirm** by GATT service discovery after connecting (the existing
  `didDiscoverServices` check). Remove the `name.contains("TOTEM")` gate entirely.
- **Rationale**: A connected BLE HID keyboard stops advertising (feature 001 R6), so discovery
  must use connected-peripheral enumeration. macOS does not reliably report a *custom* service
  in the enumeration result for a bonded HID device until GATT discovery runs, so the HID
  service is kept in the query to reliably surface keyboards, and custom-service presence is the
  authoritative compatibility test confirmed on connect — exactly the proven 001 flow minus the
  name filter.
- **Alternatives considered**: Query by custom service only (rejected — may miss bonded
  keyboards whose custom service isn't cached in the enumeration); trust `.name`/advertising
  (rejected — connected devices don't advertise, and names are not a compatibility signal).

## MR3. Firmware kit packaging (reusable, shield-scoped)

- **Decision**: Create `config/keybeacon_kit/` containing the shared `keybeacon.c`, a
  `keybeacon.cmake` snippet (the guarded `zephyr_library` block), a `Kconfig.keybeacon`
  declaring a **generic** symbol `CONFIG_ZMK_KEYBEACON`, and a `README.md` porting guide. A
  shield consumes the kit with exactly two wire-up lines — `include(.../keybeacon.cmake)` in
  its `CMakeLists.txt` and `rsource`/`source` of `Kconfig.keybeacon` in its Kconfig — plus
  `CONFIG_ZMK_KEYBEACON=y` in the keyboard `.conf`. `keybeacon.c` is **never edited to
  port**. The Totem shield is refactored to be the reference consumer.
- **Rationale**: Keeps the feature shield-scoped so it can reach ZMK `app`-private headers via
  `zephyr_library_include_directories(${CMAKE_SOURCE_DIR}/include)` (feature 001 R1), while
  removing Totem branding (generic symbol) and eliminating logic duplication. "Copy a directory
  + wire two lines + enable one symbol" is the minimal, documented per-keyboard change
  (FR-009, SC-003) and leaves shared logic untouched.
- **Alternatives considered**:
  - *Standalone ZMK/west module* — rejected (001 R1: cannot reach `app`-private headers).
  - *Leave files in the Totem shield and copy wholesale* — rejected: duplicates the shared
    logic and keeps the Totem-named symbol; worse for multi-shield repos and for a clean
    porting story.
  - *Cross-shield `zephyr_library_sources` with no snippet* — rejected: fragile relative paths;
    the `.cmake` snippet encapsulates the guards and the kit path in one include.

## MR4. Stable identifier for "remember the selected keyboard"

- **Decision**: Persist `CBPeripheral.identifier.uuidString` (the macOS-stable per-device
  identifier) in `UserDefaults`. On launch, prefer the remembered identifier; reconnect via the
  enumeration result (match on identifier) or `retrievePeripherals(withIdentifiers:)`.
- **Rationale**: `CBPeripheral.identifier` is stable for a given Mac+device and is the
  documented key for reconnecting to known peripherals; the current code already caches it
  in-memory as `knownIdentifier`, so we only add persistence. Names are not unique (two
  identically named keyboards) so the identifier is the correct disambiguator (spec edge case).
- **Alternatives considered**: Remember by name (rejected — not unique, user-renameable); by BLE
  MAC (rejected — not exposed by CoreBluetooth).

## MR5. De-branding persisted settings + migration

- **Decision**: Rename the `UserDefaults` keys `totemPanelFrame*` → `panelFrame*` and
  `totemPanelLocked` → `panelLocked`, and introduce `selectedKeyboardIdentifier`. Perform a
  **one-time migration** on launch: for each new key that is absent while its legacy `totem*`
  counterpart exists, copy the legacy value forward, then mark migration done. Never reset
  existing users.
- **Rationale**: Satisfies FR-004 (no model-specific branding in stored data) and the "existing
  Totem users" edge case (position/lock preserved). A guarded copy-forward is the standard,
  low-risk `UserDefaults` migration.
- **Alternatives considered**: Hard rename with no migration (rejected — silently loses users'
  saved position/lock); keep `totem*` keys (rejected — leaves branding, violates FR-004).

## MR6. Multi-keyboard chooser UX

- **Decision**: Add a menu-bar **"Keyboard ▸"** submenu listing compatible keyboards by name
  with a checkmark on the active one. Auto-connect when exactly one compatible keyboard is
  present (FR-013) or when the remembered one is available (FR-015); when two or more are
  present and none is remembered, populate the submenu and connect only on explicit selection
  (FR-014). A single panel always tracks the active selection (FR-016); selecting another
  switches the single connection.
- **Rationale**: Reuses the existing menu-bar presence (feature 001) — the lowest-footprint
  surface for selection; keeps "single active keyboard + remember" semantics chosen in the
  spec's Clarifications.
- **Alternatives considered**: A separate window/picker (rejected — heavier than needed, the
  app is menu-bar-first); auto-pick first of several (rejected — the spec forbids silently
  guessing when multiple are present and none is remembered).

## MR7. Probe (developer verification) genericization

- **Decision**: Update `tools/probe.py` to discover by the custom service UUID (same rule as
  MR2) and drop the `"TOTEM"` name filter; keep the connected-peripheral enumeration and the
  scan fallback. Print the discovered keyboard's `.name` for confirmation.
- **Rationale**: FR-012 — verification tooling must identify by the contract so it works across
  keyboards; keeps probe and app behavior identical (same discovery rule), reducing drift.
- **Alternatives considered**: Leave the probe Totem-specific (rejected — can't verify other
  keyboards; contradicts the feature).
