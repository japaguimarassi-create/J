# Moto G04s Research Dossier

## Verified official facts

Motorola's official support page identifies the moto g04s and provides its software/security, manual and repair resources. Motorola also states that most recent devices participate in its bootloader-unlock program, but eligibility must be checked through Motorola's unlock process.

## External firmware observations

Public firmware listings for Brazilian RETBR variants identify the moto g04s as XT2421-6 and use the codename Lion. They list Android 14 builds including ULAS34.89-208-2 and ULAS34.89-208-4.

Independent hardware/servicing reports describe Lion/Lion_g devices on the UMS9230 platform, with Android 14, A/B state and UFS on some variants.

These observations are not authoritative enough to become flashing rules.

## Engineering rule

The Migration Engine must query the actual phone before selecting a profile or release artifact.

A future device profile may use observed identifiers such as:
- model / SKU
- product/device/codename
- board
- SoC/platform
- build fingerprint
- bootloader state
- verified-boot state
- slot state
- partition topology

The profile must reject ambiguity instead of guessing.

## Bootloader

Motorola's documentation says bootloader compatibility must be checked through the official program. AOSP documents LOCKED and UNLOCKED states and notes that changing state performs a user-data wipe after confirmation.

Therefore the Lokivolt installer will never assume the G04s can be unlocked, and it will never attempt an exploit-based bypass.

## Dynamic partitions / AVB

AOSP documents that dynamic partitions rely on verified boot and that boot-critical partitions such as boot, dtbo and vbmeta remain physical. The Lokivolt planner will therefore inspect the actual topology and AVB state instead of assuming a super partition or a specific flashing layout.

## Next evidence to collect from the real device

The next physical-phone discovery should provide the exact values exposed by:
- ro.product.*
- ro.build.*
- ro.boot.*
- verified boot state
- active slot
- block-device topology where readable
- storage
- available Termux runtime capabilities

The live device remains the source of truth.
