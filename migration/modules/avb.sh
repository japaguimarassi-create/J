#!/usr/bin/env bash
set -u
inspect_verified_boot() {
  local output="$1"
  local state digest
  state=""
  digest=""
  if [[ -n "${LOKIVOLT_GETPROP_FILE:-}" && -f "$LOKIVOLT_GETPROP_FILE" ]]; then
    state="$(awk -F'[][]' '/ro.boot.verifiedbootstate/ {print $4; exit}' "$LOKIVOLT_GETPROP_FILE")"
    digest="$(awk -F'[][]' '/ro.boot.vbmeta.digest/ {print $4; exit}' "$LOKIVOLT_GETPROP_FILE")"
  else
    state="$(getprop ro.boot.verifiedbootstate 2>/dev/null || true)"
    digest="$(getprop ro.boot.vbmeta.digest 2>/dev/null || true)"
  fi
  python3 - "$output" "$state" "$digest" <<'PY'
import json,sys
out,state,digest=sys.argv[1:]
json.dump({"schema_version":1,"verified_boot_state":state or None,"vbmeta_digest":digest or None,"available":bool(state or digest)},open(out,"w",encoding="utf-8"),sort_keys=True,indent=2)
PY
}
