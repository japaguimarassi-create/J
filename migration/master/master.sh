#!/usr/bin/env bash
set -u
set -o pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT/lib/exit_codes.sh"
source "$ROOT/lib/log.sh"
source "$ROOT/lib/state.sh"
source "$ROOT/modules/device.sh"
source "$ROOT/modules/preflight.sh"
source "$ROOT/modules/partitions.sh"
source "$ROOT/modules/avb.sh"
source "$ROOT/modules/vault.sh"
source "$ROOT/modules/transaction.sh"
source "$ROOT/modules/profile.sh"
source "$ROOT/modules/plan.sh"
source "$ROOT/modules/recovery.sh"
source "$ROOT/modules/storage.sh"
source "$ROOT/modules/health.sh"

MODE="discover"
VAULT=""
KILL_SWITCH=""

usage() {
  cat <<'USAGE'
Lokivolt Migration Engine v1

Usage:
  master.sh [--mode discover|mutate] [--vault PATH] [--kill-switch PATH]

Modes:
  discover     read-only inventory, Vault, capabilities and dry-run plan
  mutate       refused in v1

Options:
  --vault PATH       Vault root
  --kill-switch PATH force safe abort when file contains enabled=true
  --help             show help
USAGE
}

while (($#)); do
  case "$1" in
    --mode) (($# >= 2)) || exit "$LV_MISSING_PREREQ"; MODE="$2"; shift 2 ;;
    --vault) (($# >= 2)) || exit "$LV_MISSING_PREREQ"; VAULT="$2"; shift 2 ;;
    --kill-switch) (($# >= 2)) || exit "$LV_MISSING_PREREQ"; KILL_SWITCH="$2"; shift 2 ;;
    --help|-h) usage; exit "$LV_OK" ;;
    *) log_error "unknown option: $1"; exit "$LV_MISSING_PREREQ" ;;
  esac
done

[[ "$MODE" == "discover" ]] || { log_warn "v1 mutation is disabled"; exit "$LV_AUTH_REQUIRED"; }
[[ -n "$VAULT" ]] || VAULT="$PWD/LokivoltVault"
[[ -n "$KILL_SWITCH" ]] || KILL_SWITCH="$VAULT/run/KILL_SWITCH"

if [[ -f "$KILL_SWITCH" ]] && grep -Eq '^enabled=true$' "$KILL_SWITCH"; then
  log_error "kill switch active"
  exit "$LV_SAFE_ABORT"
fi

mkdir -p "$VAULT/run" "$VAULT/logs" "$VAULT/staging" || exit "$LV_INTERNAL_ERROR"
STATE_FILE="$VAULT/run/state-machine.json"
cat > "$STATE_FILE" <<'JSON'
{"schema_version":1,"engine_version":"1.0.0","mode":"discover","state":"INIT","read_only":true}
JSON

run_preflight "$VAULT/staging/preflight.json" || exit "$LV_MISSING_PREREQ"
state_transition_file "$STATE_FILE" INIT PREFLIGHT || exit "$LV_INTERNAL_ERROR"

collect_device_properties "$VAULT/staging/device" >/dev/null || exit "$LV_MISSING_PREREQ"
collect_runtime_architecture "$VAULT/staging/device" || exit "$LV_MISSING_PREREQ"
collect_inventory "$VAULT/staging/device" "$VAULT/staging/inventory.json" || exit "$LV_VERIFY_FAILED"
collect_storage "$VAULT/staging/storage.txt"
inspect_slots "$VAULT/staging/slots.json"
inspect_verified_boot "$VAULT/staging/avb.json"
inspect_block_devices "$VAULT/staging/blocks.txt"
inspect_dynamic_partitions "$VAULT/staging/dynamic.json"
state_transition_file "$STATE_FILE" PREFLIGHT INVENTORY || exit "$LV_INTERNAL_ERROR"

python3 - "$VAULT/staging/inventory.json" "$VAULT/staging/preflight.json" "$VAULT/staging/slots.json" "$VAULT/staging/avb.json" "$VAULT/staging/dynamic.json" <<'PY'
import json,sys
inv=json.load(open(sys.argv[1],encoding="utf-8"))
inv["preflight"]=json.load(open(sys.argv[2],encoding="utf-8"))
slot=json.load(open(sys.argv[3],encoding="utf-8"))
avb=json.load(open(sys.argv[4],encoding="utf-8"))
dyn=json.load(open(sys.argv[5],encoding="utf-8"))
inv["boot"]["slot"]=slot.get("active_slot") or inv["boot"].get("slot")
inv["boot"]["verified_boot_state"]=avb.get("verified_boot_state") or inv["boot"].get("verified_boot_state")
inv["ab_slots"]=bool(slot.get("ab_slots") or inv.get("ab_slots"))
inv["dynamic_partitions"]=bool(dyn.get("dynamic_partitions") or inv.get("dynamic_partitions"))
json.dump(inv,open(sys.argv[1],"w",encoding="utf-8"),sort_keys=True,indent=2)
PY

state_transition_file "$STATE_FILE" INVENTORY VAULT_CREATE || exit "$LV_INTERNAL_ERROR"
vault_init "$VAULT" "STATE-000"
cp "$VAULT/staging/inventory.json" "$VAULT/staging/state.json"
vault_write_state "$VAULT" "STATE-000" "$VAULT/staging"
vault_verify_state "$VAULT" "STATE-000" || exit "$LV_VERIFY_FAILED"

state_transition_file "$STATE_FILE" VAULT_CREATE CAPABILITY_ANALYSIS || exit "$LV_INTERNAL_ERROR"
detect_capabilities "$VAULT/staging/inventory.json" "$VAULT/staging/capabilities.json" || exit "$LV_VERIFY_FAILED"
python3 - "$VAULT/staging/inventory.json" "$VAULT/staging/capabilities.json" <<'PY'
import json,sys
a=json.load(open(sys.argv[1],encoding="utf-8"))
b=json.load(open(sys.argv[2],encoding="utf-8"))
a["capabilities"]=b["capabilities"]
json.dump(a,open(sys.argv[1],"w",encoding="utf-8"),sort_keys=True,indent=2)
PY

state_transition_file "$STATE_FILE" CAPABILITY_ANALYSIS PLAN || exit "$LV_INTERNAL_ERROR"
resolve_profile "$VAULT/staging/inventory.json" "$VAULT/staging/profile.json" || exit "$LV_VERIFY_FAILED"
build_plan "$VAULT/staging/inventory.json" "$VAULT/staging/profile.json" "$VAULT/staging/plan.json" || exit "$LV_VERIFY_FAILED"
build_recovery_plan "$VAULT/staging/inventory.json" "$VAULT/staging/plan.json" "$VAULT/staging/recovery.json" || exit "$LV_VERIFY_FAILED"
validate_recovery_plan "$VAULT/staging/recovery.json" || exit "$LV_VERIFY_FAILED"
state_transition_file "$STATE_FILE" PLAN WAITING_FOR_AUTHORIZATION || exit "$LV_INTERNAL_ERROR"
health_check_discovery "$VAULT/staging/health.json" || exit "$LV_VERIFY_FAILED"
printf '%s\n' 'Discovery complete. No device partitions were modified.'
exit "$LV_OK"
