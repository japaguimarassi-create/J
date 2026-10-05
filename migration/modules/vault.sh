#!/usr/bin/env bash
set -u
set -o pipefail

VAULT_LIB="$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" && pwd)"

vault_init() {
  local root="$1"
  local state_id="$2"
  local target="$root/states/$state_id"
  mkdir -p "$root/states" "$root/transactions" "$root/logs" "$root/firmware/manifests" "$root/firmware/hashes" "$root/run"
  if [[ -e "$target/state-digest" ]]; then
    return 1
  fi
  mkdir -p "$target"
  printf '%s\n' "$state_id" > "$root/run/current-state"
}

vault_write_state() {
  local root="$1" state_id="$2" input_dir="$3"
  local target="$root/states/$state_id"
  mkdir -p "$target"
  [[ ! -e "$target/state-digest" ]] || return 1
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

vault_next_state_id() {
  local root="$1"
  python3 - "$root" <<'PY'
import re,sys
from pathlib import Path
root=Path(sys.argv[1])/"states"
highest=-1
if root.exists():
    for item in root.iterdir():
        m=re.fullmatch(r"STATE-(d{3,})",item.name)
        if m:
            highest=max(highest,int(m.group(1)))
print(f"STATE-{highest+1:03d}")
PY
}

