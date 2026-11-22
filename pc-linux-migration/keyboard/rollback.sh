#!/usr/bin/env bash
set -Eeuo pipefail

TARGET="/etc/keyd/default.conf"
BACKUP_DIR="/var/backups/aoc-keyboard"

if [[ $EUID -eq 0 ]]; then SUDO=""; else SUDO="sudo"; fi

if ! command -v keyd >/dev/null 2>&1; then
  printf 'keyd não está instalado.\n' >&2
  exit 1
fi

LATEST="$(find "$BACKUP_DIR" -maxdepth 1 -type f -name 'default.conf.*.bak' -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -n1 | cut -d' ' -f2- || true)"

if [[ -n "$LATEST" ]]; then
  $SUDO cp -a "$LATEST" "$TARGET"
  printf 'Configuração anterior restaurada: %s\n' "$LATEST"
else
  $SUDO rm -f "$TARGET"
  printf 'Nenhum backup anterior encontrado; configuração personalizada removida.\n'
fi

$SUDO keyd reload || $SUDO systemctl restart keyd
printf 'Reconfiguração desfeita.\n'
