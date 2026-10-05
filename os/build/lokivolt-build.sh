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

mkdir -p "\$AOSP_DIR/vendor/lokivolt/config" "\$AOSP_DIR/vendor/lokivolt/products"
cp "\$ROOT/config/identity-policy.json" "\$AOSP_DIR/vendor/lokivolt/config/"
cp "\$ROOT/config/reset-flow.json" "\$AOSP_DIR/vendor/lokivolt/config/"
rm -rf "\$AOSP_DIR/packages/apps/LokivoltSetup"
cp -R "\$ROOT/packages/apps/LokivoltSetup" "\$AOSP_DIR/packages/apps/"
cp "\$ROOT/product/lokivolt.mk" "\$AOSP_DIR/vendor/lokivolt/products/"

case "\$TARGET" in
  cf)
    product_file="$(find "\$AOSP_DIR/device/google/cuttlefish" -type f -name 'aosp_cf_arm64_phone.mk' -print -quit 2>/dev/null)"
    [[ -n "\$product_file" ]] || die "Cuttlefish product file not found"
    ;;
  generic-arm64)
    product_file="\$AOSP_DIR/build/make/target/product/aosp_arm64.mk"
    [[ -f "\$product_file" ]] || die "generic arm64 product file not found"
    ;;
  moto-g04s)
    die "Moto g04s target is intentionally blocked until validated device, kernel, vendor, AVB and partition sources are present"
    ;;
  *)
    die "Unknown target: \$TARGET"
    ;;
esac

grep -q 'vendor/lokivolt/products/lokivolt.mk' "\$product_file" || printf '%s\n' 'include vendor/lokivolt/products/lokivolt.mk' >> "\$product_file"

source build/envsetup.sh

case "\$TARGET" in
  cf)
    lunch aosp_cf_arm64_phone-userdebug
    ;;
  generic-arm64)
    lunch aosp_arm64-userdebug
    ;;
esac

m
printf '%s\n' "\$TARGET build complete"
