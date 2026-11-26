# Frameless-style Portals — Forge 1.20.1

Independent clean-room implementation work for Minecraft Forge 1.20.1. The supplied Frameless Portals release targets NeoForge 1.21.1 and cannot load on Forge 1.20.1. Its license is All Rights Reserved; this repository does not redistribute its classes, source, textures, shaders, models, audio or other proprietary assets.

## Loader and dependencies

- Minecraft 1.20.1
- Forge 47.3.0
- Java 17
- No Immersive Portals dependency
- No external portal engine dependency

## Native systems currently implemented

- Own synchronized portal endpoint entity with NBT persistence and two-ended links.
- Proximity activation and closing, configurable size and range, optional border effects, custom procedural sphere/swirl/glitch accents.
- Server-side sphere-crossing detection and dimension transit for players, mobs, projectiles, dropped items and vehicles, with cooldown protection.
- Remote destination chunk snapshots, including heightmaps/block entities/lighting, sent to nearby players.
- Auxiliary client-side ClientLevel for the remote dimension and a separate LevelRenderer.
- Off-screen TextureTarget rendering of the remote ClientLevel, camera mapping aligned with the player's view, and projection of that image onto the visible spherical aperture.
- Remote non-player entity snapshots for mobs, items, projectiles and vehicles, updated into the auxiliary ClientLevel.
- Portal Anchor, Portal Tuner and Creative Portal Gun with an orb projectile, two-shot endpoint placement, radius presets, mouse-wheel sizing and HUD display.
- Anchor placement modes (bubble/floor/ceiling/wall) with saved block-state records for later restoration.
- Placement-preview shell with basic entity-obstruction warning.
- P-key settings panel and server-validated controls for portal radius, activation range, active state and removal.
- Commands for placement, inspection, resizing, range, retargeting, link state, scaling and removal.
- GitHub Actions build with Java 17 and a runtime metadata check confirming no Immersive Portals mod dependency.

## Remaining parity gaps

This is a native independent implementation, not a verified exact recreation of the original Frameless engine. Remote view currently sends a bounded 3×3 snapshot of chunks that are already loaded in the destination dimension and updates non-player entity snapshots in a limited region. It does not yet request/load arbitrary remote chunks on demand, mirror other players, simulate remote entities client-side, or synchronize their AI/leashes and passenger graphs.

Cross-dimensional transit still uses Forge's regular dimension-transfer API after detecting a sphere crossing. Therefore it may show the normal dimension transition/loading behavior; seamless no-freeze player crossing with continuous same-session world state is not complete.

Other gaps: exact original GPU mask/shader pipeline; full forming/waiting animation and sound design; advanced placement clearance/collision preview; full door/terrain shaping and rollback fidelity; through-aperture block/entity interaction, mining and projectile collision; mob pursuit/leash synchronization; the original Portal Gun orb/resize UI parity; terrain blending; and a complete renderer compatibility layer.

## Renderer compatibility

No Embeddium/Oculus or shader-pack compatibility is claimed. The original release's declared renderer limitations do not automatically define this independent implementation's behavior. This port still needs its own renderer matrix and in-game validation.

## Install

Put the JAR produced by the native branch's GitHub Actions workflow in the mods folder with Forge 47.3.0. Immersive Portals is not required and should not be installed for this project.

## Verification

GitHub Actions verifies Java 17 compilation, JAR packaging, and the absence of an Immersive Portals runtime dependency. No Minecraft client or dedicated-server gameplay test has been performed, by request. A successful Gradle build does not prove that the remote view, movement, networking, mod compatibility or multiplayer behavior works in-game.

## License

The independent code and documentation in this branch are MIT-licensed. Frameless Portals by Sh4de remains All Rights Reserved; its code and assets are not included.