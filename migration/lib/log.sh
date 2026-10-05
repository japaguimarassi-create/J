#!/usr/bin/env bash
lv_timestamp() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }
log_info() { printf '%s INFO %s\n' "$(lv_timestamp)" "$*" >&2; }
log_warn() { printf '%s WARN %s\n' "$(lv_timestamp)" "$*" >&2; }
log_error() { printf '%s ERROR %s\n' "$(lv_timestamp)" "$*" >&2; }
