#!/usr/bin/env bash
set -u
build_plan() {
  local inventory="$1" profile="$2" output="$3"
  python3 - "$inventory" "$profile" "$output" <<'PY'
import json,sys
inv=json.load(open(sys.argv[1],encoding="utf-8"))
prof=json.load(open(sys.argv[2],encoding="utf-8"))
caps=inv.get("capabilities") or {}
blocked=[]
actions=[]
if not inv.get("preflight",{}).get("safe",True):
    blocked.append({"code":"PREFLIGHT_UNSAFE","reason":"preflight reported unsafe state"})
if not inv.get("boot",{}).get("state"):
    blocked.append({"code":"BOOT_STATE_UNKNOWN","reason":"bootloader state is unknown"})
if any(k in caps and caps[k] is False for k in ("CAN_QUERY_PROPERTIES",)):
    blocked.append({"code":"CAPABILITY_MISSING","reason":"required capability unavailable"})
actions.append({"id":"discover","mode":"read-only","status":"allowed"})
actions.append({"id":"prepare-flash","mode":"state-changing","status":"blocked","reason":"v1 mutation phase is disabled"})
result={
 "schema_version":1,
 "profile":prof.get("profile","generic"),
 "mode":"dry-run",
 "requires_authorization":True,
 "allowed":not blocked,
 "blocked_reasons":blocked,
 "actions":actions,
 "destructive":False
}
json.dump(result,open(sys.argv[3],"w",encoding="utf-8"),sort_keys=True,indent=2)
PY
}
plan_requires_authorization() { grep -q '"requires_authorization": true' "$1"; }
plan_is_safe() { grep -q '"destructive": false' "$1"; }
