#!/usr/bin/env bash
set -u

state_allowed() {
  local from="$1" to="$2"
  case "$from:$to" in
    INIT:PREFLIGHT|PREFLIGHT:INVENTORY|INVENTORY:VAULT_CREATE|VAULT_CREATE:CAPABILITY_ANALYSIS|CAPABILITY_ANALYSIS:PLAN|PLAN:WAITING_FOR_AUTHORIZATION|PLAN:ABORTED|WAITING_FOR_AUTHORIZATION:PREPARE|PREPARE:EXECUTE|EXECUTE:VERIFY|VERIFY:HEALTH_CHECK|HEALTH_CHECK:COMMIT|VERIFY:RECOVERY_PLAN|HEALTH_CHECK:RECOVERY_PLAN) return 0 ;;
    *) return 1 ;;
  esac
}

state_transition_file() {
  local file="$1" from="$2" to="$3"
  state_allowed "$from" "$to" || return 1
  python3 - "$file" "$from" "$to" <<'PY'
import json,sys
p,old,new=sys.argv[1:]
data=json.load(open(p,encoding="utf-8"))
if data.get("state")!=old:
    raise SystemExit(1)
data["state"]=new
json.dump(data,open(p,"w",encoding="utf-8"),sort_keys=True,indent=2)
PY
}
