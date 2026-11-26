# Native Forge branch status

- [x] Remove Immersive Portals from Gradle dependencies and runtime metadata.
- [x] Replace external Portal entities with a native Forge entity.
- [x] Native two-ended endpoint creation, persistence, proximity activation and portal management.
- [x] Procedural spherical shell, swirl, border and forming/glitch-style accents.
- [x] Sphere boundary-crossing detection and Forge dimension transfer for supported server entities.
- [x] Portal Anchor, Portal Tuner and Portal Gun items.
- [x] Portal Gun orb projectile, two-shot placement, size presets, mouse-wheel sizing and HUD.
- [x] Anchor bubble/floor/ceiling/wall placement modes with reversible block-state records.
- [x] Basic placement preview and obstruction warning.
- [x] Portal settings GUI and server-validated radius/range/enable/remove controls.
- [x] Portal settings GUI destination cycling and border toggle.
- [x] Own remote ClientLevel and LevelRenderer, using a bounded off-screen render target.
- [x] Remote 3D chunk snapshots for a 3x3 area around the destination camera, loaded on demand.
- [x] Remote chunk/light/block-entity application on the client.
- [x] Limited non-player entity snapshots with client ticking and vehicle/passenger relationship reconstruction.
- [x] Remote sphere projection using the destination view texture.
- [x] Client world/texture cleanup on disconnect and buffer release.
- [x] Fallback to the shell view when Embeddium/Oculus is detected.
- [x] CI compile/package verification and no-Immersive runtime metadata check.
- [ ] Extend remote streaming beyond the fixed 3x3 area and send chunk deltas instead of periodic snapshots.
- [ ] Remote player mirrors and skin/profile synchronization.
- [ ] Seamless no-freeze traversal without Forge's regular dimension transition.
- [ ] Full through-aperture collision, entity interaction, mining and projectile interaction.
- [ ] Original-grade GPU mask/shader pipeline and complete visual/audio parity.
- [ ] Full leash synchronization and remote mob AI simulation.
- [ ] Renderer compatibility matrix beyond the conservative Embeddium/Oculus fallback.
- [ ] In-game client/server testing (explicitly excluded for this task).

Latest CI must be read from the latest commit on this branch. Build success proves compilation and packaging only; it does not prove in-game behavior.