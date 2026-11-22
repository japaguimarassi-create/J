#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)' || { echo 'Python 3.10+ é necessário.' >&2; exit 1; }
python3 -m pip install --user -r requirements.txt
exec python3 agent.py
