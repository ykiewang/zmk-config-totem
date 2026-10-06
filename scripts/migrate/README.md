<!--
Copyright (c) 2026 The TOTEM ZMK Contributors
SPDX-License-Identifier: MIT
-->

# Migration tooling — firmware repo → standalone app repo

> **Status: RETIRED (seeding complete).** The app repo has been seeded and the split executed; this
> directory is kept for traceability only. Do **not** re-run `split-app-repo.sh` against the live
> app repo — it would recreate a seed tree over real history.

One-time tooling that seeds the standalone **KeyBeacon app repo**
(`github.com/ykiewang/keybeacon`) from this firmware repo, per feature 003 (research R2).

## `split-app-repo.sh`

History-preserving split of the macOS app into the app repo:

| Source (this repo) | Destination (app repo) | How |
|--------------------|------------------------|-----|
| `host/macos/` | `app/macos/` | `git subtree split` — **commit history preserved** |
| `specs/003-standalone-app-and-protocol/protocol/` | `protocol/` | seeded fresh (content copied by the protocol tasks) |
| `tools/probe.py` | `conformance/` | seeded fresh (evolved by the conformance tasks) |

Only `host/macos/` carries real multi-feature history (001/002), so it is the one path
that is split. `protocol/` and `conformance/` are newly authored in the app repo (their
editorial history would be a single commit), so they are seeded by their own tasks rather
than split.

### Run

```bash
scripts/migrate/split-app-repo.sh --dry-run      # show the plan, change nothing
scripts/migrate/split-app-repo.sh                # produce ../keybeacon (or $KEYBEACON_DEST)
```

The script stops **before** pushing. The push to the public repo is a maintainer action
(requires GitHub auth):

```bash
git -C ../keybeacon push -u origin main
git -C ../keybeacon push origin protocol-v1.0.0   # the pinnable protocol tag
git -C ../keybeacon push origin app-v0.1.0         # triggers the first release build
```

## After migration is verified

- The firmware repo removes `host/macos/` (it now lives in the app repo) and keeps
  `tools/probe.py` as a developer probe — see feature 003 task T030.
- This `scripts/migrate/` directory is **retired** once the app repo is seeded and pushed;
  it is kept in history for traceability.
