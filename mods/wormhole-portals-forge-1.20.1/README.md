# Frameless-style Portals — Forge 1.20.1

Independent clean-room reimplementation for Minecraft Forge 1.20.1. The supplied Frameless Portals release targets NeoForge 1.21.1 and cannot be loaded on Forge 1.20.1. The original project is All Rights Reserved; this repository does not redistribute its code, textures, models, shaders or audio.

## Loader and dependencies

- Minecraft 1.20.1
- Forge 47.3.0
- Java 17
- No Immersive Portals dependency
- No external portal-engine dependency

## Current native systems

- Native synchronized portal endpoint entities with persistent two-ended dimension links.
- Proximity activation and spherical boundary-crossing detection.
- Procedural animated shell, inner swirl, border and simple forming/glitch accents.
- Forge dimension transfer for supported server entities. Cross-dimension player transit still uses Forge's normal dimension-transfer path and may show the normal transition.
- Portal Anchor, Tuner and Portal Gun with a two-shot orb workflow.
- Radius presets, mouse-wheel size adjustment, size HUD and a settings panel.
- Anchor modes for bubble, floor, ceiling and wall apertures, with saved block-state restoration records.
- Basic placement obstruction preview.
- On-demand 3x3 destination chunk snapshots, including heightmaps, block entities and light data.
- Off-screen destination-world rendering into a texture projected onto the spherical aperture.
- Limited non-player entity snapshots with client-side ticking and vehicle/passenger relationships.
- Conservative shell-only fallback when Embeddium or Oculus is detected.

## Important limitations — not feature parity

This is now independent of Immersive Portals, but it is not a complete port of Frameless Portals.

The remote view is a bounded prototype: it streams a 3x3 chunk area and periodically resends whole chunks. It does not stream arbitrary render-distance chunks or chunk deltas. Only a limited number of non-player entities are mirrored; remote players, skins, full mob AI, leash synchronization and robust passenger groups are not complete.

Crossing a portal still uses Forge's normal dimension-transfer API. The remote destination can be visible through the bubble, but this branch does not yet provide the original no-freeze/no-loading-screen transition. Collision and interactions through the aperture (picking, mining, placing, projectiles and entity interactions) are not fully redirected into the remote world.

The visuals are custom procedural effects, not the original GPU mask/shader stack. Exact visual/audio parity and a full renderer compatibility matrix are not implemented. Embeddium/Oculus trigger a conservative shell-only fallback; other shader/render replacements have not been validated.

## Install

Put the generated JAR in the `mods` folder with Forge 47.3.0. Do not install Immersive Portals for this mod.

## Build and validation

The root workflow `.github/workflows/wormhole-portals-forge-1.20.1.yml` compiles with Java 17 and uploads the JAR as an Actions artifact. A successful Gradle build proves compile/package integrity only. No Minecraft client/server gameplay test has been performed.

## License

The independent code and documentation in this repository are MIT-licensed. Frameless Portals by Sh4de remains All Rights Reserved; none of its proprietary classes or assets are included.