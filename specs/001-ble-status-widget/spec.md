# Feature Specification: BLE Keyboard Status Widget

**Feature Branch**: `001-ble-status-widget`

**Created**: 2026-10-05

**Status**: Draft

**Input**: User description: "docs/superpowers/specs/2026-10-05-ble-widget-mvp-design.md — ZMK BLE 桌面悬浮窗 MVP"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See the active layer on the desktop (Priority: P1)

A typist uses the split keyboard and wants to know, without looking down at the
keyboard, which layer is currently active. A small always-on-top panel on the
desktop shows the active layer's name (e.g. `BASE`, `NAVI`, `SYM`, `ADJ`) and
updates live as the layer changes.

**Why this priority**: The active layer is the one piece of state the computer
cannot determine on its own. This is the reason the feature exists; without it
there is no product.

**Independent Test**: Power on the keyboard and the panel, switch layers via the
keyboard, and confirm the displayed name tracks the real active layer. Delivers
value on its own as a live layer readout.

**Acceptance Scenarios**:

1. **Given** the panel is running and connected, **When** the keyboard is on its
   base layer, **Then** the panel shows the base layer's name.
2. **Given** the panel is showing a layer, **When** the user activates a
   different layer, **Then** the panel updates to the new layer's name without
   user interaction.
3. **Given** the user returns to a previously shown layer, **When** that layer
   becomes active again, **Then** the panel reflects it again.

---

### User Story 2 - See active modifier keys, merged by side (Priority: P2)

While typing combos, the user wants to see which modifier keys (Shift, Control,
Option, Command) are currently held. The panel shows the four modifiers on the
same row as the layer name; the left and right instances of a modifier are merged
into a single indicator, which is highlighted when active and dimmed when not,
in a fixed set of slots that never reflow.

**Why this priority**: Modifiers come free in the same status snapshot as the
layer (near-zero extra cost) and are reported by the keyboard itself rather than
inferred by the host. Valuable, but the feature is still useful without them.

**Independent Test**: Hold and release each modifier (including left/right
variants) and confirm the matching indicator highlights and un-highlights, with
both sides lighting the same indicator.

**Acceptance Scenarios**:

1. **Given** the panel is running, **When** the user holds either Shift key,
   **Then** the single Shift indicator is highlighted.
2. **Given** a modifier indicator is highlighted, **When** the user releases all
   matching modifier keys, **Then** the indicator returns to the dimmed state.
3. **Given** the panel is idle with no modifiers held, **When** the layout is
   displayed, **Then** all four modifier slots are visible in fixed positions.

---

### User Story 3 - Place and dock the panel without it getting in the way (Priority: P3)

The user wants to position the panel where it suits them and have it stay there,
including across restarts and display changes. Because a window that ignores
mouse clicks cannot also be grabbed to drag, the user needs an explicit
"locked / click-through" toggle: unlocked (default) allows dragging but the panel
may intercept clicks beneath it; locked makes the panel click-through so it never
blocks what is under it, at the cost of not being draggable.

**Why this priority**: Usability and non-interference matter, but the panel still
delivers its core readout even at the default position.

**Independent Test**: Drag the panel to a new position, restart it, and confirm
the position is restored; toggle click-through and confirm clicks pass through
(to and from under the panel) and that the locked state persists.

**Acceptance Scenarios**:

1. **Given** the panel is unlocked, **When** the user drags it to a new spot,
   **Then** it moves and remembers that position for the next launch.
2. **Given** the panel is locked (click-through), **When** the user clicks on a
   window beneath it, **Then** the click reaches that window and the panel does
   not move.
3. **Given** the panel is locked, **When** the user checks the toggle state after
   a restart, **Then** the locked state is preserved.
4. **Given** the user switches spaces or enters a full-screen app, **When** the
   panel is visible, **Then** it remains visible without stealing focus.

---

### User Story 4 - Trust the panel to stay connected and fail gracefully (Priority: P4)

The user wants the panel to recover on its own when the keyboard sleeps,
disconnects, or the computer's Bluetooth is toggled, and to never crash or show
misleading data. A menu-bar presence shows connection status and offers
reconnect / lock-toggle / quit.

**Why this priority**: Robustness and clear failure modes are required for a
always-on utility, but they refine an already-working readout.

**Independent Test**: Disconnect/reconnect the keyboard, toggle Bluetooth off and
on, and confirm the panel shows a clear "not connected" state, then recovers
automatically without crashing.

**Acceptance Scenarios**:

1. **Given** the panel is connected, **When** the keyboard disconnects, **Then**
   the panel shows a not-connected state and retries on an interval.
2. **Given** the panel is in the not-connected state, **When** the keyboard
   becomes available again, **Then** the panel reconnects and resumes live
   updates without user action.
3. **Given** Bluetooth is off or unavailable, **When** the app runs, **Then** the
   menu-bar presence indicates the problem and the app does not crash.
4. **Given** a malformed or truncated status message arrives, **When** the panel
   parses it, **Then** it is discarded rather than shown as bad data.

---

### Edge Cases

- Active layer has no name: the panel must still show a sensible fallback
  (e.g. a layer-number indicator) instead of a blank or broken state.
- Status payload shorter than the minimum expected length: discard defensively.
- Layer name that is not valid UTF-8: fall back to the layer-number indicator.
- Keyboard absent at launch: show not-connected and keep retrying.
- Display configuration changes (monitor added/removed): a previously saved
  position may fall outside visible bounds and must be brought back on-screen.
- Sustained idle (no layer/modifier change): the keyboard must not send redundant
  status updates, and the panel must remain stable.
- Rapid layer/modifier switching: the panel must keep up without missing the
  final state or flickering out of sync.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST display the name of the currently active layer and
  update it live as the active layer changes.
- **FR-002**: The system MUST display the current state of the four modifier
  keys (Shift, Control, Option, Command) as a fixed set of indicators that
  highlight when active.
- **FR-003**: The system MUST merge the left and right instances of each
  modifier into a single indicator.
- **FR-004**: The system MUST present the layer name and modifier indicators on
  one row with fixed, non-reflowing slots.
- **FR-005**: The system MUST derive all reported keyboard state from the
  keyboard itself as the source of truth, not from host-side inference.
- **FR-006**: The keyboard MUST expose a documented, versioned status snapshot
  containing the active layer (index and name) and the modifier bitmask as its
  interface to the host; the concrete encoding is fixed in the design document
  and MUST be frozen before firmware and host work proceed in parallel.
- **FR-007**: The keyboard side MUST send a status update only when the reported
  state has changed.
- **FR-008**: The panel MUST be an always-on-top window that does not steal focus
  and remains visible across spaces and full-screen apps.
- **FR-009**: The panel MUST be draggable in its unlocked state and MUST persist
  its position, restoring it on the next launch, with a sensible default
  position on first run.
- **FR-010**: The system MUST provide a user-toggleable lock (click-through)
  state that makes the panel pass mouse clicks through to whatever is beneath
  it; this state MUST persist across launches.
- **FR-011**: The system MUST present a menu-bar presence showing connection
  status with controls to reconnect, toggle the lock/click-through state, and
  quit.
- **FR-012**: The system MUST automatically detect a disconnected or unavailable
  keyboard, show a not-connected state, and retry connecting on an interval
  without user action.
- **FR-013**: The system MUST recover automatically when the keyboard reappears
  and MUST NOT crash when Bluetooth is off or unavailable.
- **FR-014**: The system MUST reject malformed or undersized status messages and
  MUST fall back to a layer-number indicator when a layer name is missing or
  undecodable.
- **FR-015**: The reported state MUST reflect live physical keyboard state; a
  stale or assumed value MUST NOT be shown as current.

### Key Entities

- **Status Snapshot**: The single unit of state the keyboard reports to the host
  — active layer (index + name) plus the modifier bitmask. This is the frozen
  interface contract between the two sides.
- **Layer**: A named keyboard layer (base, navigation, symbols, adjustment).
  Carries a display name that may be absent.
- **Modifier Set**: The four logical modifiers, each representing the merged
  left/right physical keys, with an active/inactive state.
- **Floating Panel**: The always-on-top desktop window showing the snapshot, with
  position and lock state that persist.
- **Connection State**: Whether the panel currently has a live link to the
  keyboard (connected / not connected / unavailable).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After a layer or modifier change, the panel reflects the new state
  fast enough to be perceived as immediate (target: within 1 second, for at
  least 95% of changes across a normal typing session).
- **SC-002**: Across a 1-hour idle session with no layer or modifier changes, the
  keyboard sends zero redundant status updates.
- **SC-003**: The panel correctly reflects active layer and modifier state for
  100% of changes in a scripted test that exercises all four layers and all eight
  physical modifier keys.
- **SC-004**: After a disconnect, the panel returns to a live updated state
  within 10 seconds of the keyboard becoming available again, with no user
  action.
- **SC-005**: Toggling Bluetooth off and on and disconnecting/reconnecting the
  keyboard across 20 cycles produces zero application crashes.
- **SC-006**: Panel position and lock state survive an application restart in
  100% of trials, and a saved position is always shown within visible screen
  bounds.
- **SC-007**: A user can position the panel and switch it between
  blocking/click-through modes using only the menu bar, with no configuration
  files or command line.

## Assumptions

- Target platform is a desktop OS whose user-space applications can discover,
  read, and subscribe to a custom service on a connected BLE HID keyboard
  without disrupting typing — validated in the project's probe phase.
- The keyboard's central half carries the reporting firmware; the peripheral
  half and the reset build do not.
- The keyboard has four layers with display names already defined
  (`BASE`/`NAVI`/`SYM`/`ADJ`); no keymap changes are required.
- Scope is bounded to a fixed, minimal set of indicators; the following are
  explicitly out of scope for this feature: battery level, output/BLE profile
  status, typing speed, HID lock-key indicators, animated mascots, launch at
  login, and any user-configurable layout or settings screen. The snapshot
  format leaves room to add such fields later without breaking the contract.
- No on-device unit-test framework exists for the firmware; firmware behavior is
  validated by build success plus real-hardware verification, while host-side
  parsing is covered by automated tests.
- The concrete interface encoding (service/characteristic identifiers and the
  exact byte layout) is governed by the existing design document and is treated
  as already frozen; this specification refers to it rather than redefining it.
