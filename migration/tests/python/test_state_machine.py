import json
import subprocess
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
STATE=ROOT/"lib"/"state.sh"

def test_valid_and_invalid_transitions():
    with tempfile.TemporaryDirectory() as tmp:
        p=Path(tmp)/"state.json"
        p.write_text(json.dumps({"state":"INIT","schema_version":1}),encoding="utf-8")
        cmd=f'source "{STATE}"; state_transition_file "{p}" INIT PREFLIGHT'
        assert subprocess.run(["bash","-lc",cmd]).returncode==0
        cmd=f'source "{STATE}"; state_transition_file "{p}" PREFLIGHT COMMIT'
        assert subprocess.run(["bash","-lc",cmd]).returncode!=0
        assert json.loads(p.read_text(encoding="utf-8"))["state"]=="PREFLIGHT"
