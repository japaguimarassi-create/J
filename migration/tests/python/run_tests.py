import importlib
import traceback
from pathlib import Path

ROOT=Path(__file__).resolve().parent
MODULES=("test_hashes","test_state_machine","test_manifests","policy_scan")

failed=0
total=0

for name in MODULES:
    module=importlib.import_module(name)
    for attr_name in sorted(dir(module)):
        if not attr_name.startswith("test_"):
            continue
        fn=getattr(module,attr_name)
        if not callable(fn):
            continue
        total+=1
        label=f"{name}.{attr_name}"
        try:
            fn()
            print(f"PASS {label}")
        except Exception:
            failed+=1
            print(f"FAIL {label}")
            traceback.print_exc()

print(f"Ran {total} tests; failures={failed}")
raise SystemExit(1 if failed else 0)
