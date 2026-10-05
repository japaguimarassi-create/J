from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]
PATTERNS=[
    r"fastboot\s+(flash|erase|format|boot)",
    r"\bdd\b[^\n]*(/dev/block|/dev/)",
    r"sgdisk\b",
    r"parted\b",
    r"wipefs\b",
]
def test_no_v1_device_write_primitives():
    offenders=[]
    for path in ROOT.rglob("*.sh"):
        text=path.read_text(encoding="utf-8",errors="replace")
        for pattern in PATTERNS:
            if re.search(pattern,text,re.I):
                offenders.append(str(path))
    assert not offenders, offenders
