#!/usr/bin/env bash
set -u
set -o pipefail

lv_prop_source() {
  if [[ -n "${LOKIVOLT_GETPROP_FILE:-}" && -f "$LOKIVOLT_GETPROP_FILE" ]]; then
    cat "$LOKIVOLT_GETPROP_FILE"
    return 0
  fi
  if command -v getprop >/dev/null 2>&1; then
    getprop
    return 0
  fi
  return 1
}

collect_device_properties() {
  local out="$1"
  mkdir -p "$out"
  local raw="$out/getprop.raw"
  lv_prop_source > "$raw" 2>/dev/null || : > "$raw"
  printf '%s\n' "$raw"
}

collect_runtime_architecture() {
  local out="$1"
  local arch abi
  arch="$(getprop ro.product.cpu.abi 2>/dev/null || true)"
  abi="$(uname -m 2>/dev/null || true)"
  cat > "$out/runtime.txt" <<EOF
arch=$abi
ro.product.cpu.abi=$arch
EOF
}

device_prop() {
  local key="$1" file="$2"
  awk -v wanted="$key" '
    $0 ~ "^\\[" wanted "\\]: \\[" {
      line=$0
      sub("^\\[" wanted "\\]: \\[", "", line)
      sub("\\]$", "", line)
      print line
      exit
    }
  ' "$file"
}

collect_inventory() {
  local raw_dir="$1" output="$2"
  local raw="$raw_dir/getprop.raw"
  [[ -f "$raw" ]] || return 1
  python3 - "$raw" "$output" <<'PY'
import json,re,sys
from datetime import datetime,timezone
raw,out=sys.argv[1:]
props={}
for line in open(raw,encoding="utf-8",errors="replace"):
    m=re.match(r"^\[([^]]+)\]: \[([^]]*)\]$",line.rstrip("\n"))
    if m:
        props[m.group(1)]=m.group(2)
def one(*keys):
    for k in keys:
        if k in props and props[k]!="":
            return props[k]
    return None
locked=one("ro.boot.flash.locked")
if locked=="1": boot_state="locked"
elif locked=="0": boot_state="unlocked"
else: boot_state=None
slot=one("ro.boot.slot_suffix")
vb=one("ro.boot.verifiedbootstate")
dynamic=any(props.get(k)=="true" for k in ("ro.boot.dynamic_partitions","ro.boot.dynamic_partitions_retrofit")) or bool(one("ro.boot.super_partition"))
ab=bool(slot)
data={
 "schema_version":1,
 "state_id":"STATE-000",
 "collected_at":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),
 "properties":{
   "ro.product.model":one("ro.product.model"),
   "ro.product.manufacturer":one("ro.product.manufacturer"),
   "ro.build.version.release":one("ro.build.version.release"),
   "ro.build.version.security_patch":one("ro.build.version.security_patch"),
   "ro.product.cpu.abi":one("ro.product.cpu.abi")
 },
 "boot":{"state":boot_state,"verified_boot_state":vb,"slot":slot},
 "dynamic_partitions":dynamic,
 "ab_slots":ab,
 "evidence":{"source":"getprop","raw_file":"getprop.raw"}
}
json.dump(data,open(out,"w",encoding="utf-8"),sort_keys=True,indent=2)
PY
}
