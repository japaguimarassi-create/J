#!/usr/bin/env bash
set -euo pipefail
rm -f "$HOME/.local/share/applications/aoc-migration-center.desktop"
rm -f "$HOME/.config/autostart/aoc-migration-center.desktop"
echo "Atalho e inicialização automática removidos."
echo "A pasta do aplicativo e todos os cofres foram preservados em ~/.local/share/aoc-migration-center."
echo "Remova manualmente a pasta do aplicativo somente depois de conferir que nenhum backup foi salvo nela."
