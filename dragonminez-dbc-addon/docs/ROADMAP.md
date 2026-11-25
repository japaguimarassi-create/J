# Roadmap

## 0.1.0 — Playable foundation

- [x] Forge 1.7.10 project scaffold
- [x] Persistent Angel Lineage state
- [x] Divine Altar + Divine Sigil awakening loop
- [x] Attendant Staff + Divine Instinct
- [x] Configurable energy, cooldown, duration, and evade chance
- [x] Operator test commands
- [x] DBC/JRMCore class-presence detection without compile-time dependency

## 0.2.0 — DBC adapter

- Inspect exact target DBC/Reforged builds and their public APIs.
- Add an optional reflective adapter for reading DBC race/form data.
- Add a compatibility matrix for original DBC, DBC Reforged, and DBC Additions.
- Do not overwrite race arrays or player NBT keys without version-specific tests.

## 0.3.0 — Angel presentation

- DBC-style halo/aura assets.
- Angel-themed equipment and visual overlays.
- Player rendering integration only after the selected DBC renderer path is verified.
- Optional Glind detection and shared divine progression rules.

## 0.4.0 — Forms and Ki integration

- Angel progression tiers and mastery.
- Divine Ki costs routed through a versioned DBC adapter.
- Form unlock rules and server/client synchronization.
- Multiplayer tests for dedicated servers.

## 0.5.0 — DMZ world content

- Time Chamber access point and compact dimension.
- Demon Realm region and structures.
- NPC quest hooks built in-house; no CustomNPC+ requirement.
- More Dragon Ball items, structures, and progression.

## Stability gates

- Never mutate a player's DBC race or form data without a backup/migration path.
- Never assume Reforged and original DBC share identical race indexes.
- Keep optional mods optional.
- Validate client and dedicated-server class loading separately.
