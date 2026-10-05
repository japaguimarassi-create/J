#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
source "$ROOT/modules/profile.sh"
TMP="$(mktemp -d)"
printf '%s\n' '{"properties":{"ro.product.manufacturer":"motorola"}}' > "$TMP/inventory.json"
resolve_profile "$TMP/inventory.json" "$TMP/profile.json"
grep -q '"profile": "motorola"' "$TMP/profile.json"
printf '%s\n' '{"properties":{"ro.product.manufacturer":"acme"}}' > "$TMP/inventory2.json"
resolve_profile "$TMP/inventory2.json" "$TMP/profile2.json"
grep -q '"profile": "generic"' "$TMP/profile2.json"
printf 'PASS: profiles\n'
