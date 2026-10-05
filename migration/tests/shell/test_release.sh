#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
source "$ROOT/modules/release.sh"
TMP="$(mktemp -d)"
printf '%s\n' '{"properties":{"ro.product.model":"moto g04s"},"boot":{"state":"unlocked"}}' > "$TMP/inventory.json"
printf '%s\n' '{"schema_version":1,"release":"lokivolt-0.1.0","device_family":"moto","android_base":"14","required_bootloader_state":"UNLOCKED","images":[{"name":"boot","sha256":"0123456789012345678901234567890123456789012345678901234567890123"}]}' > "$TMP/release.json"
validate_release_manifest "$TMP/release.json" "$TMP/inventory.json"
printf 'PASS: release manifest\n'
