#!/usr/bin/env bash
set -u
set -o pipefail

run_preflight() {
  local output="$1"
  local source_mode="live"
  local android="false"
  local termux="false"
  local safe="false"
  local issues=""

  if [[ -n "${LOKIVOLT_GETPROP_FILE:-}" && -f "$LOKIVOLT_GETPROP_FILE" ]]; then
    source_mode="fixture"
    android="true"
    safe="true"
  elif command -v getprop >/dev/null 2>&1; then
    android="true"
    if [[ -n "${PREFIX:-}" ]]; then
      termux="true"
      safe="true"
    else
      issues="TERMUX_CONTEXT_NOT_CONFIRMED"
    fi
  else
    issues="ANDROID_GETPROP_NOT_FOUND"
  fi

  python3 - "$output" "$source_mode" "$android" "$termux" "$safe" "$issues" <<'PY'
import json,sys
out,source,android,termux,safe,issues=sys.argv[1:]
json.dump({
  "schema_version":1,
  "source_mode":source,
  "platform":{"android":android=="true","termux":termux=="true"},
  "read_only":True,
  "safe":safe=="true",
  "issues":[x for x in issues.split(",") if x]
},open(out,"w",encoding="utf-8"),sort_keys=True,indent=2)
PY
}
