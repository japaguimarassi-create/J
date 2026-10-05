#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
source "$ROOT/modules/plan.sh"
source "$ROOT/modules/recovery.sh"
TMP="$(mktemp -d)"
printf '%s\n' '{"properties":{"ro.product.manufacturer":"motorola"},"boot":{"state":"locked"},"preflight":{"safe":true},"capabilities":{"CAN_QUERY_PROPERTIES":true}}' > "$TMP/inventory.json"
printf '%s\n' '{"profile":"motorola"}' > "$TMP/profile.json"
build_plan "$TMP/inventory.json" "$TMP/profile.json" "$TMP/plan.json"
grep -q '"destructive": false' "$TMP/plan.json"
grep -q '"requires_authorization": true' "$TMP/plan.json"
build_recovery_plan "$TMP/inventory.json" "$TMP/plan.json" "$TMP/recovery.json"
validate_recovery_plan "$TMP/recovery.json"
printf 'PASS: planner\n'
