# Build status — DualLong HyperCore 0.1.0

## Automated build

- Workflow run: https://github.com/japaguimarassi-create/J/actions/runs/43782893608
- Branch: `feature/dual-long-hypercore-1.7.10`
- Commit used by successful run: `0b0eee73d80a3fbcfa041da73ff27934ceade47b`
- Environment: Ubuntu 22.04, Temurin Java 8, Gradle 6.9.1, ForgeGradle 1.2.11
- Result: `BUILD SUCCESSFUL`
- Completed tasks include `compileJava`, `compileTestJava`, `test`, `jar`, `reobf` and `build`.
- Uploaded workflow artifact: `DualLongHyperCore-0.1.0` (artifact ID `14189485719`).

## Verified JAR

- File: `DualLongHyperCore-0.1.0.jar`
- SHA-256: `144576e4f102dc782cb3a5450101f4568f0f3fa5d5a710e9b7a70f9018504e2c`
- Class-file major version: `52` (Java 8)
- Archive integrity: passed ZIP/JAR integrity test.
- Manifest declares the Forge coremod loading plugin and `FMLCorePluginContainsFMLMod: true`.

## Scope and remaining validation

This proves that the current source compiles, tests and reobfuscates against the configured Forge 1.7.10 toolchain. It does **not** prove that it has been launched in a live Minecraft instance with the user's exact DBC/JRMCore/JBRA stack.

Version 0.1.0 detects the supplied mod IDs, stores separate 128-bit player values in NBT, provides operator commands for this separate storage, and observes selected class loads using an identity transformer. It does not yet widen native DBC/JRMCore Ki, Power Level, damage, defense, packet fields or HUD displays. It also does not yet enable performance optimizers. Those features require additional call-path analysis and in-game regression tests.

Do not treat the sidecar values as native gameplay stats in this version.
