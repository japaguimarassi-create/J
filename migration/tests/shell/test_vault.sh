#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
source "$ROOT/modules/vault.sh"
TMP="$(mktemp -d)"
mkdir -p "$TMP/input"
printf '%s\n' '{"model":"test","schema_version":1}' > "$TMP/input/state.json"
vault_init "$TMP/vault" STATE-000
vault_write_state "$TMP/vault" STATE-000 "$TMP/input"
vault_verify_state "$TMP/vault" STATE-000 || { printf 'FAIL: fresh state\n' >&2; exit 1; }
printf '%s\n' '{"model":"corrupt","schema_version":1}' > "$TMP/vault/states/STATE-000/state.json"
if vault_verify_state "$TMP/vault" STATE-000; then
  printf 'FAIL: corruption accepted\n' >&2
  exit 1
fi
printf 'PASS: vault\n'
