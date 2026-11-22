#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
CENTER_SRC="$PROJECT_DIR/center"
APP_DIR="$HOME/.local/share/aoc-migration-center"
DESKTOP_DIR="$HOME/.local/share/applications"
AUTOSTART_DIR="$HOME/.config/autostart"
AUTOSTART=0
if [[ "${1:-}" == "--autostart" ]]; then AUTOSTART=1; fi
if [[ ! -f /etc/linuxmint/info ]]; then
    echo "Este instalador foi projetado para Linux Mint. A instalação foi cancelada." >&2
    exit 1
fi
if [[ ! -f "$CENTER_SRC/agent.py" || ! -f "$CENTER_SRC/web/index.html" ]]; then
    echo "Pasta center/ incompleta. Extraia o repositório inteiro antes de instalar." >&2
    exit 1
fi
command -v python3 >/dev/null 2>&1 || { echo "Python 3 não encontrado." >&2; exit 1; }
mkdir -p "$APP_DIR" "$DESKTOP_DIR"
cp -a "$CENTER_SRC/." "$APP_DIR/"
cp "$SCRIPT_DIR/launch_window.sh" "$APP_DIR/launch_window.sh"
chmod 700 "$APP_DIR/launch_window.sh"
if ! python3 -m venv "$APP_DIR/.venv" 2>/dev/null; then
    echo "Instalando suporte a ambientes virtuais do Python…"
    sudo apt-get install -y python3-venv
    python3 -m venv "$APP_DIR/.venv"
fi
"$APP_DIR/.venv/bin/python" -m pip install --disable-pip-version-check -r "$APP_DIR/requirements.txt"
DESKTOP_FILE="$DESKTOP_DIR/aoc-migration-center.desktop"
cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=AOC Migration Center
Comment=Backup e restauração criptografados
Exec="$APP_DIR/launch_window.sh"
Icon=drive-harddisk
Terminal=false
Categories=System;Utility;
StartupNotify=true
EOF
chmod 644 "$DESKTOP_FILE"
if [[ "$AUTOSTART" -eq 1 ]]; then
    mkdir -p "$AUTOSTART_DIR"
    cp "$DESKTOP_FILE" "$AUTOSTART_DIR/aoc-migration-center.desktop"
fi
echo "AOC Mint Edition instalado."
echo "Abra Menu > Administração > AOC Migration Center."
if [[ "$AUTOSTART" -eq 1 ]]; then echo "Inicialização automática ativada."; fi
