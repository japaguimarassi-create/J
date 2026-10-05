#!/usr/bin/env bash
set -u
inspect_block_devices() {
  local output="$1"
  if [[ -n "${LOKIVOLT_BLOCK_SOURCE:-}" && -f "$LOKIVOLT_BLOCK_SOURCE" ]]; then
    cp "$LOKIVOLT_BLOCK_SOURCE" "$output"
    return 0
  fi
  if [[ -r /proc/partitions ]]; then
    cat /proc/partitions > "$output"
    return 0
  fi
  : > "$output"
}
inspect_dynamic_partitions() {
  local output="$1"
  local evidence="${LOKIVOLT_PARTITION_METADATA:-}"
  python3 - "$output" "$evidence" <<'PY'
import json,sys
out,evidence=sys.argv[1:]
dynamic=False
if evidence:
    try:
        data=json.load(open(evidence,encoding="utf-8"))
        dynamic=bool(data.get("dynamic_partitions"))
    except Exception:
        dynamic=False
json.dump({"schema_version":1,"dynamic_partitions":dynamic,"evidence_file":evidence or None},open(out,"w",encoding="utf-8"),sort_keys=True,indent=2)
PY
}
inspect_slots() {
  local output="$1"
  local value="${LOKIVOLT_SLOT:-}"
  if [[ -z "$value" && -n "${LOKIVOLT_GETPROP_FILE:-}" && -f "$LOKIVOLT_GETPROP_FILE" ]]; then
    value="$(awk -F'[][]' '/ro.boot.slot_suffix/ {print $4; exit}' "$LOKIVOLT_GETPROP_FILE")"
  fi
  if [[ -z "$value" ]]; then value="$(getprop ro.boot.slot_suffix 2>/dev/null || true)"; fi
  python3 - "$output" "$value" <<'PY'
import json,sys
out,value=sys.argv[1:]
json.dump({"schema_version":1,"ab_slots":bool(value),"active_slot":value or None},open(out,"w",encoding="utf-8"),sort_keys=True,indent=2)
PY
}
