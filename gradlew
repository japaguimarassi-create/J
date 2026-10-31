#!/usr/bin/env sh
set -eu
GRADLE_VERSION=8.8
GRADLE_HOME_DIR="${GRADLE_USER_HOME:-$HOME/.gradle}/voxmobs-bootstrap/gradle-${GRADLE_VERSION}"
GRADLE_BIN="$GRADLE_HOME_DIR/bin/gradle"
if [ ! -x "$GRADLE_BIN" ]; then
  command -v curl >/dev/null 2>&1 || { echo 'curl is required to bootstrap Gradle 8.8.' >&2; exit 1; }
  command -v unzip >/dev/null 2>&1 || { echo 'unzip is required to bootstrap Gradle 8.8.' >&2; exit 1; }
  mkdir -p "$(dirname "$GRADLE_HOME_DIR")"
  TMP_ZIP="${TMPDIR:-/tmp}/voxmobs-gradle-${GRADLE_VERSION}.zip"
  curl -fL --retry 3 --retry-delay 2 "https://services.gradle.org/distributions/gradle-${GRADLE_VERSION}-bin.zip" -o "$TMP_ZIP"
  TMP_DIR="${TMPDIR:-/tmp}/voxmobs-gradle-${GRADLE_VERSION}"
  rm -rf "$TMP_DIR"
  mkdir -p "$TMP_DIR"
  unzip -q "$TMP_ZIP" -d "$TMP_DIR"
  mv "$TMP_DIR/gradle-${GRADLE_VERSION}" "$GRADLE_HOME_DIR"
  rm -rf "$TMP_DIR" "$TMP_ZIP"
fi
exec "$GRADLE_BIN" "$@"
