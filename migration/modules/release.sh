#!/usr/bin/env bash
set -u
validate_release_manifest() {
  local manifest="$1" inventory="$2"
  python3 - "$manifest" "$inventory" <<'PY'
import hashlib,json,sys
m=json.load(open(sys.argv[1],encoding="utf-8"))
i=json.load(open(sys.argv[2],encoding="utf-8"))
required=("schema_version","release","device_family","android_base","images")
if any(k not in m for k in required): raise SystemExit(30)
if not isinstance(m["images"],list) or not m["images"]: raise SystemExit(30)
model=str(i.get("properties",{}).get("ro.product.model") or "")
family=str(m.get("device_family") or "")
if family and model and family.lower() not in model.lower() and family.lower() not in "generic":
    raise SystemExit(30)
for image in m["images"]:
    if not image.get("name") or len(str(image.get("sha256",""))) != 64:
        raise SystemExit(30)
if m.get("required_bootloader_state")=="UNLOCKED" and i.get("boot",{}).get("state")!="unlocked":
    raise SystemExit(40)
raise SystemExit(0)
PY
}
