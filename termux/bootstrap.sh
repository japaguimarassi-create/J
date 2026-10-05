#!/usr/bin/env bash
set -u
set -o pipefail

REPO="japaguimarassi-create/J"
BRANCH="lokivolt/migration-engine-v1"
DEST="${HOME}/.local/share/lokivolt"

command -v curl >/dev/null 2>&1 || { printf '%s\n' 'curl is required' >&2; exit 20; }
command -v tar >/dev/null 2>&1 || { printf '%s\n' 'tar is required' >&2; exit 20; }
[[ -n "${PREFIX:-}" && -d "$PREFIX" ]] || { printf '%s\n' 'This bootstrap must run inside Termux' >&2; exit 50; }

tmp="$(mktemp -d)"
archive="$tmp/lokivolt.tar.gz"
url="https://github.com/$REPO/archive/refs/heads/$BRANCH.tar.gz"

cleanup() {
  rm -rf "$tmp"
}
trap cleanup EXIT

curl --fail --location --silent --show-error "$url" --output "$archive" || exit 30
mkdir -p "$DEST" "$PREFIX/bin" || exit 70
tar -xzf "$archive" -C "$tmp" || exit 30

source_dir=""
while IFS= read -r candidate; do
  if [[ -d "$candidate/migration" && -d "$candidate/bin" ]]; then
    source_dir="$candidate"
    break
  fi
done < <(find "$tmp" -mindepth 1 -maxdepth 1 -type d -print)

[[ -n "$source_dir" ]] || { printf '%s\n' 'Cannot locate Lokivolt archive root' >&2; exit 30; }

rm -rf "$DEST/migration" "$DEST/bin"
cp -R "$source_dir/migration" "$DEST/" || exit 70
cp -R "$source_dir/bin" "$DEST/" || exit 70
cp -R "$source_dir/docs" "$DEST/" 2>/dev/null || true
cp -R "$source_dir/os" "$DEST/" 2>/dev/null || true
chmod 755 "$DEST/bin/lokivolt" || exit 70

cat > "$PREFIX/bin/lokivolt" <<EOF
#!/usr/bin/env bash
set -u
set -o pipefail
export LOKIVOLT_ROOT="$DEST"
exec bash "$DEST/bin/lokivolt" "\$@"
EOF
chmod 755 "$PREFIX/bin/lokivolt" || exit 70

printf '%s\n' 'Lokivolt installed.'
printf '%s\n' "Engine: $DEST"
printf '%s\n' 'Command: lokivolt doctor'
