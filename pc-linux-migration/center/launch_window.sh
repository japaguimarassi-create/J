#!/usr/bin/env bash
set -euo pipefail
APP_DIR="$HOME/.local/share/aoc-migration-center"
PYTHON="$APP_DIR/.venv/bin/python"
URL="http://127.0.0.1:8765"
RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp}"
PID_FILE="$RUNTIME_DIR/aoc-migration-center-$UID.pid"
LOG_FILE="$HOME/.local/state/aoc-migration-center/agent.log"
mkdir -p "$(dirname "$LOG_FILE")"
if [[ ! -x "$PYTHON" ]]; then
    echo "AOC Migration Center não está instalado. Execute install_aoc_mint.sh primeiro." >&2
    exit 1
fi
if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    :
else
    nohup "$PYTHON" "$APP_DIR/agent.py" >>"$LOG_FILE" 2>&1 </dev/null &
    echo "$!" > "$PID_FILE"
fi
ready=0
for _ in $(seq 1 40); do
    if "$PYTHON" -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8765/api/status", timeout=1).read()' >/dev/null 2>&1; then
        ready=1
        break
    fi
    sleep 0.25
done
if [[ "$ready" -ne 1 ]]; then
    echo "O agente local não iniciou. Consulte: $LOG_FILE" >&2
    exit 1
fi
if command -v chromium >/dev/null 2>&1; then
    exec chromium --app="$URL" --user-data-dir="$APP_DIR/.browser-profile" --no-first-run
elif command -v chromium-browser >/dev/null 2>&1; then
    exec chromium-browser --app="$URL" --user-data-dir="$APP_DIR/.browser-profile" --no-first-run
elif command -v google-chrome >/dev/null 2>&1; then
    exec google-chrome --app="$URL" --user-data-dir="$APP_DIR/.browser-profile" --no-first-run
elif command -v firefox >/dev/null 2>&1; then
    exec firefox --new-window "$URL"
else
    exec xdg-open "$URL"
fi
