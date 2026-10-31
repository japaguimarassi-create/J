# VoxMobs — Minecraft Forge 1.20.1

Projeto independente de mod para Minecraft Java 1.20.1 / Forge 47.4.28 / Java 17.

O código-fonte completo está no pacote de origem entregue junto desta conversa. Este branch registra o projeto e seu plano técnico; ainda não contém o pacote binário do mod nem uma release.

## Recursos implementados no protótipo

- Conversa textual com mobs mirando para a entidade e enviando `!mob mensagem`.
- Push-to-talk por tecla V: captura local de PCM 44,1 kHz, reamostra para 16 kHz e transcreve com Vosk pt-BR.
- O áudio bruto não é enviado ao servidor nem ao provedor de linguagem; somente o texto reconhecido é enviado ao servidor do mundo.
- TTS autoral em Java por síntese formântica, com perfis de pitch, velocidade, brilho e nasalidade por tipo de mob. É experimental/robótico, não é voz neural natural.
- Cérebro offline determinístico com diálogo básico e interpretação de ações em português.
- Endpoint LLM OpenAI-compatible opcional, desligado por padrão; endpoint remoto exige consentimento explícito por jogador.
- Memória persistente por par mob/jogador; comandos para consentimento e exclusão de memória.
- Ações de follow, approach, flee, look, sit (somente pet domesticado e pelo dono), jump, stop e protect, validadas no servidor.
- Rede Forge com direção de pacotes limitada e controle de distância/frequência.

## Voz offline

O primeiro uso baixa o modelo pequeno `vosk-model-small-pt-0.3` (~31 MB) e uma biblioteca nativa do Vosk para Linux x64, Linux ARM64 ou Windows x64. Depois da instalação, a transcrição é local. O modelo pequeno tem precisão limitada em ruído, sotaques e nomes próprios.

## Limites conhecidos

- O modo offline não é um LLM treinado; é um motor determinístico de intenções e respostas.
- O TTS formântico é original, mas sua naturalidade e inteligibilidade são limitadas.
- O recurso de voz foi projetado para Minecraft Java desktop. Não é addon Bedrock/mobile e não foi validado no Android/PojavLauncher.
- A compilação Gradle completa ainda precisa ser confirmada pelo GitHub Actions. Os testes de fumaça locais das classes puras de interpretação e TTS passaram; não foi possível baixar Gradle no ambiente atual devido à indisponibilidade de DNS.

## Build

Requisitos: JDK 17 e Gradle 8.8.

```bash
gradle --no-daemon test build
```

Consulte o README dentro do pacote de origem para instalação, configuração e arquitetura detalhadas.
