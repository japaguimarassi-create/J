#!/usr/bin/env bash
set -u
set -o pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
status=0
while IFS= read -r file; do
  bash -n "$file" || status=1
done < <(find "$ROOT" -type f -name '*.sh' -print)
python3 -m py_compile "$ROOT"/lib/*.py "$ROOT"/tests/python/*.py || status=1
python3 "$ROOT/tests/python/run_tests.py" || status=1
bash "$ROOT/tests/shell/test_master.sh" || status=1
bash "$ROOT/tests/shell/test_preflight.sh" || status=1
bash "$ROOT/tests/shell/test_jarvis_bridge.sh" || status=1
bash "$ROOT/tests/shell/test_device_discovery.sh" || status=1
bash "$ROOT/tests/shell/test_transactions.sh" || status=1
bash "$ROOT/tests/shell/test_vault.sh" || status=1
bash "$ROOT/tests/shell/test_platform_inspection.sh" || status=1
bash "$ROOT/tests/shell/test_profiles.sh" || status=1
bash "$ROOT/tests/shell/test_planner.sh" || status=1
bash "$ROOT/tests/shell/test_recovery.sh" || status=1
bash "$ROOT/tests/shell/test_release.sh" || status=1
exit "$status"
