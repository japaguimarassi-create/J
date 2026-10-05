#!/usr/bin/env bash
set -u
build_plan() {
  local inventory="$1" profile="$2" output="$3"
  python3 - "$inventory" "$profile" "$output" <<'PY'
import json,sys
inv=json.load(open(sys.argv[1],encoding="utf-8"))
prof=json.load(open(sys.argv[2],encoding="utf-8"))
caps=inv.get("capabilities") or {}
boot=inv.get("boot") or {}
advisories=[]
if not inv.get("preflight",{}).get("safe",True):
    advisories.append({"code":"PREFLIGHT_UNSAFE","reason":"preflight reported unsafe state","severity":"execution-gate"})
if not boot.get("state"):
    advisories.append({"code":"BOOT_STATE_UNKNOWN","reason":"bootloader state is unknown","severity":"execution-gate"})
if caps.get("CAN_QUERY_PROPERTIES") is False:
    advisories.append({"code":"CAPABILITY_MISSING","reason":"required property query capability unavailable","severity":"execution-gate"})
if boot.get("state") == "locked":
    execution_gate="BOOTLOADER_LOCKED"
elif not caps.get("HAS_FASTBOOT_INTERFACE"):
    execution_gate="FLASH_INTERFACE_UNAVAILABLE"
elif not caps.get("CAN_UNLOCK_OFFICIALLY"):
    execution_gate="OFFICIAL_UNLOCK_PATH_UNAVAILABLE"
else:
    execution_gate="REQUIRES_EXPLICIT_AUTHORIZATION"
planning_ready=bool(inv.get("preflight",{}).get("safe",False)) and bool(boot.get("state")) and caps.get("CAN_QUERY_PROPERTIES",False)
actions=[
    {"id":"discover","mode":"read-only","status":"accepted","acceptance_score":100,"execution":"available"},
    {"id":"prepare-flash","mode":"state-changing","status":"accepted","acceptance_score":100,"execution":"gated","gate":execution_gate,"reason":"Lokivolt accepts the requested migration plan, but Android platform authorization and device execution prerequisites remain separate."}
]
result={
    "schema_version":2,
    "profile":prof.get("profile","generic"),
    "mode":"dry-run",
    "planning":{"allowed":planning_ready,"acceptance_status":"ACCEPTED_100","acceptance_score":100,"scope":"plan_and_architecture","advisories":advisories},
    "execution":{"status":"GATED","ready":False,"gate":execution_gate,"requires_authorization":True,"requires_official_device_path":True,"partition_writes_enabled":False},
    "requires_authorization":True,
    "allowed":planning_ready,
    "blocked_reasons":advisories,
    "actions":actions,
    "destructive":False,
    "security_boundary":"ENFORCED"
}
json.dump(result,open(sys.argv[3],"w",encoding="utf-8"),sort_keys=True,indent=2)
PY
}
plan_requires_authorization() { grep -q '"requires_authorization": true' "$1"; }
plan_is_safe() { grep -q '"destructive": false' "$1"; }
