# Technical notes

## Why this starts as an independent Forge addon

DragonMine Z targets the modern 1.20.1 Forge ecosystem and uses modern libraries. DBC targets 1.7.10 and has its own older player, transformation, and rendering systems. The code and assets cannot be dropped into one another.

The addon uses Forge 1.7.10 as its runtime and implements the initial progression loop without adding another framework dependency.

## Persistence

DMZDBCData is registered as an IExtendedEntityProperties implementation. Its NBT payload stores Angel Lineage unlock state, Divine Energy, active ability ticks, and ability cooldown ticks.

The data is copied during PlayerEvent.Clone so death/respawn does not erase addon progression.

## DBC compatibility

The compatibility probe checks for DBC and JRMCore classes by name using Class.forName(..., false, ...). It does not load or modify those classes. The addon can start without DBC installed and can report whether the expected DBC runtime is present.

This is deliberately not yet a full race adapter. DBC race registration is sensitive to the version and companion race addons installed. A mismatched race-array mutation can shift race IDs or make character data invalid.

## Balance configuration

The config file exposes maximum Divine Energy, activation cost, active duration, cooldown duration, energy regeneration interval, and direct-hit evade chance. All durations are in ticks (20 ticks = 1 second).
