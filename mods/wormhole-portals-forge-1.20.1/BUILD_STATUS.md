# Native Forge branch status

- [x] Remove Immersive Portals from Gradle dependencies and runtime metadata.
- [x] Replace external Portal entities with a native Forge entity.
- [x] Native two-ended endpoint creation, persistence, proximity activation and portal management.
- [x] Procedural spherical shell, swirl, border and forming/glitch-style accents.
- [x] Sphere boundary-crossing detection and Forge dimension transfer for supported server entities.
- [x] Portal Anchor, Portal Tuner and Portal Gun items.
- [x] Portal Gun orb projectile, two-shot placement, size presets, mouse-wheel sizing and HUD.
- [x] Anchor bubble/floor/ceiling/wall placement modes.
- [x] SavedData block-state restoration records for carved terrain.
- [x] Basic placement preview and obstruction warning.
- [x] Portal settings GUI and server-validated radius/range/enable/remove controls.
- [x] Own remote ClientLevel and LevelRenderer.
- [x] Bounded 3x3 snapshots for destination chunks, heightmaps, block entities and lighting.
- [x] Off-screen TextureTarget render and spherical aperture projection for the remote view.
- [x] Limited remote non-player entity snapshots for mobs, dropped items, projectiles and vehicles.
- [x] CI compile/package verification and no-Immersive runtime metadata check.
- [ ] On-demand loading and streaming of arbitrary destination chunks beyond the already-loaded 3x3 area.
- [ ] Remote player mirrors and remote entity client-side simulation.
- [ ] Seamless no-freeze traversal without Forge's regular dimension transition.
- [ ] Full through-aperture collision, entity interaction, mining and projectile interaction.
- [ ] Original-grade shader/mask pipeline, complete visual/audio parity and renderer compatibility matrix.
- [ ] Full entity passenger, leash and mob-AI synchronization.
- [ ] In-game client/server testing (explicitly excluded for this task).

The previous 0.2.0 artifact belongs to the old Immersive-Portals-based branch and is not the artifact for this native branch. Only use a JAR produced by a successful workflow run on `frameless-portals-forge-1.20.1-native`.