# Wormhole Portals — Forge 1.20.1

Independent clean-room implementation of the core Frameless-style bubble portal behavior for Minecraft Forge 1.20.1. This is not a conversion of the uploaded 1.21.1 NeoForge binary and does not contain its source, textures, shaders, sounds or other proprietary assets.

## Build target

- Minecraft 1.20.1
- Forge 47.3.0
- Java 17
- Immersive Portals 3.0.7 for Forge 1.20.1 (required runtime and compile API)
- Gradle 8.8

## Architecture

The portal aperture is generated as a 20-face icosphere. Each triangle is an actual Immersive Portals view surface, paired with a reverse surface in the destination world. Immersive Portals supplies remote dimension rendering, chunk/view management, portal traversal and cross-portal interaction. The mod controls the spherical grouping, activation, tools and destinations.

A shared link identifier is written to all portal entities. A server ticker opens or closes both ends for all players based on distance. Closed bubbles receive a client-side wireframe shell. Each bubble consists of 40 portal entities (20 faces at each end); this is a deliberate first implementation and has a higher render cost than the original single-mask renderer.

## Implemented in this source build

- Two-way, real-time, no-loading-screen dimensional portals through Immersive Portals.
- Bubble aperture approximated by a 20-triangle icosphere mesh.
- Open/close activation range and shared multiplayer state.
- Nether, End and any currently loaded registered dimension as a destination.
- Nether 8:1 coordinate scaling and default spawn/End destination selection.
- Same-dimension links between two selected points.
- Portal Anchor: click-air to cycle loaded destination dimensions, then use on a block face to place a portal.
- Portal Tuner: click-air to select a destination; use on a nearby portal to cycle its radius; sneak-use on a portal to retarget it; sneak-use with no target selected removes it.
- Creative Portal Gun: two right-clicks place the two bubble endpoints; the next shot replaces the active pair; sneak-use on air cycles size; sneak-use on a surface removes the active pair.
- Commands to list, inspect, place, resize, change activation range, retarget, link/unlink, change scale and remove portals.
- Portal entity metadata is saved through Immersive Portals entity serialization.
- Optional border particles and activation sound.
- GitHub Actions workflow compiles on Java 17 and uploads the mod JAR.

## Feature parity and limits

The uploaded JAR contains additional subsystems beyond the portal entity itself: a custom GPU mask/render pipeline, glitch/forming effects, waiting swirl, custom sound/hum layer, live remote entity/chunk synchronization hooks, projectile/leash/mob-pursuit hooks, terrain/block collision hooks, survival placement previews and option panels, Portal Gun orb/resize UI, and renderer compatibility hooks for supported Sodium/Iris versions. The current implementation does **not** claim exact parity for those systems. It delegates remote view, entity transport and cross-portal interaction to Immersive Portals, and replaces the original GPU mask with a 20-face portal mesh. Shader effects, exact forming animation, target-clearance preview, custom orb projectile UX, mob pursuit/leash synchronization, original renderer compatibility and sound/particle replication remain incomplete and require dedicated Forge 1.20.1 implementations and in-game QA.

No Embeddium/Oculus or shader-pack compatibility is claimed. The original Frameless Portals license is All Rights Reserved; only independently written code and original documentation are included here.

## Commands

All commands require permission level 2:

```text
/wormhole place
/wormhole place <dimension>
/wormhole list
/wormhole info <link-id>
/wormhole target <dimension> <link-id>
/wormhole rule auto <link-id>
/wormhole rule identity <link-id>
/wormhole rule end <link-id>
/wormhole rule scale <factor> <link-id>
/wormhole rule fixed <x> <y> <z> <link-id>
/wormhole size <radius> <link-id>
/wormhole range <blocks> <link-id>
/wormhole link <link-id>
/wormhole unlink <link-id>
/wormhole remove <link-id|all>
```

## Install

Put both JARs in the `mods` folder:

1. The `wormhole-portals-forge-1.20.1` JAR produced by this repository's GitHub Actions workflow.
2. [Immersive Portals 3.0.7 for Forge 1.20.1](https://www.curseforge.com/minecraft/mc-mods/immersive-portals-for-forge/files).

Do not install the Fabric or NeoForge build of Immersive Portals on Forge.

## GitHub build

The root workflow `.github/workflows/wormhole-portals-forge-1.20.1.yml` runs `gradle clean build` on pushes to the `frameless-portals-forge-1.20.1` branch, pull requests and manual dispatch. It uploads the compiled JAR as the `wormhole-portals-forge-1.20.1` artifact. A successful Java compilation is not the same as passing client/server in-game tests.

## License

The independent code in this repository is MIT-licensed. Immersive Portals is installed separately under its own Apache-2.0 license. No Frameless Portals source or proprietary assets are redistributed.
