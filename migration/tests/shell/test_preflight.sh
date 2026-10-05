#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
source "$ROOT/modules/preflight.sh"
TMP="$(mktemp -d)"
bash -c 'unset PREFIX; unset LOKIVOLT_GETPROP_FILE; source "$1"; run_preflight "$2"' _ "$ROOT/modules/preflight.sh" "$TMP/live.json"
grep -q '"safe": false' "$TMP/live.json" || { printf 'FAIL: unsafe host accepted\n' >&2; exit 1; }
printf '%s\n' '[ro.product.model]: [fixture]' > "$TMP/props"
export LOKIVOLT_GETPROP_FILE="$TMP/props"
run_preflight "$TMP/fixture.json"
grep -q '"safe": true' "$TMP/fixture.json" || { printf 'FAIL: fixture rejected\n' >&2; exit 1; }
printf 'PASS: preflight\n'
