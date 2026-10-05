#!/usr/bin/env bash
set -u
set -o pipefail

VAULT_LIB="$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" && pwd)"

vault_init() {
  local root="$1"
  local state_id="$2"
  mkdir -p "$root/states/$state_id" "$root/transactions" "$root/logs" "$root/firmware/manifests" "$root/firmware/hashes" "$root/run"
  printf '%s\n' "$state_id" > "$root/run/current-state"
}

vault_write_state() {
  local root="$1" state_id="$2" input_dir="$3"
  local target="$root/states/$state_id"
  mkdir -p "$target"
  python3 - "$input_dir" "$target" <<'PY'
import shutil,sys
from pathlib import Path
source=Path(sys.argv[1])
target=Path(sys.argv[2])
for item in sorted(source.iterdir()):
    destination=target/item.name
    if item.is_dir():
        shutil.copytree(item,destination,dirs_exist_ok=True)
    elif item.is_file():
        shutil.copy2(item,destination)
PY
  python3 "$VAULT_LIB/hash_tree.py" "$target" "$target/hashes.sha256" > "$target/state-digest"
}

vault_hash_tree() {
  local root="$1" state_id="$2"
  local target="$root/states/$state_id"
  python3 "$VAULT_LIB/hash_tree.py" "$target" "$target/hashes.sha256"
}

vault_verify_state() {
  local root="$1" state_id="$2"
  local target="$root/states/$state_id"
  [[ -f "$target/hashes.sha256" ]] || return 1
  local expected actual
  expected="$(cat "$target/state-digest" 2>/dev/null || true)"
  actual="$(python3 "$VAULT_LIB/hash_tree.py" "$target" "$target/hashes.check.sha256")" || return 1
  [[ "$expected" == "$actual" ]]
}
