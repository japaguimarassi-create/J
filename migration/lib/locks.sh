#!/usr/bin/env bash
acquire_lock() {
  local path="$1"
  local parent="$(dirname "$path")"
  mkdir -p "$parent" || return 1
  mkdir "$path" 2>/dev/null || return 1
  printf '%s\n' "$$" > "$path/pid" || return 1
  return 0
}
release_lock() {
  local path="$1"
  [[ -f "$path/pid" ]] || return 0
  rm "$path/pid" 2>/dev/null || true
  rmdir "$path" 2>/dev/null || true
}
