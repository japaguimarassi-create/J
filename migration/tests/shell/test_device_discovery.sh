#!/usr/bin/env bash
set -u
set -o pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$ROOT/modules/device.sh"
source "$ROOT/modules/preflight.sh"
source "$ROOT/lib/capabilities.sh"
fail(){ printf 'FAIL: %s\n' "$1" >&2; exit 1; }
TMP="$(mktemp -d)"
cat > "$TMP/props" <<'PROPS'
[ro.product.model]: [moto g04s]
[ro.product.manufacturer]: [motorola]
[ro.build.version.release]: [14]
[ro.boot.verifiedbootstate]: [green]
[ro.boot.slot_suffix]: [_a]
PROPS
export LOKIVOLT_GETPROP_FILE="$TMP/props"
collect_device_properties "$TMP/raw" >/dev/null || fail "property collection"
grep -q 'ro.product.model' "$TMP/raw/getprop.raw" || fail "raw properties recorded"
collect_inventory "$TMP/raw" "$TMP/inventory.json" || fail "inventory"
grep -Eq '"collected_at": "[^"]+"' "$TMP/inventory.json" || fail "collection timestamp"
run_preflight "$TMP/preflight.json" || fail "preflight"
grep -q '"read_only": true' "$TMP/preflight.json" || fail "read-only preflight"
cat > "$TMP/inventory.json" <<'JSON'
{
  "properties": {
    "ro.product.model": "moto g04s",
    "ro.product.manufacturer": "motorola"
  },
  "boot": {
    "state": "locked",
    "verified_boot_state": "green",
    "slot": "_a"
  },
  "dynamic_partitions": false,
  "ab_slots": true
}
JSON
detect_capabilities "$TMP/inventory.json" "$TMP/capabilities.json" || fail "capability detection"
grep -q '"HAS_AB_SLOTS": true' "$TMP/capabilities.json" || fail "A/B detection"
grep -q '"HAS_DYNAMIC_PARTITIONS": false' "$TMP/capabilities.json" || fail "dynamic partition detection"
printf 'PASS: device discovery\n'
