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
The offline classifier has 300,000 parameters: 1,000 token/bigram embeddings × 256; 256 input-bias values; a 256 × 120 dense layer plus 120 biases; and a 120 × 24 output layer plus 24 biases. The build script trains it from Portuguese and English intent examples and packages float32 weights into the JAR.

This is not a general-purpose LLM and does not contain 300,000 independent facts. Reference notes are bundled as offline text, and custom sprites are generated at build time. No external service or API is used by the finished mod.

## Compatibility and honest limits
The mod enumerates Forge's loaded mod containers and public block/item registries. Seeing a mod in the list is not the same as understanding its private internals or automatically generating its objects. The current dimension uses Minecraft's vanilla chunk generator with a selected biome; it is not yet an arbitrary voxel-world engine. The 300k classifier does not learn image/video semantics; no video corpus or multimodal model is bundled.

CI verifies compilation, model weight count, resource packaging and parsing tests, but does not replace a real in-game Forge test. Test on a backup world first. Dimension metadata is stored in config/realityengineai-dimensions.properties.
