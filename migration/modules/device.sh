#!/usr/bin/env bash
set -u
set -o pipefail

lv_prop_source() {
  if [[ -n "${LOKIVOLT_GETPROP_FILE:-}" && -f "$LOKIVOLT_GETPROP_FILE" ]]; then
    cat "$LOKIVOLT_GETPROP_FILE"
    return 0
  fi
  if command -v getprop >/dev/null 2>&1; then
    getprop
    return 0
  fi
  return 1
}

collect_device_properties() {
  local out="$1"
  mkdir -p "$out"
  local raw="$out/getprop.raw"
  lv_prop_source > "$raw" 2>/dev/null || : > "$raw"
  printf '%s\n' "$raw"
}

collect_runtime_architecture() {
  local out="$1"
  local arch abi
  arch="$(getprop ro.product.cpu.abi 2>/dev/null || true)"
  abi="$(uname -m 2>/dev/null || true)"
  cat > "$out/runtime.txt" <<EOF
arch=$abi
ro.product.cpu.abi=$arch
EOF
}

device_prop() {
  local key="$1" file="$2"
  awk -v wanted="$key" '
    $0 ~ "^\\[" wanted "\\]: \\[" {
      line=$0
      sub("^\\[" wanted "\\]: \\[", "", line)
      sub("\\]$", "", line)
      print line
      exit
    }
  ' "$file"
}
