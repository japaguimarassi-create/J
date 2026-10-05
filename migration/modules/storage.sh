#!/usr/bin/env bash
set -u
collect_storage() {
  local output="$1"
  df -Pk > "$output" 2>/dev/null || : > "$output"
}
