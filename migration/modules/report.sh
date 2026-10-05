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
print("Plan:", "allowed" if plan.get("allowed") else "blocked")
print("Authorization required:",bool(plan.get("requires_authorization")))
print("Recovery strategy:",[x.get("strategy") for x in [rec] if x.get("strategy")] or "metadata")
print("Capabilities:")
for k,v in sorted(caps.items()):
    print(f"  {k}={v}")
PY
}
