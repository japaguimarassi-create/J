# IntX — Expanded Numeric Engine

IntX is a Minecraft Forge 1.7.10 framework for values larger than Java's signed 32-bit integer range. The first milestone implements arbitrary-precision player stats, exact NBT persistence, server-authoritative synchronization, commands, a public API, and an optional CoreMod patch adding a Long DataWatcher type.

## Numeric model

Java int is a fixed 32-bit primitive. A mod cannot globally change its width. Blindly replacing every int with long would break JVM descriptors, arithmetic bytecode, packet layouts, NBT schemas, GUIs, and third-party APIs. IntX therefore creates a separate expanded numeric domain instead of claiming universal replacement.

- IntX player stats use java.math.BigInteger and are bounded by configurable digit/resource limits.
- Values persist as decimal strings in player NBT with schema version 1.
- A versioned FML SimpleNetworkWrapper packet synchronizes authoritative server values to the owning client.
- The CoreMod can register java.lang.Long as DataWatcher type 7 after verifying the expected 1.7.10 bytecode structure.
- BigInteger can use IntX packets or DataWatcher's existing String type.
- Legacy int/long conversions are explicit and saturating, never silently wrapping.

Vanilla 1.7.10 living-entity health is not simply an int field: the health path is float-based and attributes such as maximum health use double. Those systems require their own targeted audit.

## Compatibility boundary

The Long DataWatcher extension requires IntX on every peer exchanging Long DataWatcher values. Vanilla DataWatcher types remain unchanged. The 32 DataWatcher object IDs (0–31) are not expanded. If the ASM transformation does not match the expected class structure, the transformer returns the original class and disables only the Long DataWatcher API; BigInteger player stats remain available.

This milestone does not automatically rewrite all vanilla or third-party mod fields. A Dragon Block C / JRMCore adapter must be implemented against the exact installed mod versions after tracing each stat through calculations, storage, NBT, packets, and HUD rendering.

## Target stack

- Minecraft 1.7.10
- Forge 10.13.4.1614
- Java 8
- Gradle 5.6.4
- anatawa12 ForgeGradle 1.2 fork
- ASM 5.0.3

## Commands

Permission level 2; target player must be online:

- /intx set <player> <key> <integer>
- /intx add <player> <key> <integer>
- /intx get <player> <key>
- /intx list <player>
- /intx reset <player> <key>
- /intx debug

Example:
    /intx set Japa power 922337203685477580812345678901234567890
    /intx add Japa power 100000000000000000000000000000000000000
    /intx get Japa power

## Integration API

    BigInteger power = IntXAPI.get(player, "power");
    IntXAPI.set(player, "power", new BigInteger("922337203685477580812345"));
    IntXAPI.add(player, "power", BigInteger.TEN);

Keys match [A-Za-z0-9_.-] and contain 1–64 characters. Defaults: 4096 decimal digits and 128 keys per player. Both are configurable.

DataWatcher helpers:
- DataWatcherNumbers.addBigInteger(watcher, id, value) uses existing String transport.
- DataWatcherNumbers.addLong / updateLong / getLong use type 7 and fail clearly when the patch did not apply.

## Build

Use JDK 8 and Gradle 5.6.4:
    gradle --no-daemon setupDecompWorkspace test build

GitHub Actions runs workspace setup, tests, and build, then uploads the JAR artifact.
