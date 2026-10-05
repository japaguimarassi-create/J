# Upstream provenance

Lokivolt uses public Android and open-source build-system references.

## AOSP

- Android platform manifest: https://android.googlesource.com/platform/manifest
- Android source documentation: https://source.android.com
- Android backup framework reference mirror: https://github.com/aosp-mirror/platform_frameworks_base
- Android backup package reference: https://github.com/aosp-mirror/platform_frameworks_base/blob/main/core/java/android/app/backup/package.html

## LineageOS build-system reference

- LineageOS build-soong: https://github.com/LineageOS/android_build_soong
- Example super-image build implementation: https://github.com/LineageOS/android_build_soong/blob/master/filesystem/super_image.go

## Hardware evidence

No production device tree is accepted solely because a repository name matches "Moto G04s" or "XT2421-6". Device-specific source must be matched against live properties, kernel compatibility, vendor interfaces, partition metadata, AVB state, and licensing provenance.

## Research rule

A third-party tree may be inspected for ideas, but production code must not be copied automatically into the Moto g04s target.
