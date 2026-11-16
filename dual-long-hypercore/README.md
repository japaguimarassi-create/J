# DualLong HyperCore — Minecraft Forge 1.7.10

Dedicated development branch: `feature/dual-long-hypercore-1.7.10`

This directory contains the source archive for DualLong HyperCore 0.1.0. Extract `DualLongHyperCore-0.1.0-source.tar.xz`; it contains the Gradle project, Java sources, tests, CI workflow and technical audit.

## Verified baseline
- Minecraft 1.7.10 / Forge 10.13.4.1614
- Java 8 target bytecode; ASM 5 from Forge runtime
- JRMCore 1.3.51, Dragon Block C 1.4.85 and JBRA Client 1.6.52
- Optional audit targets: DBC Expansion 1.3.2, NPCDBC 1.2.1, CreatureBoost 0.1.1 and Ninjin Entities 1.4.5

## Current implementation
- Signed 128-bit two's-complement arithmetic backed by two `long` words.
- Per-player NBT sidecar storage for extended values.
- Detection of the seven supplied mod IDs.
- A non-invasive LaunchWrapper transformer that records selected class loads.
- Operator commands to inspect and modify only the sidecar values.

## Deliberate compatibility boundary
Version 0.1.0 does not replace JRMCore's binary `int` contracts and does not change DBC's native combat stats. JRMCore methods and packet structures expose legacy `int` values; widening their descriptors would break already-compiled mods. Integration into live Ki, Power Level, damage, defense, HUD and network flows is a later milestone that requires complete call-path and packet auditing.

## Build
Use JDK 8 and Gradle 6.9.1 with the GTNH-maintained ForgeGradle 1.2.11 fork. From the extracted project directory:

```bash
gradle clean test build --no-daemon
```

The GitHub Actions workflow in the source archive performs the same build and test sequence.
