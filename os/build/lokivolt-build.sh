#!/usr/bin/env bash
set -u
set -o pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AOSP_DIR="\${LOKIVOLT_AOSP_DIR:-\$HOME/lokivolt/aosp}"
TARGET="\${1:-cf}"

die() {
  printf '%s\n' "\$1" >&2
  exit 50
}

command -v repo >/dev/null 2>&1 || die "repo is required on the build host"
command -v git >/dev/null 2>&1 || die "git is required on the build host"

mkdir -p "\$AOSP_DIR"

if [[ ! -f "\$AOSP_DIR/.repo/manifest.xml" ]]; then
  cd "\$AOSP_DIR"
  repo init -u https://android.googlesource.com/platform/manifest -b android-latest-release
fi

cd "\$AOSP_DIR"
repo sync -c -j4

install -d "\$AOSP_DIR/vendor/lokivolt/config"
cp "\$ROOT/config/identity-policy.json" "\$AOSP_DIR/vendor/lokivolt/config/"
cp "\$ROOT/config/reset-flow.json" "\$AOSP_DIR/vendor/lokivolt/config/"

case "\$TARGET" in
  cf)
    source build/envsetup.sh
    lunch aosp_cf_arm64_phone-userdebug
    m
    printf '%s\n' "Cuttlefish build complete"
    ;;
  generic-arm64)
    source build/envsetup.sh
    lunch aosp_arm64-userdebug
    m
    printf '%s\n' "Generic arm64 build complete"
    ;;
  moto-g04s)
    die "Moto g04s target is intentionally blocked until validated device, kernel, vendor, AVB and partition sources are present"
    ;;
  *)
    die "Unknown target: \$TARGET"
    ;;
esac
