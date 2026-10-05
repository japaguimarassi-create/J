#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
source "$ROOT/modules/plan.sh"
source "$ROOT/modules/recovery.sh"
TMP="$(mktemp -d)"
printf '%s
' '{"properties":{"ro.product.manufacturer":"motorola"},"boot":{"state":"locked"},"preflight":{"safe":true},"capabilities":{"CAN_QUERY_PROPERTIES":true,"HAS_FASTBOOT_INTERFACE":false,"CAN_UNLOCK_OFFICIALLY":false,"CAN_FLASH_BOOT":false,"CAN_FLASH_SYSTEM":false}}' > "$TMP/inventory.json"
printf '%s
' '{"profile":"motorola"}' > "$TMP/profile.json"
build_plan "$TMP/inventory.json" "$TMP/profile.json" "$TMP/plan.json"
grep -q '"destructive": false' "$TMP/plan.json"
grep -q '"requires_authorization": true' "$TMP/plan.json"
grep -q '"acceptance_score": 100' "$TMP/plan.json"
grep -q '"acceptance_status": "ACCEPTED_100"' "$TMP/plan.json"
grep -q '"security_boundary": "ENFORCED"' "$TMP/plan.json"
grep -q '"gate": "BOOTLOADER_LOCKED"' "$TMP/plan.json"
build_recovery_plan "$TMP/inventory.json" "$TMP/plan.json" "$TMP/recovery.json"
validate_recovery_plan "$TMP/recovery.json"
printf 'PASS: planner
'
