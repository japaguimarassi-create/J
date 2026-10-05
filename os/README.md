# Lokivolt OS

Lokivolt OS is an Android-compatible operating system layer built on AOSP interfaces with a conservative migration and recovery model.

## Current architecture

- AOSP Android 16 source baseline
- Lokivolt Setup system application
- Two-account role model
- Factory-reset compatible setup flow
- Provider-backed app and data restoration
- Password restoration delegated to the platform password manager
- Verified Boot and device-state gates
- Device-specific hardware enablement kept separate from the generic system layer

## Account roles

EMAIL 1 is the Security Account. It identifies the owner during Lokivolt provisioning and is never used as a password store.

EMAIL 2 is the Restore Account. It identifies the account used to restore supported application data and device backups.

Lokivolt stores role metadata, not passwords, OAuth refresh tokens, or exported password databases.

## Reset flow

1. Confirm the device screen lock.
2. Confirm Security Account EMAIL 1.
3. Create or verify the restore checkpoint.
4. Invoke the standard platform factory-reset path.
5. After reboot, provision the device again.
6. Authenticate EMAIL 1.
7. Authenticate EMAIL 2.
8. Resume supported backup restoration.
9. Re-enable password-manager synchronization through the provider.
10. Verify applications, data, contacts, messages, and settings.

## Hardware status

Moto g04s enablement is not hard-coded from third-party trees. The live device fingerprint, partition layout, AVB state, bootloader state, kernel compatibility, and vendor implementation must be verified before producing a flashable phone image.

## Build targets

- Cuttlefish arm64 for system integration tests
- Generic arm64 system layer
- Moto g04s device target reserved for validated hardware enablement

A source recipe is provided, but a real Moto g04s bootable image is not claimed until kernel, vendor, AVB, partition, and signing requirements are satisfied.

## Upstream references

AOSP backup APIs and Android system behavior are used as architectural references. LineageOS build-soong patterns are used only as open-source build-system references.

os/upstream/UPSTREAMS.md records provenance.
os/device/moto-g04s/README.md records the hardware evidence policy.
os/images/MANIFEST.json records expected image outputs.
os/config/reset-flow.json defines the reset and restoration state machine.
os/config/identity-policy.json defines the two-account role contract.
os/packages/apps/LokivoltSetup contains the system setup application.
os/build/lokivolt-build.sh contains the build entrypoint.
os/assets contains code-generated Lokivolt visual assets.
