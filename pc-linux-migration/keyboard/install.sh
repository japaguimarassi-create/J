#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROFILE="${1:-$SCRIPT_DIR/profile-example.conf}"
TARGET="/etc/keyd/default.conf"
BACKUP_DIR="/var/backups/aoc-keyboard"
STAMP="$(date +%Y%m%d-%H%M%S)"

if [[ $EUID -eq 0 ]]; then
  SUDO=""
else
  SUDO="sudo"
fi

if [[ ! -f "$PROFILE" ]]; then
  printf 'Perfil não encontrado: %s\n' "$PROFILE" >&2
  exit 1
fi

if ! command -v keyd >/dev/null 2>&1; then
  printf 'keyd não está instalado. Tentando instalar...\n'
  if ! command -v apt-get >/dev/null 2>&1; then
    printf 'Instalação automática disponível apenas para sistemas com apt.\n' >&2
    exit 1
  fi
  $SUDO apt-get update
  if ! $SUDO apt-get install -y keyd; then
    printf '\nO pacote keyd não está disponível nos repositórios configurados.\n'
    printf 'Consulte a documentação oficial: https://github.com/rvaiya/keyd\n'
    exit 1
  fi
fi

if ! command -v systemctl >/dev/null 2>&1; then
  printf 'systemd não encontrado; não é possível configurar o serviço automaticamente.\n' >&2
  exit 1
fi

$SUDO install -d -m 0755 "$BACKUP_DIR"
if $SUDO test -f "$TARGET"; then
  $SUDO cp -a "$TARGET" "$BACKUP_DIR/default.conf.$STAMP.bak"
  printf 'Backup da configuração anterior: %s/default.conf.%s.bak\n' "$BACKUP_DIR" "$STAMP"
fi

TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT
cp "$PROFILE" "$TMP"

if ! keyd check "$TMP"; then
  printf 'Configuração inválida. Nenhuma alteração foi aplicada.\n' >&2
  exit 1
fi

$SUDO install -D -m 0644 "$TMP" "$TARGET"
if ! $SUDO systemctl enable --now keyd; then
  printf 'Não foi possível iniciar keyd. Restaurando a configuração anterior, se existir.\n' >&2
  if $SUDO test -f "$BACKUP_DIR/default.conf.$STAMP.bak"; then
    $SUDO cp -a "$BACKUP_DIR/default.conf.$STAMP.bak" "$TARGET"
  else
    $SUDO rm -f "$TARGET"
  fi
  exit 1
fi

if ! $SUDO keyd reload; then
  printf 'Falha ao recarregar keyd. Use rollback.sh para restaurar o backup.\n' >&2
  exit 1
fi

printf '\nMapeamento aplicado. Teste em um editor de texto.\n'
printf 'Emergência: pressione Backspace + Esc + Enter para encerrar keyd.\n'
printf 'Para desfazer: execute %s/rollback.sh\n' "$SCRIPT_DIR"
