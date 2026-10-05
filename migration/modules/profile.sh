#!/usr/bin/env bash
set -u
resolve_profile() {
  local inventory="$1" output="$2"
  python3 - "$inventory" "$output" <<'PY'
import json,sys
inv=json.load(open(sys.argv[1],encoding="utf-8"))
manufacturer=str(inv.get("properties",{}).get("ro.product.manufacturer") or "").lower()
profile="motorola" if manufacturer=="motorola" else "generic"
base={"schema_version":1,"profile":profile,"manufacturer":manufacturer or None}
json.dump(base,open(sys.argv[2],"w",encoding="utf-8"),sort_keys=True,indent=2)
PY
}
profile_capability() {
  local profile="$1" key="$2"
  case "$profile:$key" in
    generic:CAN_QUERY_PROPERTIES|motorola:CAN_QUERY_PROPERTIES) printf 'true' ;;
    *) printf 'false' ;;
  esac
}
