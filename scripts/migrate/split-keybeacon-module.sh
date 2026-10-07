#!/usr/bin/env bash
#
# split-keybeacon-module.sh — history-preserving extraction of config/keybeacon_kit/
# into the standalone zmk-keybeacon Zephyr module repo (feature 005 / research R4).
#
# Copyright (c) 2026 The TOTEM ZMK Contributors
# SPDX-License-Identifier: MIT
#
# What it does:
#   - `git subtree split` config/keybeacon_kit/ into a branch, preserving the commit
#     history of keybeacon.c and its siblings, then seeds a fresh `zmk-keybeacon`
#     working tree whose ROOT is that content (zephyr/module.yml, CMakeLists.txt,
#     keybeacon.c, keybeacon.cmake, Kconfig.keybeacon, README.md, GETTING-STARTED.md,
#     CHANGELOG.md).
#
# The final `git push` + `v1.0.0` tag is a maintainer action (requires GitHub auth)
# and is intentionally NOT performed here — see the printed next steps.
#
# Usage:
#   scripts/migrate/split-keybeacon-module.sh [--dry-run]
#   KEYBEACON_MODULE_DEST=/path/to/zmk-keybeacon scripts/migrate/split-keybeacon-module.sh
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FW_REPO="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
DEST="${KEYBEACON_MODULE_DEST:-$(cd "$FW_REPO/.." && pwd)/zmk-keybeacon}"
ORIGIN="https://github.com/ykiewang/zmk-keybeacon.git"
PREFIX="config/keybeacon_kit"

DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

echo "Firmware repo : $FW_REPO"
echo "Module dest   : $DEST"
echo "Origin        : $ORIGIN"
echo "Split prefix  : $PREFIX/  ->  module repo ROOT"
echo

if [[ ! -d "$FW_REPO/$PREFIX" ]]; then
  echo "ERROR: $PREFIX/ not found in $FW_REPO — nothing to split." >&2
  exit 1
fi

if $DRY_RUN; then
  echo "[dry-run] planned subtree split of $PREFIX; no changes made."
  exit 0
fi

echo "==> 1/3 subtree split $PREFIX -> branch split-keybeacon (history preserved)"
git -C "$FW_REPO" branch -D split-keybeacon 2>/dev/null || true
git -C "$FW_REPO" subtree split -P "$PREFIX" -b split-keybeacon >/dev/null
echo "    done ($(git -C "$FW_REPO" rev-list --count split-keybeacon) commits)"

echo "==> 2/3 initialize module repo working tree at $DEST (root = kit content)"
rm -rf "$DEST"
git init -q -b main "$DEST"
git -C "$DEST" remote add origin "$ORIGIN"
git -C "$DEST" fetch -q "$FW_REPO" split-keybeacon
git -C "$DEST" reset -q --hard FETCH_HEAD

echo "==> 3/3 verify module layout at the root"
missing=0
for f in zephyr/module.yml CMakeLists.txt keybeacon.c keybeacon.cmake Kconfig.keybeacon; do
  if [[ -f "$DEST/$f" ]]; then echo "    ok       $f"; else echo "    MISSING  $f" >&2; missing=1; fi
done
[[ "$missing" == 0 ]] || { echo "ERROR: module layout incomplete." >&2; exit 1; }

echo
echo "Done. Module root carries preserved history:"
git -C "$DEST" log --oneline -5 | sed 's/^/    /'
echo
echo "Next steps (maintainer action — requires GitHub auth, NOT done here):"
echo "  - create the empty repo github.com/ykiewang/zmk-keybeacon"
echo "  - git -C \"$DEST\" push -u origin main"
echo "  - git -C \"$DEST\" tag v1.0.0 && git -C \"$DEST\" push origin v1.0.0"
echo
echo "Only after v1.0.0 is published can the firmware repo safely:"
echo "  - add west.yml pinning zmk-keybeacon v1.0.0        (task T012)"
echo "  - remove the include()/rsource lines from the Totem shield (T013/T014)"
echo "  - delete config/keybeacon_kit/ from this repo       (task T018)"
