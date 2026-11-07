# ECLIPSE: BLOOD & BREATH — Roblox Alpha

An original dark-fantasy Roblox Action RPG prototype. The full Rojo source project is included in `EclipseBloodBreath-Alpha.tar.gz`.

## Extract and build

```bash
tar -xzf EclipseBloodBreath-Alpha.tar.gz
cd eclipse-blood-breath-roblox
rojo build default.project.json --output build/EclipseBloodBreath.rbxlx
```

Open the resulting `.rbxlx` in Roblox Studio. To iterate live, run `rojo serve` from the project directory and connect the Rojo Studio plugin.

## Included in this alpha

- Procedural starting village, forest route, training yard and boss arena.
- Two original faction paths: Guardião / Escola da Maré and Criatura / Arte do Abismo.
- Server-validated attacks, heavy attacks, blocking, dodge, energy and faction skill.
- Common enemy AI and a boss with a telegraphed area attack.
- Introductory trial, XP, levels, rank titles, gold and style mastery.
- DataStore profile persistence with a temporary-session fallback on read failure.
- Portuguese HUD, touch controls, keyboard/mouse and basic gamepad actions.

## Status

This is a source-level vertical slice. Roblox Studio execution, two-client multiplayer testing, mobile profiling, DataStore validation in a published test place, final animation/mesh/audio work, and release review remain outstanding. No published Roblox experience or `.rbxlx` build is claimed until CI produces and validates the artifact.

## Intellectual property

All shipped names, factions, setting, skills, characters and procedural assets in this prototype are original. Demon Slayer is used only as a high-level genre and atmosphere reference; no character, logo, music, dialogue, footage, model or animation from that franchise is included.
