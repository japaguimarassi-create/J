# VoxMobs — Minecraft Forge 1.20.1

VoxMobs é um mod independente para Minecraft Java Edition 1.20.1, Forge 47.4.28 e Java 17. Ele adiciona conversas com criaturas, vozes individuais, memória persistente e ações validadas no mundo.

O CreatureChat enviado na conversa foi analisado somente como referência de recursos. O VoxMobs tem implementação e identidade próprias; não copia o código nem os recursos visuais do outro mod.

## Cérebro offline com 100.000 parâmetros

O mod contém uma rede neural compacta implementada em Java puro, sem servidor de IA, endpoint, chave, token ou API remota. O modelo possui exatamente **100.000 parâmetros treináveis** e cinco saídas interligadas:

- **Fala:** classifica a intenção comunicativa (cumprimento, pergunta, aviso, preferência, ajuda e outras categorias); um gerador local de frases transforma a intenção em resposta em português.
- **Ação:** estima a ação adequada entre classes como seguir, aproximar, fugir, proteger, pegar e soltar item.
- **Reação:** estima estados como curiosidade, alegria, medo, alerta, confusão e afeto.
- **Memória:** ajuda a classificar fatos e eventos relevantes para retenção.
- **Expressão vocal:** escolhe a emoção de fala que modula o sintetizador.

A rede usa um núcleo compartilhado, cinco cabeças de saída e 64 adaptadores de espécie. As conversas são lembradas por par mob/jogador no arquivo de mundo, enquanto os pesos do cérebro são guardados em `config/voxmobs/brain-100k.dat`.

No primeiro início, o modelo treina com um corpus português incluído no próprio código. O treino passa por temperaturas de 0,55 a 1,28, valida periodicamente a perda e revisa exemplos fáceis e difíceis: os exemplos com maior erro recebem treino adicional e os mais bem aprendidos são repetidos com peso menor para consolidar o comportamento. Depois, cada ação confirmada ou rejeitada pode ajustar os pesos localmente. Administradores também podem ensinar uma frase de comando específica com `/voxmobs teach FOLLOW "me acompanhe até a vila"`; o exemplo passa por 48 atualizações em um ciclo de seis temperaturas variadas e os pesos são gravados localmente. Esse comando exige permissão de operador nível 2. `/voxmobs brain` mostra a contagem e os resultados de aprendizado.

**Limite realista:** 100 mil parâmetros não equivalem a um LLM grande e não tornam o sistema perfeito. Este cérebro é um classificador multitarefa pequeno, acoplado a memória, regras de segurança e modelos de resposta locais. Ele não inventa conhecimento geral como um modelo de bilhões de parâmetros. Os dados incluídos são um conjunto inicial de treino, não milhões de exemplos humanos revisados.

## Vozes individuais

Cada mob recebe uma identidade vocal estável, derivada do UUID da entidade, do identificador de espécie e do nome. O nome vocal combina um nome sorteado com um sufixo curto derivado do identificador para diferenciar criaturas que tenham nomes-base iguais. Assim, dois creepers podem ter vozes diferentes e o mesmo mob mantém sua identidade ao falar novamente.

O sistema sorteia uma apresentação vocal **feminina ou masculina** e associa um nome próprio à voz. Os bancos de nomes são distintos. O perfil também varia pitch, brilho, velocidade, nasalidade, formantes e aspereza conforme a espécie e o indivíduo. A emoção escolhida pelo cérebro altera a interpretação vocal sem trocar a identidade básica.

Em `config/voxmobs-client.toml`, `voiceGenderMode` aceita `random`, `feminine` ou `masculine`. `showVoiceIdentity` vem ativado por padrão e mostra o nome e a apresentação vocal sorteados ao falar.

O TTS é um sintetizador formântico original em Java que gera PCM localmente. **Não é uma voz neural natural** nem uma gravação humana; a saída é deliberadamente sintética e pode precisar de mais trabalho de fonética e prosódia.

## Voz do jogador: STT local

Mire em um mob, segure `J`, fale e solte a tecla. O áudio é capturado no cliente, reamostrado e transcrito localmente pelo Vosk em português brasileiro. Só o texto reconhecido é enviado ao servidor do mundo. O áudio bruto não é transmitido.

Para manter o mod sem downloads automáticos ou conexões externas, o modelo de reconhecimento e a biblioteca nativa precisam ser instalados manualmente. Consulte [`VOICE_INSTALL.md`](VOICE_INSTALL.md). Depois da instalação, o reconhecimento funciona sem internet. A síntese TTS própria não precisa de modelos externos.

## Ações do mundo

Mire em um mob e use `!mob sua instrução` no chat, ou fale com `J`:

| Instrução | Comportamento |
|---|---|
| `me siga` / `vem comigo` | O mob segue o jogador |
| `venha aqui` / `chegue perto` | Aproxima-se |
| `fuja` / `fique longe` | Tenta se afastar |
| `olhe para mim` | Olha para o jogador |
| `sente` | Só funciona para animal domesticado e seu dono |
| `pule` | Salta |
| `pare` | Interrompe navegação e acompanhamento |
| `me proteja` | Acompanha e reage a ameaças próximas |
| `pegue o item` | Pega um item solto próximo, se a mão principal estiver vazia |
| `solte o item` | Joga no chão o item que estiver na mão principal |
| `spawn modid:entidade` | Tenta criar uma entidade registrada como `Mob`, inclusive de outros mods instalados |

A ação de spawn aceita identificadores do registro Minecraft/Forge, por exemplo `minecraft:zombie` ou `meumod:guardiao`. O namespace e a entidade precisam existir no modpack/servidor. O spawn tem cooldown por entidade, limite local de criaturas e validação de espaço e borda do mundo. Pode ser desativado pelo servidor com `allowMobSpawning = false`.

O mod não executa texto arbitrário como comando de console. Ele interpreta uma lista de ações internas permitidas; isso evita que uma conversa com uma criatura vire acesso irrestrito ao servidor.

## Controles e comandos

| Ação | Controle |
|---|---|
| Conversar por texto | Mire para um mob e digite `!mob sua mensagem` |
| Conversar por voz | Mire para um mob, segure `J`, fale e solte `J` |
| Ver status | `/voxmobs status` |
| Ver estado do cérebro | `/voxmobs brain` |
| Ensinar um comando novo (operador) | `/voxmobs teach FOLLOW me acompanhe até a vila` |
| Apagar suas memórias | `/voxmobs forget` |

A tecla `J` pode ser alterada em Opções → Controles → VoxMobs.

## Instalação

1. Use Minecraft **Java Edition 1.20.1**, Forge **47.4.28** e Java **17**.
2. Compile o projeto ou baixe o artefato `voxmobs-1.20.1` produzido pelo GitHub Actions quando o workflow estiver verde.
3. Coloque o JAR em `mods` no cliente e no servidor.
4. Para conversar por texto e ouvir o TTS, não precisa instalar o modelo de reconhecimento de voz.
5. Para usar o microfone, instale o Vosk local conforme [`VOICE_INSTALL.md`](VOICE_INSTALL.md) e autorize o microfone no sistema operacional.

O mod é para Minecraft Java desktop. Não é um addon Bedrock e não foi validado no Minecraft Trial, mobile ou PojavLauncher/Android.

## Arquitetura

```text
Texto ou voz do jogador
        │
        ├── Chat digitado
        │
        └── Captura PCM → Vosk local → texto
                                   │
                                   ▼
                 validação de entidade/distância/limite
                                   │
                                   ▼
                  memória por mob + jogador + contexto
                                   │
                                   ▼
             núcleo compartilhado de 100.000 parâmetros
                   │          │          │
                fala       ação       reação
                   │          │          │
                memória    validação   emoção vocal
                   │          │          │
                   └──────────┴──────────┘
                              │
                    resposta e ação internas
                              │
                 validação e execução no servidor
                              │
                 TTS formântico e perfil individual
                              │
                           alto-falante
```

## Limitações conhecidas

- A rede de 100 mil parâmetros é pequena e especializada; pode classificar incorretamente frases novas ou ambíguas.
- O modo offline usa corpus local, templates e heurísticas; não é um LLM generativo nem entende todo assunto.
- O TTS é formântico e robótico. Os nomes e gêneros indicam perfis de timbre, não vozes humanas gravadas.
- O modelo Vosk small pode errar com ruído, sotaques e nomes de mobs de mods.
- `PICKUP_ITEM` considera apenas itens soltos próximos e exige a mão principal vazia. `DROP_ITEM` solta apenas o item da mão principal.
- `SPAWN_MOB` só cria entidades que estejam registradas e disponíveis no modpack; não baixa nem instala outros mods.
- A ação `SIT` só funciona para animais domesticados e quando o jogador é o dono.
- O projeto é para Forge 1.20.1 / Java 17; não há suporte a Fabric, NeoForge, Bedrock ou mobile nesta versão.
- A compilação completa do Forge precisa ser confirmada pelo GitHub Actions. O ambiente de edição não conseguiu baixar o Gradle por falha de DNS; por isso, os testes locais do núcleo Java não são apresentados como uma compilação completa do mod.

## Construção

Requisitos: JDK 17 e Gradle 8.8.

```bash
gradle --no-daemon test build
```

O workflow do GitHub executa testes e build e publica o JAR como artefato.

## Licenças e créditos

- Código VoxMobs: MIT.
- Vosk Java e biblioteca nativa: Apache License 2.0, de Alpha Cephei.
- `vosk-model-small-pt-0.3`: Apache License 2.0, conforme catálogo oficial de modelos Vosk.
- Forge/Minecraft: dependências e marcas pertencem aos seus respectivos titulares.

Consulte [`THIRD_PARTY.md`](THIRD_PARTY.md) e [`VOICE_INSTALL.md`](VOICE_INSTALL.md) para detalhes.
