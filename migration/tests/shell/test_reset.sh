#!/usr/bin/env bash
set -u
set -o pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
source "$ROOT/modules/reset.sh"

TMP="$(mktemp -d)"
build_reset_plan "security@example.com" "restore@example.com" "$TMP/reset.json" || exit 1
python3 - "$TMP/reset.json" <<'PY'
import json,sys
x=json.load(open(sys.argv[1]))
assert x["email_1"]["role"]=="security"
assert x["email_2"]["role"]=="restore"
assert x["authorization_required"] is True
assert x["passwords"]=="provider_password_manager"
PY

if build_reset_plan "same@example.com" "same@example.com" "$TMP/bad.json"; then
  exit 1
fi

printf '%s\n' 'PASS: reset plan'
