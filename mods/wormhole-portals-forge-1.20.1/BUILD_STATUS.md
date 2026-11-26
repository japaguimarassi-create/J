# Native Forge branch status

- [x] Remove Immersive Portals from Gradle dependencies.
- [x] Remove Immersive Portals runtime dependency from mods.toml.
- [x] Replace external Portal entities with a native Forge entity.
- [x] Add native endpoint pairing and server-side proximity activation.
- [x] Add procedural sphere/swirl/border rendering.
- [x] Add basic entity dimension transit and cooldown protection.
- [x] Port Anchor, Tuner and command paths to the native entity model.
- [ ] Live remote dimension world and chunk/entity streaming.
- [ ] No-freeze cross-dimensional traversal.
- [ ] Full Anchor config UI and collision preview.
- [ ] Floor/ceiling/wall door placement, carving and rollback.
- [ ] Portal Gun orb projectile, linked-door UX, width/height wheel controls and size display.
- [ ] Full renderer/shader compatibility layer.
- [ ] In-game client/server testing (explicitly excluded for this task).

The previous 0.2.0 artifact belongs to the Immersive-Portals-based branch and must not be used as the native Frameless-style build. This branch is a rewrite and requires a new CI build.