# Enturma AI — Socializador + Minecraft 1.20.1

Um único projeto com duas partes integradas: o núcleo de IA social (português brasileiro, contexto e memória de conversa) e um mod Forge para Minecraft 1.20.1. O mod não traz outro chatbot separado: ele chama o mesmo backend Enturma usado pelo chat web.

## O que está implementado

- Chat web para conversar e receber ajuda social, com contexto, objetivo, tom e histórico SQLite.
- Backend de inferência local baseado em `Qwen/Qwen3-0.6B`, com fallback de diálogo do lado do mod quando o backend/modelo não está disponível.
- Endpoint de diálogo para o jogo, com contexto de dimensão, bioma, criatura, jogador, estado resumido do mundo e IDs/versões dos mods carregados.
- Persona/contexto distintos por tipo de criatura: aldeão, golem, zumbi, esqueleto, creeper, gato, porco e perfil genérico; entidades de outros mods podem ser ativadas por ID.
- Menu **Mobs: Enturma** na tela de criação de mundo para ativar todos os mobs ou editar IDs de entidades. A configuração fica em `config/enturma-mobs.json`; use `/enturma reload` para recarregá-la no servidor.
- Interação sem substituir comércio vanilla: agache e clique com a mão vazia em um mob habilitado para iniciar uma conversa. O chat normal do jogador é encaminhado ao mob ativo enquanto ele estiver por perto. Também existe `/enturma talk <mensagem>`.
- Ações de jogo: olhar para o jogador, seguir em situações seguras, emitir emotes/partículas, tocar som ambiente e soltar itens registrados no mundo. A quantidade de itens é limitada; apenas tipos de ação permitidos são executados. Não é executado texto arbitrário como comando de console.
- Pesquisa web leve e sob demanda sobre mods, via `ddgs` opcional e cache de 6 horas. O resultado pode não existir para mods obscuros ou páginas bloqueadas.
- Voz TTS opcional: backend `edge-tts` + `ffmpeg` gera PCM e o plugin Simple Voice Chat transmite áudio espacial. Sem Simple Voice Chat, a conversa continua em texto/partículas.
- Pipeline de especialização SFT + LoRA para exemplos sociais e diálogos de mobs; validador de JSONL, testes e workflow de CI para Python e compilação do mod.

## Limites honestos

O pacote **não contém um adaptador LoRA já treinado** e não afirma que houve pré-treinamento de 680 milhões de parâmetros. O modelo usado tem aproximadamente 600 milhões de parâmetros e já vem pré-treinado; o treinamento específico deste projeto ainda deve ser executado e avaliado em hardware adequado. Para carregar um adaptador LoRA já treinado, defina `ENTURMA_ADAPTER=output/enturma-lora` antes de iniciar o backend; o endpoint de saúde informa o adaptador configurado. O JSONL de Minecraft fornece 40 exemplos-semente, não um corpus suficiente para alegar qualidade de produção. A IA recebe um resumo do estado do mundo e a lista de mods; ela não ganha visão completa do mundo nem conhecimento garantido de toda receita de cada mod.

## Requisitos

- Backend: Python 3.10–3.12 recomendado, espaço para baixar os pesos, e memória suficiente para inferência. CPU funciona, mas pode ser lenta. GPU CUDA é recomendada para treinamento.
- Mod: Minecraft 1.20.1, Forge 47.4.28 ou versão compatível da linha 47, Java 17.
- Voz opcional: Simple Voice Chat instalado no servidor e nos clientes que precisam ouvir; para gerar áudio, instale `requirements-voice.txt` e disponibilize `ffmpeg` no PATH.

## Executar a IA

Na pasta raiz do projeto:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Abra `http://127.0.0.1:8000`. Na primeira chamada de geração, Transformers baixa os pesos de `Qwen/Qwen3-0.6B`. Não exponha o backend sem autenticação/limites: esta versão foi feita para uso local ou rede privada.

Para habilitar a voz e a pesquisa web opcionais:

```bash
pip install -r requirements-voice.txt
```

O pacote opcional inclui `edge-tts` e `ddgs`; a síntese depende de acesso à internet e de `ffmpeg` instalado no sistema.

Instale `ffmpeg` separadamente para voz TTS. Endpoints novos: `POST /api/minecraft/dialogue`, `POST /api/minecraft/mod-knowledge` e `POST /api/minecraft/voice`. `/api/health` mostra o estado do modelo.

## Compilar o mod

Requer JDK 17 e Gradle 8.8. O GitHub Actions do projeto compila automaticamente o JAR e publica-o como artifact do workflow.

```bash
cd minecraft-forge
gradle build --no-daemon
```

O JAR sai em `minecraft-forge/build/libs/`. Copie o JAR para a pasta `mods` do perfil Forge 1.20.1. O workflow de CI também disponibiliza um artifact se a compilação for concluída com sucesso. O servidor Minecraft precisa conseguir acessar o backend configurado. O endpoint fica em `config/enturma-common.toml`; para single-player local, `http://127.0.0.1:8000` funciona se o backend estiver no mesmo dispositivo/PC. Para servidor remoto, configure uma URL privada acessível pelo servidor e não publique a porta sem proteção.

## Como usar no jogo

1. Inicie o backend Enturma AI.
2. Abra a criação de mundo e use **Mobs: Enturma** para ativar `Todos os mobs` ou inserir IDs como `minecraft:villager, minecraft:iron_golem, alexsmobs:capuchin`.
3. Crie o mundo e carregue o mod no Forge 1.20.1.
4. Agache e clique com a mão vazia em um mob habilitado. Depois, converse pelo chat normal perto dele ou use `/enturma talk <mensagem>`.
5. `/enturma status` mostra a configuração e `/enturma reload` recarrega a lista de criaturas.

## Treino especializado

Os dados de diálogo social ficam em `data/social_dialogues.jsonl` e os do jogo em `data/minecraft_dialogues.jsonl`. Use diálogos originais ou dados cuja licença permita o uso pretendido; não treine com conversas privadas sem consentimento.

```bash
python validate_dataset.py data/social_dialogues.jsonl
python validate_dataset.py data/minecraft_dialogues.jsonl
pip install -r requirements-train.txt
python train.py --data data/social_dialogues.jsonl data/minecraft_dialogues.jsonl --output output/enturma-lora --epochs 3
```

Compare o modelo-base e o adaptador em cenários reservados e por avaliação humana de naturalidade, coerência entre turnos, fidelidade ao contexto, variedade, utilidade social e qualidade das ações antes de distribuir o adaptador. O número de parâmetros do modelo-base não aumenta com LoRA.

## Arquitetura

- `socializer/core.py`: persona social e prompts.
- `socializer/engine.py`: carregamento/inferência do modelo local.
- `socializer/game.py`: persona de mobs, parsing/normalização das respostas, whitelist de ações, perfis de TTS e pesquisa de mods.
- `app.py`: interface web e API de conversa/jogo/voz/pesquisa.
- `minecraft-forge/`: mod Forge 1.20.1, configuração em criação do mundo, comandos e execução de ações dentro do servidor.
- `.github/workflows/ci.yml`: testes Python, validação dos datasets e build do mod.
