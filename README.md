# Reality Engine AI 0.2.0

Experimental mod for Minecraft Java 1.7.10, Forge 10.13.4.1614 and Java 8.

## Improvements
- Build-time generated custom item, block, computer and entity textures; no Nether Star texture reuse.
- Dedicated renderer and bundled skin for the generated creature.
- Offline command classifier with exactly 300,000 trainable scalar parameters.
- Ambiguous requests do not silently create generic objects.
- Block placement uses ray tracing or the player's look direction and searches free spaces without blindly moving down.
- A computer block opens an interactive GUI with buttons for loaded mods, registry summary, help and current project.
- Runtime compatibility catalogue reads Forge's actual loaded mod list plus registered blocks/items.
- Real sword, pickaxe and food item, plus an artifact that applies only recognized effects.
- Dimension metadata is persisted; creating a dimension never automatically teleports the player.
- The computer retrieves relevant notes from the bundled offline reference corpus.

## Chat command examples
The first word must be exactly crie, case-insensitively. /crie, crielobo and sentences where crie appears later are ignored.

- crie um computador em bloco
- crie um bloco de cristal
- crie uma espada
- crie uma picareta
- crie um dragão
- crie uma dimensão de neve
- crie lista de mods instalados
- crie liste os blocos registrados
- crie buscar registro tinkers
- crie entrar na dimensão 3
- crie ajuda

For ambiguous requests, the mod creates nothing and asks for a more specific type.

## Parameter count and training
The offline classifier has 300,000 parameters: 881 token/bigram buckets × 256; 256 input-bias values; a 256 × 264 dense layer plus 264 biases; and a 264 × 24 output layer plus 24 biases. The build script trains it from Portuguese and English intent examples and packages float32 weights into the JAR.

This is not a general-purpose LLM and does not contain 300,000 independent facts. Reference notes are bundled as offline text, and custom sprites are generated at build time. No external service or API is used by the finished mod.

## Compatibility and honest limits
The mod enumerates Forge's loaded mod containers and public block/item registries. Seeing a mod in the list is not the same as understanding its private internals or automatically generating its objects. The current dimension uses Minecraft's vanilla chunk generator with a selected biome; it is not yet an arbitrary voxel-world engine. The 300k classifier does not learn image/video semantics; no video corpus or multimodal model is bundled.

CI verifies compilation, model weight count, resource packaging and parsing tests, but does not replace a real in-game Forge test. Test on a backup world first. Dimension metadata is stored in config/realityengineai-dimensions.properties.


## Runtime configuration engine (0.3.0)

The mod now includes a data-driven runtime extension layer. It adds behavior through Forge events and registered mod APIs; it does **not** edit, overwrite, or repackage Minecraft's base JAR or source files. The configuration is loaded from:

\`config/realityengineai/runtime-rules.json\`

Rules listen for:
- \`player_interact\` — right-clicking a block or air.
- \`block_break\` — breaking a block.
- \`entity_tick\` — periodic entity updates, throttled to once per 20 ticks per entity.
- \`world_tick\` — periodic world updates, throttled to once per 20 ticks.

Supported actions:
- \`message\`
- \`set_block\` (uses a block registry ID and coordinate offsets)
- \`give_item\` (uses an item registry ID)
- \`potion\`
- \`set_time\`
- \`weather\`
- \`explosion\` (power is capped at 2)
- \`spawn_entity\`

The engine limits the number of rules and actions, clamps cooldowns and dangerous values, and catches per-action failures. It does not allow generated text to execute arbitrary Java, edit class files, or write to Minecraft's installation. This protects the world and the user's files while still allowing behaviors to be assembled and changed without rebuilding the mod.

### Let the AI create a rule

Chat command examples (the first word must be exactly \`crie\`):
- \`crie configuração: quando clicar no bloco minecraft:stone, coloque minecraft:dirt acima\`
- \`crie configuração: quando quebrar bloco minecraft:stone, dar item minecraft:diamond\`
- \`crie configuração: quando clicar, mensagem Olá, regra executada\`
- \`crie configuração: quando clicar, mudar para noite\`
- \`crie configuração: quando clicar, ativar chuva\`
- \`crie configuração: quando clicar, criar explosão\`

A generated rule is validated and appended to \`runtime-rules.json\`, then reloaded. If the prompt does not identify a supported event and action, the engine declines rather than inventing a random block or item. For more complex combinations, edit the JSON rules file using the schema of the example rule, then run \`crie recarregar regras\`.

### Example rule

\`\`\`json
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
\`\`\`

Registry IDs may refer to blocks/items registered by other Forge mods, for example \`othermod:machine_block\`, provided that mod is loaded and its registry ID is correct. Entity spawning currently uses entity names exposed through Minecraft's entity registry; some modded entities may not be registered there.

**Scope limit:** a configuration engine cannot implement literally every possible change to Minecraft's internals. Features needing new rendering pipelines, new engine algorithms, new packets, or transformations of private vanilla methods may require a dedicated Forge integration or an ASM coremod. Those can still run without changing the original Minecraft JAR, but they are separate, version-sensitive code and are not silently synthesized by this rules engine.
