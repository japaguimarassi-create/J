#!/usr/bin/env bash
set -u
set -o pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$ROOT/modules/partitions.sh"
source "$ROOT/modules/avb.sh"
fail(){ printf 'FAIL: %s\n' "$1" >&2; exit 1; }
TMP="$(mktemp -d)"
printf '%s\n' 'major minor  #blocks  name' > "$TMP/blocks"
export LOKIVOLT_BLOCK_SOURCE="$TMP/blocks"
inspect_block_devices "$TMP/block.txt" || fail "block inspection"
grep -q 'major minor' "$TMP/block.txt" || fail "block evidence"
printf '%s\n' '[ro.boot.slot_suffix]: [_a]' > "$TMP/props"
export PATH="$PATH"
inspect_slots "$TMP/slot.json" || fail "slot inspection"
grep -q '"active_slot":' "$TMP/slot.json" || fail "slot field"
inspect_verified_boot "$TMP/avb.json" || fail "AVB inspection"
grep -q '"schema_version": 1' "$TMP/avb.json" || fail "AVB schema"
printf 'PASS: platform inspection\n'
