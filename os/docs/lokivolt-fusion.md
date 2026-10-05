# Lokivolt Android-Linux Fusion Architecture

Lokivolt is not designed as Android plus an unrelated Linux installation. Android already uses a Linux-derived kernel architecture: AOSP describes the Android kernel as Linux LTS combined with Android Common Kernel changes, with GKI separating generic kernel code from hardware-specific vendor modules. citeturn770145search2turn770145search0

## Fusion model

The Lokivolt stack is:

Linux/ACK/GKI kernel
-> vendor modules and hardware support
-> Android native daemons and libraries
-> Android Framework and system services
-> Lokivolt Fusion Services
-> Lokivolt UI
-> JARVIS policy-controlled orchestration

AOSP documents Binder as a core IPC boundary and recommends AIDL for current HAL development. SELinux remains the security boundary. citeturn432857search3turn432857search11

## What makes Lokivolt Linux-capable

Lokivolt uses the Linux kernel directly as its operating-system foundation and can expose Linux-oriented tools and native services through Android-compatible interfaces. It does not require pretending that a desktop GNU/Linux distribution is the Android userspace.

The practical result is one OS with:
- Linux kernel primitives and drivers;
- Android application/runtime compatibility;
- Android HAL and Binder/AIDL integration;
- Lokivolt-native system services;
- JARVIS as a policy-constrained control plane;
- an optional future isolated Linux compatibility environment when it can be implemented without weakening Android security.

## Update architecture

Modern Android uses A/B or Virtual A/B update mechanisms, and dynamic partitions are part of the modern update architecture. Lokivolt therefore treats A/B, Virtual A/B, and dynamic partitions as capabilities discovered from the target device, not assumptions. citeturn432857search0turn770145search10

The Moto G04s discovery already exposed A/B and dynamic partitions. That is strong evidence for the compatibility profile, but it does not by itself authorize flashing.

## Security architecture

A locked Android device is a real security state. AOSP states that locked devices prevent unauthorized software from being flashed and verify boot software against the device root of trust. citeturn432857search4

Lokivolt therefore uses two independent decisions:

1. Plan acceptance: 100% when the architecture and observed state are understood.
2. Execution authorization: separately gated by bootloader state, official unlock path, flashing interface, image compatibility, AVB and recovery requirements.

This lets Lokivolt say that a migration plan is fully accepted without falsely granting a privilege that the hardware or platform has not granted.

## Firmware validation

A Lokivolt ROM candidate must match the exact device identity and its required kernel, vendor, boot, AVB, partition and rollback constraints. AOSP's GKI compatibility model also means kernel version and KMI compatibility matter; a different GKI family cannot simply be swapped in and assumed compatible. citeturn770145search8

The project therefore never turns a generic AOSP build into a claimed Moto G04s flash image until device-specific sources have been validated.
