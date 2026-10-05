#!/usr/bin/env bash
set -u

jarvis_explain_state() {
  local inventory="$1"
  python3 - "$inventory" <<'PY'
import json,sys
d=json.load(open(sys.argv[1],encoding="utf-8"))
p=d.get("properties",{})
b=d.get("boot",{})
print(f"device={p.get('ro.product.model') or 'unknown'}")
print(f"android={p.get('ro.build.version.release') or 'unknown'}")
print(f"boot_state={b.get('state') or 'unknown'}")
print(f"verified_boot={b.get('verified_boot_state') or 'unknown'}")
print(f"slot={b.get('slot') or 'unknown'}")
print(f"dynamic_partitions={bool(d.get('dynamic_partitions'))}")
print("mutation=v1-disabled")
PY
}

jarvis_request_plan() {
  local inventory="$1" profile="$2" output="$3"
  local module_dir
  module_dir="$(cd "$(dirname "$0")" && pwd)"
  source "$module_dir/plan.sh"
  build_plan "$inventory" "$profile" "$output"
}
