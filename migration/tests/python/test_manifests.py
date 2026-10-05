import json
import subprocess
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
JSON_UTIL=ROOT/"lib"/"json_util.py"

def test_canonical_json_key_order_is_stable():
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)
        src=root/"input.json"
        dst=root/"output.json"
        src.write_text(json.dumps({"z":1,"a":{"d":2,"b":3}}),encoding="utf-8")
        assert subprocess.run(["python3",str(JSON_UTIL),str(src),str(dst)]).returncode==0
        data=dst.read_text(encoding="utf-8")
        assert data.index('"a"') < data.index('"z"')
        again=root/"output2.json"
        subprocess.check_call(["python3",str(JSON_UTIL),str(dst),str(again)])
        assert dst.read_text(encoding="utf-8")==again.read_text(encoding="utf-8")
