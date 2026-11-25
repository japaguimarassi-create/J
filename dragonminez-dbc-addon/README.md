# DragonMine Z — DBC Edition

A Forge 1.7.10 addon prototype that rebuilds selected DragonMine Z ideas inside the Dragon Block C ecosystem while preserving the older DBC visual and gameplay constraints.

## Target

- Minecraft Java 1.7.10
- Forge 10.13.4.1614
- Java 8
- No mandatory companion mods beyond the normal DBC installation stack
- DBC/JRMCore are detected reflectively; this first slice does not compile against or patch their closed internals

## Playable slice in 0.1.0

- Persistent Angel Lineage progression stored on the player.
- Craftable Divine Sigil and Divine Altar.
- Awakening costs 30 vanilla XP levels and one Divine Sigil.
- Craftable Attendant Staff.
- Divine Instinct: 8 seconds of Speed II and Jump Boost I, a 20% chance to evade direct incoming hits, 30 Divine Energy cost, and a 30-second cooldown.
- Divine Energy regenerates by 1 point per second while the ability is inactive.
- /dmzdbc status displays progression and compatibility detection.
- /dmzdbc admin unlock <player> and /dmzdbc admin reset <player> are operator-only testing commands.
- Player progression is saved and copied across death/respawn.

## Important integration boundary

Version 0.1.0 does not register a new DBC race ID, replace player models, or write to JRMCore private static race arrays. Angel is an addon lineage layered over the player's existing DBC race. That keeps the first release non-destructive and avoids breaking race IDs supplied by DBC Reforged or other race addons.

The mod does not require GeckoLib, Curios, CustomNPC+, TerraBlender, or a mixin loader. The staff ability currently uses Forge player events and potion effects; it does not yet consume DBC Ki.

## Race/content mapping

| DragonMine Z concept | DBC-side strategy |
|---|---|
| Human, Saiyan, Namekian, Majin | Keep the native DBC races |
| Frost Demon | Use DBC Arcosian rather than adding a duplicate race |
| Bio-Android | Reuse an existing DBC Additions/Reforged implementation when installed; no hard dependency in 0.1.0 |
| Glind | Reuse the existing DBC Reforged race when present; do not register a second Glind ID |
| Angel | Addon-owned Angel Lineage in 0.1.0; native race/model integration is a later adapter |
| Divine Ki / Ultra Instinct | First slice provides Divine Energy and Divine Instinct; DBC Ki/form integration is later work |

## Build

Use JDK 8 and Gradle 4.10.3.

    gradle -p dragonminez-dbc-addon build --no-daemon

The jar is written to dragonminez-dbc-addon/build/libs/.

GitHub Actions builds the addon on pushes to the addon branch and stores the jar as a workflow artifact.

## Install

1. Install Minecraft 1.7.10 with Forge 10.13.4.1614.
2. Install the normal DBC files required by your chosen DBC distribution (DBC, JRMCore, and JBRA Client).
3. Put dragonminez-dbc-addon-0.1.0.jar in the mods folder.
4. Launch and craft the Divine Sigil, Divine Altar, and Attendant Staff.
5. Bring 30 XP levels and one Divine Sigil to the altar, then right-click it.
6. Hold the Attendant Staff and right-click to activate Divine Instinct.

Back up existing worlds before testing any new 1.7.10 mod.

## Research references

- DragonMine Z feature and dependency overview: https://www.curseforge.com/minecraft/mc-mods/dragonminez
- Dragon Block C requirements and guide: https://main.jingames.net/how-to-play-dragon-block-c-guide/
- DBC Reforged and its Glind entry: https://www.curseforge.com/minecraft/mc-mods/dbc-reforged
- DBC Additions race and form catalogue: https://www.curseforge.com/minecraft/mc-mods/dragon-block-c-additions
- Example of a DBC custom-race implementation (reference only; no source copied): https://github.com/Hedaox/OmniKings

## License

MIT. This project does not bundle DBC, JRMCore, JBRA Client, or DragonMine Z assets or code.
