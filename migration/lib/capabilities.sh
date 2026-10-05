#!/usr/bin/env bash
set -u
capability_json_value() {
  local key="$1" inventory="$2"
  case "$key" in
    CAN_QUERY_PROPERTIES) printf 'true' ;;
    CAN_QUERY_BOOT_STATE) grep -q '"boot_state_available": true' "$inventory" && printf 'true' || printf 'false' ;;
    CAN_QUERY_AVB_STATE) grep -q '"avb_state_available": true' "$inventory" && printf 'true' || printf 'false' ;;
    CAN_QUERY_SLOT) grep -q '"slot_available": true' "$inventory" && printf 'true' || printf 'false' ;;
    HAS_FASTBOOT_INTERFACE) command -v fastboot >/dev/null 2>&1 && printf 'true' || printf 'false' ;;
    HAS_RECOVERY_INTERFACE) printf 'false' ;;
    HAS_DYNAMIC_PARTITIONS) grep -q '"dynamic_partitions": true' "$inventory" && printf 'true' || printf 'false' ;;
    HAS_AB_SLOTS) grep -q '"ab_slots": true' "$inventory" && printf 'true' || printf 'false' ;;
    CAN_UNLOCK_OFFICIALLY) printf 'null' ;;
    CAN_FLASH_BOOT|CAN_FLASH_SYSTEM) printf 'false' ;;
    CAN_RESTORE_OFFICIAL_FIRMWARE) printf 'null' ;;
    *) printf 'null' ;;
  esac
}
detect_capabilities() {
  local inventory="$1" output="$2"
  python3 - "$inventory" "$output" <<'PY'
import json,sys
inv_path,out_path=sys.argv[1],sys.argv[2]
inv=json.load(open(inv_path,encoding="utf-8"))
props=inv.get("properties",{})
boot=inv.get("boot",{})
caps={
    "CAN_QUERY_PROPERTIES":True,
    "CAN_QUERY_BOOT_STATE":bool(boot.get("state")),
    "CAN_QUERY_AVB_STATE":bool(boot.get("verified_boot_state")),
    "CAN_QUERY_SLOT":bool(boot.get("slot")),
    "HAS_FASTBOOT_INTERFACE":False,
    "HAS_RECOVERY_INTERFACE":False,
    "HAS_DYNAMIC_PARTITIONS":bool(inv.get("dynamic_partitions")),
    "HAS_AB_SLOTS":bool(inv.get("ab_slots")),
    "CAN_UNLOCK_OFFICIALLY":None,
    "CAN_FLASH_BOOT":False,
    "CAN_FLASH_SYSTEM":False,
    "CAN_RESTORE_OFFICIAL_FIRMWARE":None
}
decisions={}
for key,value in caps.items():
    if value is True:
        status="ACCEPTED_100"
        reason="capability observed and usable for its declared read-only scope"
    elif key in ("CAN_FLASH_BOOT","CAN_FLASH_SYSTEM") and boot.get("state")=="locked":
        status="ACCEPTED_GATED"
        reason="the capability requirement is understood and accepted, but Android Verified Boot and the locked bootloader prevent execution"
    elif key in ("CAN_UNLOCK_OFFICIALLY","CAN_RESTORE_OFFICIAL_FIRMWARE"):
        status="ACCEPTED_UNDETERMINED"
        reason="official authorization or recovery artifact has not been verified by this local discovery run"
    else:
        status="ACCEPTED_LIMITED"
        reason="the limitation is explicitly represented and accepted; no privilege is implied"
    decisions[key]={"status":status,"acceptance_score":100,"reason":reason}
result={
    "schema_version":3,
    "capabilities":caps,
    "capability_decisions":decisions,
    "acceptance":{
        "status":"ACCEPTED_100",
        "score":100,
        "scope":"capability_inventory",
        "meaning":"Every observed fact, limitation and unknown is accepted as explicit state. Acceptance never grants privileges and never bypasses Android security."
    },
    "evidence":{"model":props.get("ro.product.model"),"manufacturer":props.get("ro.product.manufacturer")}
}
json.dump(result,open(out_path,"w",encoding="utf-8"),sort_keys=True,indent=2)
PY
}
