# Reality Engine AI 0.3.0

Experimental Minecraft Java 1.7.10 / Forge 10.13.4.1614 mod, built for Java 8.

## Core capabilities
- Offline intent classifier with exactly 300,000 trainable scalar parameters.
- Registered custom items, blocks, creature entities, and themed dimensions.
- Custom generated item/block sprites and creature skin.
- Forge runtime configuration rules that add behavior without modifying the original Minecraft JAR.
- Runtime awareness of loaded Forge mods and registered blocks/items.
- Ray-traced block placement and saved dimension metadata.
- Ambiguous requests are rejected instead of silently creating unrelated objects.

The old demonstration computer block and its chat-only GUI have been removed. They did not provide a real programmable computer and should not be presented as one. Requests for a computer are rejected rather than creating a fake block. A true programmable computer still requires its own implementation.

## Chat command examples
The first word must be exactly crie, case-insensitively. /crie, crielobo, and sentences where crie appears later are ignored.

- crie um bloco de cristal
- crie uma espada
- crie uma picareta
- crie um dragão
- crie uma dimensão de neve
- crie lista de mods instalados
- crie liste os blocos registrados

## Runtime configuration engine (0.3.0)

The mod now includes a data-driven runtime extension layer. It adds behavior through Forge events and registered mod APIs; it does **not** edit, overwrite, or repackage Minecraft's base JAR or source files. The configuration is loaded from:

`config/realityengineai/runtime-rules.json`

Rules listen for:
- `player_interact` — right-clicking a block or air.
- `block_break` — breaking a block.
- `entity_tick` — periodic entity updates, throttled to once per 20 ticks per entity.
- `world_tick` — periodic world updates, throttled to once per 20 ticks.
- `living_hurt` and `living_death` — entity damage and death.
- `entity_join_world` — an entity joins a world.
- `player_login` and `player_respawn` — player login and respawn.

Supported actions:
- `message`
- `set_block` (uses a block registry ID and coordinate offsets)
- `give_item` (uses an item registry ID)
- `potion`
- `set_time`
- `weather`
- `explosion` (power is capped at 2)
- `spawn_entity`

The engine limits the number of rules and actions, clamps cooldowns and dangerous values, and catches per-action failures. It does not allow generated text to execute arbitrary Java, edit class files, or write to Minecraft's installation. This protects the world and the user's files while still allowing behaviors to be assembled and changed without rebuilding the mod.

### Let the AI create a rule

Chat command examples (the first word must be exactly `crie`):
- `crie configuração: quando clicar no bloco minecraft:stone, coloque minecraft:dirt acima`
- `crie configuração: quando quebrar bloco minecraft:stone, dar item minecraft:diamond`
- `crie configuração: quando clicar, mensagem Olá, regra executada`
- `crie configuração: quando clicar, mudar para noite`
- `crie configuração: quando clicar, ativar chuva`
- `crie configuração: quando clicar, criar explosão`

A generated rule is validated and appended to `runtime-rules.json`, then reloaded. If the prompt does not identify a supported event and action, the engine declines rather than inventing a random block or item. For more complex combinations, edit the JSON rules file using the schema of the example rule, then run `crie recarregar regras`.

### Example rule

```json
{
  "id": "stone_click_message",
  "enabled": true,
  "event": "player_interact",
  "block": "minecraft:stone",
  "cooldown_ticks": 20,
  "actions": [
    {
      "type": "message",
      "text": "The runtime rule fired."
    },
    {
      "type": "set_block",
      "block": "minecraft:glowstone",
      "offset_x": 0,
      "offset_y": 1,
      "offset_z": 0
    }
  ]
}
```

Registry IDs may refer to blocks/items registered by other Forge mods, for example `othermod:machine_block`, provided that mod is loaded and its registry ID is correct. Entity spawning currently uses entity names exposed through Minecraft's entity registry; some modded entities may not be registered there.

**Scope limit:** a configuration engine cannot implement literally every possible change to Minecraft's internals. Features needing new rendering pipelines, new engine algorithms, new packets, or transformations of private vanilla methods may require a dedicated Forge integration or an ASM coremod. Those can still run without changing the original Minecraft JAR, but they are separate, version-sensitive code and are not silently synthesized by this rules engine.
