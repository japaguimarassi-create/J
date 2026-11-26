# Frameless-style Portals — Forge 1.20.1

This is an independent clean-room implementation project for Forge 1.20.1. The supplied Frameless Portals release is a NeoForge 1.21.1 binary and is not loadable on Forge 1.20.1. The original project is All Rights Reserved; no original code or assets are redistributed.

## Loader and dependencies

- Minecraft 1.20.1
- Forge 47.3.0
- Java 17
- No Immersive Portals dependency
- No external portal engine dependency

## Native systems in this branch

- Own synchronized portal endpoint entity with NBT persistence.
- Two-sided portal-pair creation between loaded dimensions.
- Proximity-based opening and closing.
- Procedural animated spherical shell, forming/glitch accents, center swirl and optional fire border.
- Portal transit for server entities, including players, mobs, projectiles, dropped items, boats and minecarts.
- Nether coordinate scaling and destination Y selection.
- Portal Anchor, Portal Tuner and Creative Portal Gun tools.
- Placement preview shell and commands for creation, listing, inspection, resizing, range, retargeting, link state and removal.
- GitHub Actions build with Java 17.

## What this is not yet

This branch is no longer based on Immersive Portals. However, removing that dependency does not magically provide Frameless's core render engine. The independent live-dimension viewport, destination chunk/entity streaming, off-screen world rendering, portal camera mapping and seamless no-freeze player crossing are not complete. Current entity transit uses Forge's ordinary dimension-transfer API, so it can show the usual transition/loading behavior. The shell is procedural geometry, not a real live view into the destination world.

Also incomplete: the full Anchor configuration panel, obstruction/clearance preview and validation, floor/ceiling/wall placement and reversible terrain carving, Portal Gun projectile/orb workflow and size HUD, entity/leash/AI synchronization, interactions through the aperture, terrain blending, and renderer/shader compatibility hooks. Do not treat these omissions as implemented.

## Renderer compatibility

No Embeddium/Oculus or shader-pack compatibility is claimed. Frameless's published release declares those renderer replacements incompatible; this native branch still needs its own renderer matrix and in-game validation.

## Build and install

GitHub Actions builds the source and uploads a JAR. Put the resulting JAR in the mods folder alongside Forge 47.3.0. Immersive Portals is not required and should not be installed for this mod.

## Testing

Compile/package verification can be run by GitHub Actions. No Minecraft client or dedicated-server gameplay test has been performed. A successful Gradle build is not evidence that rendering, movement, networking or multiplayer behavior works in-game.

## License

The independent code in this repository is MIT-licensed. Frameless Portals by Sh4de remains All Rights Reserved; its code, textures, models, shaders and audio are not included.