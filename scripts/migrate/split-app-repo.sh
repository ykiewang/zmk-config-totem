#!/usr/bin/env bash
#
# split-app-repo.sh — history-preserving migration of the KeyBeacon app assets
# out of this firmware repo and into the standalone app repo (feature 003 / R2).
#
# Copyright (c) 2026 The TOTEM ZMK Contributors
# SPDX-License-Identifier: MIT
#
# What it does:
#   - `git subtree split` the macOS app (host/macos/) into a branch, preserving its
#     commit history, then seeds a fresh `keybeacon` working tree with that history
#     mapped to app/macos/.
#   - protocol/ and conformance/ are seeded fresh by their own feature-003 tasks
#     (protocol content is copied from specs/.../protocol/; conformance evolves from
#     tools/probe.py) — their editorial history is short/new, so they are not split.
#
# The final `git push` to the public repo is a maintainer action (requires GitHub
# auth) and is intentionally NOT performed here — see the printed next steps.
#
# Usage:
#   scripts/migrate/split-app-repo.sh [--dry-run]
#   KEYBEACON_DEST=/path/to/keybeacon scripts/migrate/split-app-repo.sh
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FW_REPO="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
DEST="${KEYBEACON_DEST:-$(cd "$FW_REPO/.." && pwd)/keybeacon}"
ORIGIN="https://github.com/ykiewang/keybeacon.git"

DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

echo "Firmware repo : $FW_REPO"
echo "Keybeacon dest: $DEST"
echo "Origin        : $ORIGIN"
echo
echo "History-preserving mapping (git subtree):"
echo "  host/macos/   ->  app/macos/     (commits kept)"
echo "Seeded fresh by feature-003 tasks (not split):"
echo "  specs/003-standalone-app-and-protocol/protocol/  ->  protocol/"
echo "  tools/probe.py                                    ->  conformance/ (evolved)"
echo

if [[ ! -d "$FW_REPO/host/macos" ]]; then
  echo "ERROR: host/macos/ not found in $FW_REPO — nothing to split." >&2
  exit 1
fi

if $DRY_RUN; then
  echo "[dry-run] planned subtree split of host/macos; no changes made."
  exit 0
fi

echo "==> 1/3 subtree split host/macos -> branch split-macos"
git -C "$FW_REPO" branch -D split-macos 2>/dev/null || true
git -C "$FW_REPO" subtree split -P host/macos -b split-macos >/dev/null
echo "    done ($(git -C "$FW_REPO" rev-list --count split-macos) commits)"

echo "==> 2/3 initialize app repo working tree at $DEST"
rm -rf "$DEST"
git init -q -b main "$DEST"
git -C "$DEST" remote add origin "$ORIGIN"
git -C "$DEST" remote add fw "$FW_REPO"
git -C "$DEST" fetch -q fw split-macos
git -C "$DEST" commit -q --allow-empty -m "chore: initialize KeyBeacon app repo"

echo "==> 3/3 graft host/macos history at app/macos/"
git -C "$DEST" subtree add -q --prefix=app/macos fw split-macos
git -C "$DEST" remote remove fw

echo
echo "Done. app/macos/ carries preserved history:"
git -C "$DEST" log --oneline -5 -- app/macos | sed 's/^/    /'
echo
echo "Next steps (performed by feature-003 tasks, then a maintainer push):"
echo "  - seed protocol/, conformance/, packaging/, .github/, README, LICENSE"
echo "  - git -C \"$DEST\" push -u origin main"
echo "  - git -C \"$DEST\" push origin protocol-v1.0.0   # after the protocol tag is cut"
