#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MASTER="$ROOT/master/master.sh"

fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$1"; }

[[ -f "$MASTER" ]] || fail "master engine exists"

if bash "$MASTER" --help >/tmp/lokivolt-help.$$ 2>&1; then
  grep -q -- "--mode" /tmp/lokivolt-help.$$ || fail "help exposes mode"
  grep -q -- "--vault" /tmp/lokivolt-help.$$ || fail "help exposes vault"
else
  rm -f /tmp/lokivolt-help.$$
  fail "help exits zero"
fi
rm -f /tmp/lokivolt-help.$$

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

if bash "$MASTER" --mode discover --vault "$TMP/vault"; then
  [[ -f "$TMP/vault/run/state-machine.json" ]] || fail "discover creates run state"
else
  fail "discover exits zero in fixture mode"
fi

if bash "$MASTER" --mode mutate --vault "$TMP/vault" >/dev/null 2>&1; then
  fail "mutate is refused in v1"
else
  code=$?
  [[ "$code" -eq 40 ]] || fail "mutate returns authorization-required code"
fi

pass "master bootstrap"
