#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cat "$ROOT"/.voxmobs-source/part-*.b64 | base64 -d > "$ROOT/VoxMobs-1.20.1-source.tar.xz"
xz -t "$ROOT/VoxMobs-1.20.1-source.tar.xz"
tar -xJf "$ROOT/VoxMobs-1.20.1-source.tar.xz" -C "$ROOT"
printf '%s\n' "VoxMobs source extracted to $ROOT/VoxMobs-1.20.1"
