#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)' || { echo 'Python 3.10+ é necessário.' >&2; exit 1; }
if [[ ! -x ".venv/bin/python" ]]; then
    python3 -m venv .venv 2>/dev/null || { sudo apt-get install -y python3-venv; python3 -m venv .venv; }
fi
".venv/bin/python" -m pip install --disable-pip-version-check -r requirements.txt
exec ".venv/bin/python" agent.py
