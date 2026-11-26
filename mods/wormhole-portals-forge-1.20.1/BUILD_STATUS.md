# Build status

The source is intended to compile on GitHub Actions with Java 17, Gradle 8.8, Forge 1.20.1-47.3.0 and Immersive Portals 3.0.7. The workflow must finish successfully and verify the expected output before this build is marked compiled.

Expected artifact: `wormhole-portals-forge-1.20.1-0.2.0-alpha.1.jar`.

The mod still requires in-game validation for portal rendering, entity crossing, placement, client/server synchronization and performance. The 20-face bubble is an approximation, not an exact recreation of the Frameless GPU mask.
