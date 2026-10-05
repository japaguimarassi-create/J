#!/usr/bin/env python3
import hashlib
import sys
from pathlib import Path

root=Path(sys.argv[1]).resolve()
output=Path(sys.argv[2])
rows=[]
for path in sorted(p for p in root.rglob("*") if p.is_file() and p != output):
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    rows.append(f"{digest}  {path.relative_to(root).as_posix()}")
output.parent.mkdir(parents=True,exist_ok=True)
output.write_text("\n".join(rows)+"\n",encoding="utf-8")
print(hashlib.sha256(output.read_bytes()).hexdigest())
