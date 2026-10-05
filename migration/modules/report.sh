#!/usr/bin/env bash
set -u
print_discovery_report() {
  local inventory="$1" plan="$2" recovery="$3"
  python3 - "$inventory" "$plan" "$recovery" <<'PY'
import json,sys
inv=json.load(open(sys.argv[1],encoding="utf-8"))
plan=json.load(open(sys.argv[2],encoding="utf-8"))
rec=json.load(open(sys.argv[3],encoding="utf-8"))
p=inv.get("properties",{})
b=inv.get("boot",{})
caps=inv.get("capabilities",{})
decisions=inv.get("capability_decisions",{})
print("=== LOKIVOLT DISCOVERY ===")
print("Model:",p.get("ro.product.model") or "unknown")
print("Manufacturer:",p.get("ro.product.manufacturer") or "unknown")
print("Android:",p.get("ro.build.version.release") or "unknown")
print("Security patch:",p.get("ro.build.version.security_patch") or "unknown")
print("ABI:",p.get("ro.product.cpu.abi") or "unknown")
print("Bootloader:",b.get("state") or "unknown")
print("Verified boot:",b.get("verified_boot_state") or "unknown")
print("Slot:",b.get("slot") or "unknown")
print("A/B:",bool(inv.get("ab_slots")))
print("Dynamic partitions:",bool(inv.get("dynamic_partitions")))
planning=plan.get("planning",{})
execution=plan.get("execution",{})
print("Planning acceptance:", "100% ACCEPTED" if planning.get("acceptance_status")=="ACCEPTED_100" else "NOT ACCEPTED")
print("Planning score:",f"{planning.get('acceptance_score',0)}%")
print("Execution authorization:",execution.get("status") or "UNKNOWN")
print("Execution gate:",execution.get("gate") or "none")
print("Partition writes:", "DISABLED" if execution.get("partition_writes_enabled") is False else "UNKNOWN")
print("Authorization required:",bool(execution.get("requires_authorization",plan.get("requires_authorization"))))
print("Security boundary:",plan.get("security_boundary") or "unknown")
print("Recovery strategy:",rec.get("strategy") or "metadata")
print("Capabilities:")
for k,v in sorted(caps.items()):
    d=decisions.get(k,{})
    label=d.get("status","ACCEPTED_LIMITED") if isinstance(d,dict) else "ACCEPTED_LIMITED"
    print(f"  {k}={v} [{label}]")
PY
}
