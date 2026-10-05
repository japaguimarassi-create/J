#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
source "$ROOT/modules/jarvis_bridge.sh"
TMP="$(mktemp -d)"
printf '%s\n' '{"properties":{"ro.product.model":"moto g04s","ro.build.version.release":"14"},"boot":{"state":"locked","verified_boot_state":"green","slot":"_a"},"dynamic_partitions":false}' > "$TMP/inventory.json"
out="$(jarvis_explain_state "$TMP/inventory.json")"
printf '%s\n' "$out" | grep -q 'mutation=v1-disabled'
printf '%s\n' '{"profile":"motorola"}' > "$TMP/profile.json"
jarvis_request_plan "$TMP/inventory.json" "$TMP/profile.json" "$TMP/plan.json"
grep -q '"destructive": false' "$TMP/plan.json"
printf 'PASS: JARVIS bridge\n'
