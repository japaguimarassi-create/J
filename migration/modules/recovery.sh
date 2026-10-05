#!/usr/bin/env bash
set -u
classify_restore_strategy() {
  local state="$1" output="$2"
  python3 - "$state" "$output" <<'PY'
import json,sys
s=json.load(open(sys.argv[1],encoding="utf-8"))
caps=s.get("capabilities",{})
if caps.get("CAN_RESTORE_OFFICIAL_FIRMWARE"):
    strategy="oem-firmware"
elif caps.get("CAN_FLASH_SYSTEM"):
    strategy="lokivolt-recovery"
else:
    strategy="metadata-only"
json.dump({"schema_version":1,"strategy":strategy,"destructive":strategy!="metadata-only","evidence_capabilities":caps},open(sys.argv[2],"w",encoding="utf-8"),sort_keys=True,indent=2)
PY
}
build_recovery_plan() {
  local state="$1" plan="$2" output="$3"
  python3 - "$state" "$plan" "$output" <<'PY'
import json,sys
s=json.load(open(sys.argv[1],encoding="utf-8"))
p=json.load(open(sys.argv[2],encoding="utf-8"))
caps=s.get("capabilities",{})
levels=[{"level":1,"name":"user-data","available":True},{"level":2,"name":"lokivolt-state","available":bool(caps.get("CAN_FLASH_SYSTEM"))},{"level":3,"name":"oem-firmware","available":bool(caps.get("CAN_RESTORE_OFFICIAL_FIRMWARE"))}]
json.dump({"schema_version":1,"source_state":s.get("state_id"),"plan_allowed":not p.get("destructive",False),"levels":levels,"requires_authorization":True},open(sys.argv[3],"w",encoding="utf-8"),sort_keys=True,indent=2)
PY
}
validate_recovery_plan() {
  python3 - "$1" <<'PY'
import json,sys
p=json.load(open(sys.argv[1],encoding="utf-8"))
if p.get("schema_version")!=1 or not p.get("requires_authorization"):
    raise SystemExit(1)
raise SystemExit(0)
PY
}
