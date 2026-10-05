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
print("Plan:", "ACCEPTED 100%" if planning.get("acceptance_status")=="ACCEPTED_100" else ("allowed" if plan.get("allowed") else "blocked"))
print("Plan score:",f"{planning.get('acceptance_score',0)}%")
print("Execution:",execution.get("status") or "unknown")
print("Execution gate:",execution.get("gate") or "none")
print("Authorization required:",bool(execution.get("requires_authorization",plan.get("requires_authorization"))))
print("Security boundary:",plan.get("security_boundary") or "unknown")
print("Recovery strategy:",[x.get("strategy") for x in [rec] if x.get("strategy")] or "metadata")
print("Capabilities:")
for k,v in sorted(caps.items()):
    d=decisions.get(k,{})
    label=d.get("status","OBSERVED") if isinstance(d,dict) else "OBSERVED"
    print(f"  {k}={v} [{label}]")
PY
}
