#!/usr/bin/env bash
set -u
set -o pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$ROOT/modules/transaction.sh"
source "$ROOT/lib/state.sh"
fail(){ printf 'FAIL: %s\n' "$1" >&2; exit 1; }
TMP="$(mktemp -d)"
tx_configure "$TMP"
TX="$(tx_begin "discovery" "INIT")"
[[ "$TX" == TX-* ]] || fail "transaction id"
tx_record_precondition "$TX" "read_only" "true" || fail "precondition"
tx_record_action "$TX" "inventory" || fail "action"
tx_record_result "$TX" "verified" || fail "result"
tx_commit "$TX" || fail "commit"
grep -q ""transaction_id":"$TX"" "$TMP/transactions/journal.jsonl" || fail "journal record"
cat > "$TMP/state.json" <<'JSON'
{"state":"INIT","schema_version":1}
JSON
state_transition_file "$TMP/state.json" "INIT" "PREFLIGHT" || fail "valid transition"
! state_transition_file "$TMP/state.json" "PREFLIGHT" "COMMIT" || fail "invalid transition accepted"
grep -q '"state": "PREFLIGHT"' "$TMP/state.json" || fail "state changed"
printf 'PASS: transactions\n'
