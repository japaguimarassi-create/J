#!/usr/bin/env bash
set -Eeuo pipefail

if ! command -v keyd >/dev/null 2>&1; then
  printf 'Instale keyd primeiro: https://github.com/rvaiya/keyd\n' >&2
  exit 1
fi

printf 'Identificação de teclas iniciada. Pressione as teclas e observe os nomes.\n'
printf 'Ctrl+C encerra.\n'
printf 'Para ver eventos físicos sem remapeamento, pare keyd em outro terminal antes de executar este comando.\n\n'
sudo keyd monitor
