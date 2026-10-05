#!/usr/bin/env bash
set -u
set -o pipefail

build_reset_plan() {
  local email1="$1" email2="$2" output="$3"
  python3 - "$email1" "$email2" "$output" <<'PY'
import json,re,sys
e1,e2,out=sys.argv[1:]
pattern=re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
if not pattern.fullmatch(e1) or not pattern.fullmatch(e2):
    raise SystemExit(20)
if e1.lower()==e2.lower():
    raise SystemExit(20)
data={
  "schema_version":1,
  "email_1":{"role":"security","address":e1.lower()},
  "email_2":{"role":"restore","address":e2.lower()},
  "destructive":True,
  "factory_reset":"platform_factory_reset",
  "passwords":"provider_password_manager",
  "authorization_required":True,
  "execution":"blocked_until_platform_and_device_authorization"
}
json.dump(data,open(out,"w",encoding="utf-8"),sort_keys=True,indent=2)
PY
}
