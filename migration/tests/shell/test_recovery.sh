#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
source "$ROOT/modules/recovery.sh"
TMP="$(mktemp -d)"
printf '%s\n' '{"capabilities":{}}' > "$TMP/state.json"
printf '%s\n' '{"destructive":false}' > "$TMP/plan.json"
classify_restore_strategy "$TMP/state.json" "$TMP/strategy.json"
grep -q '"strategy": "metadata-only"' "$TMP/strategy.json"
build_recovery_plan "$TMP/state.json" "$TMP/plan.json" "$TMP/recovery.json"
validate_recovery_plan "$TMP/recovery.json"
printf 'PASS: recovery\n'
