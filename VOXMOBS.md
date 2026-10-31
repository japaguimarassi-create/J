# VoxMobs — Minecraft Forge 1.20.1

Projeto independente para Minecraft Java 1.20.1, Forge 47.4.28 e Java 17.

O código-fonte atualizado está no pacote ZIP entregue nesta conversa. Este branch documenta o projeto; o pacote-fonte ainda não está commitado como árvore de arquivos e não existe uma release/JAR validada.

## Controles

- Mire em um mob e segure **J** para gravar sua fala.
- Solte **J** para concluir a gravação, transcrever localmente em português e enviar somente o texto ao mob.
- Digite `!mob mensagem` no chat para conversar por texto.
- A tecla J aparece em Opções → Controles → Multiplayer e pode ser remapeada.

## Arquitetura offline

- Zero APIs de IA remotas, zero endpoints, tokens e chaves.
- Núcleo neural Java puro com exatamente 100.000 parâmetros treináveis.
- Cinco cabeças interligadas: intenção de fala, ação, reação, memória e emoção vocal.
- Um núcleo compartilhado mais 64 adaptadores hash de espécie; identificadores de entidades registradas por outros mods também podem ser processados. Como são 64 grupos fixos, espécies diferentes podem compartilhar um adaptador.
- Memória persistente individual por UUID de mob e jogador.
- Corpus inicial de 768 exemplos em português. O primeiro treino usa 34 épocas, temperaturas entre 0,55 e 1,28, validação e repetição dos exemplos mais fáceis/difíceis.
- Aprendizado incremental quando uma ação é confirmada ou rejeitada.
- Ensino manual local para administradores: `/voxmobs teach FOLLOW me acompanhe até a vila`. Cada lição faz 48 atualizações em seis temperaturas rotativas e salva os pesos.

## Voz

- Cada criatura recebe perfil vocal estável derivado de UUID, ID da espécie e nome.
- Identidade vocal formada por nome sorteado com sufixo determinístico, pitch, brilho, velocidade, nasalidade, formantes e aspereza.
- Apresentação feminina ou masculina sorteada por entidade; também é possível fixar uma das duas opções na configuração.
- TTS próprio em Java por síntese formântica. É offline e autoral, mas intencionalmente sintético/robótico — não equivale a uma voz neural natural.
- Captura por push-to-talk e transcrição pt-BR local via Vosk. Modelo e bibliotecas nativas são instalados manualmente; nenhum arquivo é baixado automaticamente.

## Ações validadas no servidor

Seguir, aproximar, fugir, olhar, sentar (apenas animal domesticado e seu dono), pular, parar, proteger, pegar item próximo, soltar item da mão principal e criar entidades registradas como `Mob`, inclusive de mods instalados, usando ID como `mymod:forest_guardian`.

O sistema não executa comandos arbitrários de console. O spawn tem cooldown, limite local, validação do registro, espaço e borda do mundo.

## Limites e validação

100.000 parâmetros não representam um LLM grande nem garantem respostas perfeitas. O núcleo classifica intenções e ações; as respostas em português são compostas por regras e modelos locais. O corpus embutido tem 768 exemplos, não milhões de diálogos humanos. O Vosk small pode errar em ruído e nomes próprios. O TTS formântico é robótico. O projeto não é Bedrock/mobile e ainda não foi validado no PojavLauncher.

A compilação completa do Forge não pôde ser executada neste ambiente porque `services.gradle.org` não resolveu por DNS. Os testes de fumaça das classes Java puras passaram; não há JAR final declarado como pronto.

## Build

Requisitos: JDK 17 e Gradle 8.8.

```bash
./gradlew --no-daemon test build
```

Veja também `README.md`, `VOICE_INSTALL.md` e `THIRD_PARTY.md` no pacote-fonte.
