#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  printf 'Uso: sudo %s /caminho/para/linux.iso SHA256_OFICIAL\n' "$0" >&2
  exit 2
fi

ISO_FILE="$(readlink -f "$1")"
EXPECTED_SHA="$(printf '%s' "$2" | tr '[:upper:]' '[:lower:]')"

if [[ ! -f "$ISO_FILE" ]]; then
  printf 'ISO não encontrada: %s\n' "$ISO_FILE" >&2
  exit 1
fi

if [[ ! "$EXPECTED_SHA" =~ ^[0-9a-f]{64}$ ]]; then
  printf 'Informe o SHA-256 oficial completo (64 caracteres hexadecimais).\n' >&2
  exit 1
fi

for command_name in lsblk findmnt blockdev sha256sum dd readlink; do
  command -v "$command_name" >/dev/null 2>&1 || {
    printf 'Dependência ausente: %s\n' "$command_name" >&2
    exit 1
  }
done

if [[ "$EUID" -ne 0 ]]; then
  exec sudo -- "$0" "$ISO_FILE" "$EXPECTED_SHA"
fi

printf 'Calculando SHA-256 da ISO...\n'
ACTUAL_SHA="$(sha256sum "$ISO_FILE" | awk '{print $1}')"
if [[ "$ACTUAL_SHA" != "$EXPECTED_SHA" ]]; then
  printf 'SHA-256 não corresponde ao valor oficial.\nEsperado: %s\nObtido:   %s\n' "$EXPECTED_SHA" "$ACTUAL_SHA" >&2
  exit 1
fi

printf '\nDiscos detectados:\n'
lsblk -dpno NAME,SIZE,MODEL,TRAN,TYPE | awk '$NF == "disk"'
printf '\nAtenção: o dispositivo escolhido será apagado por completo.\n'
read -r -p 'Digite o dispositivo USB inteiro (ex.: /dev/sdb): ' TARGET
TARGET="$(readlink -f "$TARGET")"

if [[ ! -b "$TARGET" ]] || [[ "$(lsblk -dn -o TYPE "$TARGET" | tr -d '[:space:]')" != "disk" ]]; then
  printf 'Dispositivo inválido. Informe o disco inteiro, não uma partição.\n' >&2
  exit 1
fi

ROOT_SOURCE="$(findmnt -n -o SOURCE / || true)"
if [[ -n "$ROOT_SOURCE" ]]; then
  ROOT_CHAIN="$(lsblk -sno PATH "$ROOT_SOURCE" 2>/dev/null || true)"
  if printf '%s\n' "$ROOT_CHAIN" | grep -Fxq "$TARGET"; then
    printf 'Operação bloqueada: o dispositivo contém o sistema em execução.\n' >&2
    exit 1
  fi
fi

ISO_SOURCE="$(findmnt -n -o SOURCE -T "$ISO_FILE" 2>/dev/null || true)"
if [[ -n "$ISO_SOURCE" ]]; then
  ISO_CHAIN="$(lsblk -sno PATH "$ISO_SOURCE" 2>/dev/null || true)"
  if printf '%s\n' "$ISO_CHAIN" | grep -Fxq "$TARGET"; then
    printf 'Operação bloqueada: a ISO está armazenada no próprio dispositivo escolhido.\n' >&2
    exit 1
  fi
fi

while IFS= read -r mountpoint; do
  if [[ -n "$mountpoint" ]]; then
    printf 'Desmonte primeiro todas as partições de %s (montagem encontrada: %s).\n' "$TARGET" "$mountpoint" >&2
    exit 1
  fi
done < <(lsblk -nrpo MOUNTPOINT "$TARGET")

ISO_SIZE="$(stat -c '%s' "$ISO_FILE")"
DEVICE_SIZE="$(blockdev --getsize64 "$TARGET")"
if (( DEVICE_SIZE < ISO_SIZE )); then
  printf 'Dispositivo pequeno demais: ISO=%s bytes, USB=%s bytes.\n' "$ISO_SIZE" "$DEVICE_SIZE" >&2
  exit 1
fi

printf '\nISO: %s\nTamanho: %s bytes\nDestino: %s\n' "$ISO_FILE" "$ISO_SIZE" "$TARGET"
lsblk -dn -o SIZE,MODEL,TRAN "$TARGET"
printf '\nIsto apagará todos os dados do dispositivo acima.\n'
read -r -p "Para confirmar, digite ERASE:$TARGET: " CONFIRMATION
if [[ "$CONFIRMATION" != "ERASE:$TARGET" ]]; then
  printf 'Confirmação incorreta. Nada foi gravado.\n'
  exit 1
fi

dd if="$ISO_FILE" of="$TARGET" bs=4M status=progress conv=fsync
sync
if command -v partprobe >/dev/null 2>&1; then
  partprobe "$TARGET" || true
fi

printf '\nMídia USB criada e sincronizada. Reinicie e selecione o USB no menu de boot.\n'
printf 'A instalação no disco interno deve ser feita pelo instalador gráfico somente após verificar o backup.\n'
