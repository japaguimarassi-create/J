#!/usr/bin/env bash
set -u
set -o pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/lib/exit_codes.sh"
source "$ROOT/lib/log.sh"
MODE="discover"
VAULT=""
usage() {
  printf '%s\n' 'Lokivolt Migration Engine v1' '' 'Usage: master.sh [--mode discover|mutate] [--vault PATH] [--read-only]'
}
while (($#)); do
  case "$1" in
    --mode) (($# >= 2)) || exit "$LV_MISSING_PREREQ"; MODE="$2"; shift 2 ;;
    --vault) (($# >= 2)) || exit "$LV_MISSING_PREREQ"; VAULT="$2"; shift 2 ;;
    --read-only) MODE="discover"; shift ;;
    --help|-h) usage; exit "$LV_OK" ;;
    *) log_error "unknown option: $1"; exit "$LV_MISSING_PREREQ" ;;
  esac
done
case "$MODE" in
  discover) ;;
  mutate) log_warn 'v1 mutation phase is disabled'; exit "$LV_AUTH_REQUIRED" ;;
  *) log_error "unsupported mode: $MODE"; exit "$LV_MISSING_PREREQ" ;;
esac
[[ -n "$VAULT" ]] || VAULT="$PWD/LokivoltVault"
mkdir -p "$VAULT/run" "$VAULT/logs" || exit "$LV_INTERNAL_ERROR"
printf '%s\n' '{' '  "schema_version": 1,' '  "engine_version": "1.0.0",' '  "mode": "discover",' '  "state": "INIT",' '  "next_state": "PREFLIGHT",' '  "read_only": true' '}' > "$VAULT/run/state-machine.json" || exit "$LV_INTERNAL_ERROR"
log_info 'Lokivolt Migration Engine v1 discovery initialized'
exit "$LV_OK"
