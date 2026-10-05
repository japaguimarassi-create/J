#!/usr/bin/env python3
import hashlib
import sys
from pathlib import Path

root=Path(sys.argv[1]).resolve()
output=Path(sys.argv[2])
excluded={"hashes.sha256","hashes.check.sha256","state-digest"}
rows=[]
for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name not in excluded):
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    rows.append(f"{digest}  {path.relative_to(root).as_posix()}")
output.parent.mkdir(parents=True,exist_ok=True)
data="\n".join(rows)+"\n"
output.write_text(data,encoding="utf-8")
print(hashlib.sha256(data.encode()).hexdigest())
