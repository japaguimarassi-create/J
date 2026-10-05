import hashlib
import subprocess
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
HASH=ROOT/"lib"/"hash_tree.py"

def test_hash_tree_excludes_metadata():
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)
        (root/"state.json").write_text('{"a":1}\n',encoding="utf-8")
        out=root/"hashes.sha256"
        first=subprocess.check_output(["python3",str(HASH),str(root),str(out)],text=True).strip()
        second=subprocess.check_output(["python3",str(HASH),str(root),str(out)],text=True).strip()
        assert first==second
        assert len(first)==64
        expected=hashlib.sha256((root/"state.json").read_bytes()).hexdigest()
        assert expected in out.read_text(encoding="utf-8")
