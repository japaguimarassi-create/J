# DualLong HyperCore

A compatibility-first numerical extension foundation for Minecraft Forge 1.7.10, designed around the Dragon Block C ecosystem.

**Current milestone: 0.1.0 — numeric core, player NBT sidecar, mod detection and non-invasive coremod audit.**

## Targets

- Minecraft 1.7.10
- Forge 10.13.4.1614
- Java 8 bytecode
- ASM 5 supplied by the Forge runtime
- JRMCore 1.3.51 / Dragon Block C 1.4.85 / JBRA Client 1.6.52 as the primary audit baseline

## What works in this milestone

- `DualLong128`: signed 128-bit two's-complement arithmetic using `high` and `low` `long` words, including parsing, formatting, addition, subtraction, multiplication, division, remainder, shifts and byte serialization.
- Player sidecar storage: nine extended numeric fields are persisted through Forge `IExtendedEntityProperties` into NBT as two longs each.
- Mod detection for JRMCore, DBC, JBRA, DBC Expansion, NPCDBC, CreatureBoost and Ninjin Entities.
- A coremod loading plugin with an identity transformer that records when relevant JRMCore/DBC classes load. It deliberately does not change their bytecode.
- `/dlhc status`, `/dlhc get <stat>` and `/dlhc set <stat> <value>` for operator-level inspection of the sidecar data.

## Important limitation

This release does **not** replace JRMCore's native `int` stats or widen DBC combat. The audited JRMCore methods and packets expose legacy `int` contracts. The sidecar prevents truncation of its own values, but DBC's native combat calculations do not consume those values yet. Real combat integration requires a separate audited transformation of complete read, calculation, packet and UI paths.

## Build

Use a Java 8 JDK and Gradle 6.9.1 with the GTNH-maintained ForgeGradle 1.2.11 fork. The build declares the QLU BMCLAPI Maven mirror as a fallback for legacy Forge userdev artifacts, followed by the official Forge Maven:

```bash
gradle clean test build --no-daemon
```

The resulting JAR is in `build/libs/`. GitHub Actions runs the same tests and build for this branch.

## Commands

- `/dlhc status`
- `/dlhc get POWER_LEVEL`
- `/dlhc set POWER_LEVEL 123456789012345678901234567890`

The `set` command changes only the DualLong HyperCore sidecar value. It does not change the native DBC stat.

## Configuration

The config file is `config/duallonghypercore.cfg`. The initial performance modules remain disabled; no speculative optimization is enabled by default.

## Audit references

See [`docs/AUDIT.md`](docs/AUDIT.md), [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), and [`docs/COMPATIBILITY.md`](docs/COMPATIBILITY.md).
