#!/usr/bin/env bash
set -u
set -o pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
MASTER="$ROOT/master/master.sh"
fail(){ printf 'FAIL: %s\n' "$1" >&2; exit 1; }
[[ -f "$MASTER" ]] || fail "master engine exists"
bash "$MASTER" --help >/tmp/lokivolt-help.$$ 2>&1 || fail "help exits zero"
grep -q -- "--mode" /tmp/lokivolt-help.$$ || fail "help exposes mode"
grep -q -- "--vault" /tmp/lokivolt-help.$$ || fail "help exposes vault"
TMP="$(mktemp -d)"
mkdir -p "$TMP/device"
cat > "$TMP/device/props" <<'PROPS'
[ro.product.model]: [moto g04s]
[ro.product.manufacturer]: [motorola]
[ro.build.version.release]: [14]
[ro.build.version.security_patch]: [2026-09-01]
[ro.product.cpu.abi]: [arm64-v8a]
[ro.boot.flash.locked]: [1]
[ro.boot.verifiedbootstate]: [green]
[ro.boot.slot_suffix]: [_a]
PROPS
export LOKIVOLT_GETPROP_FILE="$TMP/device/props"
export LOKIVOLT_BLOCK_SOURCE="$TMP/device/props"
bash "$MASTER" --mode discover --vault "$TMP/vault" || fail "discover"
grep -q '"state": "WAITING_FOR_AUTHORIZATION"' "$TMP/vault/run/state-machine.json" || fail "final discovery state"
[[ -f "$TMP/vault/states/STATE-000/state-digest" ]] || fail "baseline Vault"
[[ -f "$TMP/vault/states/STATE-001/state-digest" ]] || fail "enriched Vault"
grep -q '"acceptance_status": "ACCEPTED_100"' "$TMP/vault/staging/plan.json" || fail "100% planning acceptance"
grep -q '"execution": "gated"' "$TMP/vault/staging/plan.json" || fail "execution gate"
grep -q '"status": "ACCEPTED_GATED"' "$TMP/vault/staging/inventory.json" || fail "capability decision"
BASE_DIGEST="$(cat "$TMP/vault/states/STATE-000/state-digest")"
bash "$MASTER" --mode discover --vault "$TMP/vault" || fail "second discovery"
[[ "$(cat "$TMP/vault/states/STATE-000/state-digest")" == "$BASE_DIGEST" ]] || fail "baseline Vault changed"
[[ -f "$TMP/vault/states/STATE-002/state-digest" ]] || fail "second-run baseline"
[[ -f "$TMP/vault/states/STATE-003/state-digest" ]] || fail "second-run enriched state"
[[ -f "$TMP/vault/staging/plan.json" ]] || fail "plan"
[[ -f "$TMP/vault/staging/recovery.json" ]] || fail "recovery"
grep -q 'discovery-complete' "$TMP/vault/transactions/journal.jsonl" || fail "transaction result"
grep -q '"commit"' "$TMP/vault/transactions/journal.jsonl" || fail "transaction commit"
printf '%s\n' 'enabled=true' > "$TMP/kill"
if bash "$MASTER" --mode discover --vault "$TMP/second" --kill-switch "$TMP/kill" >/dev/null 2>&1; then fail "kill switch ignored"; fi
if bash "$MASTER" --mode mutate --vault "$TMP/mutate" >/dev/null 2>&1; then
  fail "mutation accepted"
else
  code=$?
  [[ "$code" -eq 40 ]] || fail "mutation wrong exit code"
fi
printf 'PASS: master integration\n'
