#!/usr/bin/env bash
set -u
verify_file_hashes() {
  local manifest="$1"
  python3 - "$manifest" <<'PY'
import hashlib,sys
from pathlib import Path
manifest=Path(sys.argv[1]).resolve()
root=manifest.parent
for line in manifest.read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    digest, rel=line.split("  ",1)
    data=(root/rel).read_bytes()
    if hashlib.sha256(data).hexdigest()!=digest:
        raise SystemExit(30)
raise SystemExit(0)
PY
}
