#!/usr/bin/env bash
set -u
set -o pipefail

REPO="japaguimarassi-create/J"
BRANCH="lokivolt/migration-engine-v1"
DEST="${HOME}/.local/share/lokivolt"

command -v curl >/dev/null 2>&1 || { printf '%s\n' 'curl is required' >&2; exit 20; }
command -v tar >/dev/null 2>&1 || { printf '%s\n' 'tar is required' >&2; exit 20; }

tmp="$(mktemp -d)"
archive="$tmp/lokivolt.tar.gz"
url="https://github.com/$REPO/archive/refs/heads/$BRANCH.tar.gz"

curl --fail --location --silent --show-error "$url" --output "$archive" || exit 30
mkdir -p "$DEST"
tar -xzf "$archive" -C "$tmp" || exit 30

source_dir="$tmp/J-$BRANCH"
[[ -d "$source_dir" ]] || exit 30

cp -R "$source_dir"/migration "$DEST"/
cp -R "$source_dir"/bin "$DEST"/
cp -R "$source_dir"/docs "$DEST"/
printf '%s\n' 'Lokivolt installed to ~/.local/share/lokivolt'
printf '%s\n' 'Run: bash ~/.local/share/lokivolt/bin/lokivolt discover'
