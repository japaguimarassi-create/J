# Nexus Optimizer — Minecraft Java 1.20.1

Forge client-side mod built for Java 17. It uses a small adaptive controller that samples FPS and Java heap pressure, applies progressively stronger video-setting reductions only after repeated poor samples, and restores the original settings after sustained recovery or when leaving a world.

Profiles preserve the chosen graphics mode and ambient occlusion. The controller first reduces particles, clouds, and entity render distance; only the stronger profiles lower render/simulation distance and the strongest profile disables entity shadows. It does not force garbage collection or run background workers.

Build: \`gradle build --no-daemon\`. The reobfuscated mod JAR is placed in \`build/libs/nexusoptimizer-1.0.0.jar\`.
