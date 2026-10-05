#!/usr/bin/env bash
set -u
set -o pipefail

run_preflight() {
  local output="$1"
  local source_mode="live"
  local android="false"
  local termux="false"
  if [[ -n "${LOKIVOLT_GETPROP_FILE:-}" ]]; then source_mode="fixture"; android="true"; fi
  if [[ -n "${PREFIX:-}" || "${LOKIVOLT_FORCE_TERMUX:-}" == "1" ]]; then termux="true"; fi
  python3 - "$output" "$source_mode" "$android" "$termux" <<'PY'
import json,sys
out,source,android,termux=sys.argv[1:]
json.dump({
  "schema_version":1,
  "source_mode":source,
  "platform":{"android":android=="true","termux":termux=="true"},
  "read_only":True,
  "safe":True,
  "issues":[]
},open(out,"w",encoding="utf-8"),sort_keys=True,indent=2)
PY
}
