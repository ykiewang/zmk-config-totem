#!/usr/bin/env bash
#
# verify-protocol-pin.sh — prove the firmware's vendored KeyBeacon Protocol (KBP)
# snapshot is intact and has not diverged from the authoritative standard.
#
# Copyright (c) 2026 The TOTEM ZMK Contributors
# SPDX-License-Identifier: MIT
#
# Two layers (contract specs/003-.../contracts/firmware-pin.md §3):
#   1. OFFLINE integrity (ALWAYS): sha256(KBP.md) == kbp.lock:snapshot_sha256, and
#      the version declared inside KBP.md == kbp.lock:kbp_version.
#   2. ONLINE equality (WHEN reachable): fetch protocol/README.md @ source_ref from
#      source_repo and diff vs KBP.md. Unreachable ⇒ soft-skip (never fail just
#      because the app repo is offline — preserves the standalone-build guarantee).
#
# Exit codes:  0 = pin verified   1 = integrity/version/diff mismatch   2 = malformed lock
#
# Runs as a NON-firmware CI job (no board build needed) and locally with stock tools.

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PINNED="$ROOT/protocol-pinned"
KBP="$PINNED/KBP.md"
LOCK="$PINNED/kbp.lock"

die_malformed() { echo "FAIL(2): malformed kbp.lock — $1" >&2; exit 2; }
die_mismatch()  { echo "FAIL(1): $1" >&2; exit 1; }

[[ -f "$KBP"  ]] || die_malformed "missing snapshot $KBP"
[[ -f "$LOCK" ]] || die_malformed "missing lock $LOCK"

lock_get() {
  # key: value  (YAML-ish, single line). Trims surrounding whitespace.
  sed -n -E "s/^$1:[[:space:]]*([^[:space:]].*)$/\1/p" "$LOCK" | head -n1
}

KBP_VERSION="$(lock_get kbp_version)"
SOURCE_REPO="$(lock_get source_repo)"
SOURCE_REF="$(lock_get source_ref)"
SOURCE_COMMIT="$(lock_get source_commit)"
SNAPSHOT_SHA256="$(lock_get snapshot_sha256)"

for kv in kbp_version:"$KBP_VERSION" source_repo:"$SOURCE_REPO" \
          source_ref:"$SOURCE_REF" source_commit:"$SOURCE_COMMIT" \
          snapshot_sha256:"$SNAPSHOT_SHA256"; do
  [[ -n "${kv#*:}" ]] || die_malformed "missing field '${kv%%:*}'"
done
[[ "$SOURCE_REF" == protocol-v* ]] || die_malformed "source_ref must be a protocol-vX.Y.Z tag, got '$SOURCE_REF'"
echo "$SNAPSHOT_SHA256" | grep -Eq '^[0-9a-f]{64}$' || die_malformed "snapshot_sha256 is not 64 hex chars"

sha256_of() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}'
  elif command -v shasum  >/dev/null 2>&1; then shasum -a 256 "$1" | awk '{print $1}'
  else echo "no sha256 tool (need sha256sum or shasum)" >&2; return 3; fi
}

# ---- 1. OFFLINE integrity (always) ----
ACTUAL_SHA="$(sha256_of "$KBP")" || exit 2
if [[ "$ACTUAL_SHA" != "$SNAPSHOT_SHA256" ]]; then
  die_mismatch "snapshot hash mismatch
  expected $SNAPSHOT_SHA256
  actual   $ACTUAL_SHA
  (protocol-pinned/KBP.md was edited independently of the pinned standard)"
fi

# Version declared inside KBP.md, e.g. '**Version**: 1.0.0 · ...'
DECLARED_VERSION="$(grep -m1 -E '^\*\*Version\*\*' "$KBP" \
  | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -n1)"
[[ -n "$DECLARED_VERSION" ]] || die_mismatch "could not read a version from KBP.md"
if [[ "$DECLARED_VERSION" != "$KBP_VERSION" ]]; then
  die_mismatch "version mismatch: KBP.md declares $DECLARED_VERSION, kbp.lock pins $KBP_VERSION"
fi
echo "OK offline: sha256 matches, KBP.md declares $DECLARED_VERSION == pinned $KBP_VERSION"

# ---- 2. ONLINE equality (best-effort) ----
# https://github.com/OWNER/REPO(.git) -> raw.githubusercontent.com/OWNER/REPO/<ref>/protocol/README.md
slug="${SOURCE_REPO#*github.com[:/]}"; slug="${slug%.git}"
RAW_URL="https://raw.githubusercontent.com/${slug}/${SOURCE_REF}/protocol/README.md"

if ! command -v curl >/dev/null 2>&1; then
  echo "online check skipped (offline): curl not available"; echo "RESULT: pin verified (offline)"; exit 0
fi
TMP="$(mktemp)"; trap 'rm -f "$TMP"' EXIT
if curl -fsSL --max-time 20 "$RAW_URL" -o "$TMP" 2>/dev/null; then
  if diff -u "$KBP" "$TMP" >/dev/null; then
    echo "OK online: KBP.md is byte-identical to protocol/README.md @ $SOURCE_REF"
    echo "RESULT: pin verified (offline + online)"; exit 0
  fi
  echo "---- diff (pinned vs upstream @ $SOURCE_REF) ----" >&2
  diff -u "$KBP" "$TMP" >&2 || true
  die_mismatch "firmware snapshot has DIVERGED from the authoritative standard at $SOURCE_REF"
else
  echo "online check skipped (offline): could not fetch $RAW_URL"
  echo "RESULT: pin verified (offline)"; exit 0
fi
