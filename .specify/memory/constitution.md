# TOTEM ZMK Config Constitution

## Core Principles

### I. Interface Contract First

Any firmware↔host coupling MUST be expressed as an explicit, documented interface
contract (e.g. a GATT service/characteristic UUID set and its payload byte layout)
before either side is implemented. That contract is the single point of coupling:
once frozen, firmware and host MUST be developed and tested in parallel against it.
Every payload byte MUST have a documented meaning, endianness, and length rule;
unused capacity MUST be reserved rather than repurposed. A breaking change to an
already-shipped contract requires a coordinated version bump on both sides.

**Rationale**: The contract is the only thing two independently-built halves truly
share. Freezing it early keeps the codebases decoupled and lets them evolve without
lockstep rebuilds.

### II. Keyboard as Source of Truth

Firmware MUST report state that the host cannot derive on its own, and MUST derive
that state from authoritative ZMK APIs (keymap/layer/modifier sources) rather than
re-inventing it. State the host can obtain locally without privileged access SHOULD
NOT be duplicated over the wire unless the keyboard's value is strictly more
correct. Reported values MUST reflect live physical keyboard state, never a cached
or assumed one.

**Rationale**: The project exists to surface information the PC cannot self-acquire
(such as the active layer). Anything the host already knows cheaply is payload this
project does not need.

### III. Shield-Scoped, Minimal Footprint

Firmware changes MUST live in the shield scope and be gated behind an explicit
Kconfig symbol with correct `depends on` guards. Features meaningful only on the
central half MUST compile for the central role only; peripheral and `settings_reset`
builds MUST NOT carry them. Shield code MUST NOT depend on non-exported `app PRIVATE`
internals from a context that cannot reach them. Added firmware MUST NOT increase
on-air traffic or power draw when reported state has not changed.

**Rationale**: Unscoped firmware bloats builds that do not need it and risks
breaking the peripheral half or the reset image. Role- and symbol-gated changes keep
each build minimal and correct.

### IV. MVP Discipline (YAGNI)

Every development increment MUST declare a bounded scope with an explicit, written
list of non-goals. Non-goals MUST be deferred rather than silently half-implemented.
Extensibility MUST be achieved by reserving slack in an existing contract (e.g.
trailing payload bytes), never by pre-building unused features. A feature MUST be
added only when it has a concrete consumer and a stated rationale.

**Rationale**: Bounded scopes keep embedded and host code small, reviewable, and
shippable; reserved slack preserves room to grow without re-versioning.

### V. Hardware-Verified by CI

Every firmware change MUST build cleanly through the repository's declared build
targets before it is considered done, and MUST be validated against real hardware
behavior rather than compilation alone. Build configuration (e.g. `build.yaml`) and
shield definitions MUST stay in sync with the firmware they build. A change that
cannot pass the firmware build MUST NOT be merged.

**Rationale**: For embedded firmware, "compiles" is a floor, not a finish line; CI
plus on-device validation is the only trustworthy signal that a build will actually
run on the keyboard.

## Firmware & Platform Constraints

- Firmware targets ZMK on Zephyr; board/shield definitions, overlays, and Kconfig
  MUST follow ZMK conventions, and the build manifest MUST remain the single source
  of build targets.
- Device-tree bindings (modifiers, keycodes, layers) MUST use the canonical
  `dt-bindings/zmk/*` definitions instead of literal magic numbers.
- Host-side tooling that talks to hardware MUST depend only on the frozen interface
  contract (Principle I), not on firmware internals.
- Sources of truth (specs, contracts) MUST be recorded in the repository under
  version control, not left in external or ephemeral locations.

## Development Workflow

- Design before implementation: a feature MUST have a written design/spec artifact
  fixing goals, non-goals, and the interface contract before implementation starts.
- Risky assumptions MUST be resolved by an isolated spike/probe whose findings are
  recorded, so the design rests on verified behavior rather than speculation.
- Specs are the single source of truth for a feature's intent; when implementation
  diverges, the divergence MUST be reconciled by amending the spec, not by leaving
  the two out of sync.
- Reviews MUST verify each principle above; any deviation MUST be justified and
  recorded.

## Governance

This constitution supersedes other development practices when they conflict.
Amendments MUST be made by editing this document, MUST increment the version below
per semantic versioning, and MUST include a Sync Impact Report describing the change.
Versioning policy:

- MAJOR: backward-incompatible governance changes, or principle removals or
  redefinitions.
- MINOR: a new principle or section is added, or existing guidance is materially
  expanded.
- PATCH: clarifications, wording, or non-semantic refinements.

Every change MUST be reviewed for compliance with the principles; unjustified
complexity MUST be rejected or explicitly reasoned. The last-amended date MUST be
updated whenever this document changes.

**Version**: 1.0.0 | **Ratified**: 2026-10-05 | **Last Amended**: 2026-10-05
