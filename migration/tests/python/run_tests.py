import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
suite=unittest.TestSuite()
loader=unittest.TestLoader()
for name in ("test_hashes","test_state_machine","test_manifests","policy_scan"):
    module=__import__(name)
    suite.addTests(loader.loadTestsFromModule(module))
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
