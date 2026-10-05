#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
CLI="$ROOT/bin/lokivolt"

[[ -x "$CLI" ]] || { printf '%s\n' 'CLI mode is not executable; use bash wrapper' >&2; }
out="$(bash "$CLI" version)"
grep -q 'Lokivolt Migration Engine v1.0.0' <<<"$out" || { printf '%s\n' 'FAIL: version' >&2; exit 1; }
bash "$CLI" --help >/dev/null || { printf '%s\n' 'FAIL: help' >&2; exit 1; }
printf 'PASS: CLI\n'
