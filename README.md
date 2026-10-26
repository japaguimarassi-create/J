# Reality Engine AI 0.5.0

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

## Runtime configuration engine (0.5.0)

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


## Bot de execução de prompts (0.4.0)

O comando `/bot` cria uma entidade visível que acompanha o jogador:
- `/bot` — gera o bot.
- `/bot crie um mapa do zero raio 24` — gera terreno procedural numa região do mundo atual.
- `/bot crie uma casa`, `/bot crie um castelo de pedra`, `/bot crie uma torre`, `/bot crie uma ponte`, `/bot crie uma cidade`, `/bot crie um labirinto`, `/bot crie um computador` — usa módulos declarativos de construção.
- `/bot status`, `/bot parar`, `/bot remover`, `/bot recarregar`, `/bot modulos`, `/bot ajuda`.

O executor modifica o mundo no ciclo de ticks do servidor e gera operações sob demanda. Não dispara um milhão de comandos simultâneos: isso travaria o servidor. A fila aceita até 1.000.000 operações por tarefa, processando-as em lotes de 128 por tick por padrão. Os limites podem ser editados em `config/realityengineai/bot-settings.json`, dentro dos limites impostos pelo código.

Na primeira execução, o mod cria `config/realityengineai/modules/` e os arquivos `starter-builders.json` e `README.txt`. Os módulos incluem configurações para casas, castelos, torres, pontes, muros, plataformas, arenas, labirintos, cidades, computadores e veículos. Para acrescentar um módulo, use por exemplo `/bot crie um módulo chamado garagem 15x9x7`; depois edite o JSON gerado e rode `/bot recarregar`.

**Limites reais:** o bot é uma entidade de IA do Minecraft, não uma instância genuína de `EntityPlayer`. Ele se movimenta e segue seu proprietário, e o executor constrói com operações permitidas. Um mapa é uma região de terreno no mundo carregado, não um arquivo de mundo separado. O computador é uma construção de blocos, não um PC com sistema operacional real. Executar aplicativos externos ou Fortnite ainda exige uma ponte externa compatível.


## Classificador semântico 0.5.0

O modelo local passou de 24 para 41 classes e usa 2.048 buckets de tokens/bigramas. As categorias separam itens, blocos, entidades, dimensões, construções, terrenos, mapas procedurais e consultas. O total do classificador é 300.393 parâmetros escalares, gravados em assets/realityengineai/brain/weights.bin.

Exemplos de interpretação:
- crie uma espada de pedra -> item/sword
- crie um bloco de pedra -> block/generic
- crie uma construção de pedra -> structure/generic
- crie terreno montanhoso raio 16 -> terrain/mountain
- crie um mapa do zero raio 24 -> map/procedural
- crie uma dimensão de deserto -> dimension/desert
- crie um bloco de máquina -> block/machine
- crie um amuleto de proteção -> item/amulet

tools/train_brain.py usa um corpus específico do projeto. Os exemplos-base são separados entre treino, validação e teste antes da ampliação sintética. A compilação gera training_report.json com perdas, acurácia de teste, macro-F1, F1 por classe, matriz de confusão, número real de gerações e motivo de parada. O limite configurado pode chegar a 500.000 gerações, mas o treino para por estagnação da validação ou pelo limite de tempo; não força a perda a zero nem declara gerações que não ocorreram.

## Pesquisa web controlada

Use /bot pesquisar <assunto> ou “crie pesquise na internet sobre <assunto>”. O recurso faz até três buscas paralelas, guarda URLs, títulos e trechos em config/realityengineai/knowledge/web-research/ e apresenta resultados no chat. As requisições usam timeouts, limite de tamanho da resposta e poucos workers para não bloquear os ticks nem sobrecarregar o dispositivo.

Isso é pesquisa com fontes persistidas, não atualização automática dos pesos neurais a partir de snippets não verificados. O classificador continua sendo uma IA especializada em interpretação de intenções, não um modelo de linguagem genérico. Um serviço público de busca pode bloquear ou alterar as respostas; nesses casos o mod informa que não encontrou resultados.

## Texturas expandidas

O gerador procedural cria texturas próprias para cajado, amuleto e adaga; blocos tecnológico, metálico e corrompido; e skins separadas para criatura, dragão, criatura hostil e robô. Elas são conectadas a itens/blocos registrados ou selecionadas pelo renderer da entidade.

## Referências técnicas consultadas

- Forge 1.7.10 API Javadocs: https://skmedix.github.io/ForgeJavaDocs/javadoc/forge/1.7.10-10.13.4.1614/
- Hugging Face Trainer: https://huggingface.co/docs/transformers/en/main_classes/trainer
- Hugging Face Model Cards: https://huggingface.co/docs/hub/en/model-cards
- scikit-learn Model Evaluation: https://scikit-learn.org/stable/modules/model_evaluation.html
- Intent classification evaluation dataset paper: https://aclanthology.org/D19-1131/

Consulte tools/RESEARCH_SOURCES.md para fontes e o método de avaliação. O modelo continua especializado e limitado ao domínio/corpus usado.


## Version 0.6.0 — Semantic Creation Blueprint

The creation flow preserves the full prompt and derives a structured blueprint before creating an item. The blueprint separates:

- **Object identity:** display name, item category and base archetype.
- **Design inputs:** material/style inferred from the entire request.
- **Purpose and abilities:** action clauses plus a list of independently recognized effects.
- **Source prompt:** the original full request remains stored on the generated stack for later inspection.

For example, `crie uma espada de gelo que congela inimigos e cura o jogador` creates an item named `Espada de gelo`, keeps the entire instruction in NBT, records the ice design and healing/freezing abilities separately, and executes supported abilities instead of using the entire sentence as the display name. Sword and dagger templates can apply their recognized combat effects on hit; compatible self-effects activate on right-click for artifact, staff and amulet templates.

This is template-based customization of registered Forge 1.7.10 items, not arbitrary registration of a brand-new Minecraft item class, a generated 3D model, or unlimited behavior. Effects are explicitly recognized and only supported actions are executed. Unimplemented abilities remain recorded and are reported rather than falsely claimed as working. Training/evaluation and the Forge CI build remain required checks.
