# Instalação de voz offline (sem APIs e sem downloads automáticos)

O VoxMobs não consulta serviços de IA, endpoints HTTP, nuvem nem APIs externas durante o jogo. O reconhecimento de voz usa Vosk local e só funciona depois de instalar manualmente o modelo e a biblioteca nativa correspondente ao sistema.

Crie as pastas abaixo dentro da pasta `config` do perfil do Minecraft:

```text
config/voxmobs/
  models/pt-br-small/
    am/final.mdl
    conf/...
    graph/...
    ivector/...
  native/linux-x64/libvosk.so
```

Para Windows x64, use `native/windows-x64/` e coloque `libvosk.dll` e as DLLs dependentes do pacote Vosk. Para Linux ARM64, use `native/linux-arm64/libvosk.so`.

Use o modelo oficial `vosk-model-small-pt-0.3` (aproximadamente 31 MB) e a biblioteca nativa Vosk 0.3.45 para a plataforma correta. Extraia o conteúdo do modelo dentro de `models/pt-br-small`; não deixe uma pasta extra `vosk-model-small-pt-0.3` dentro dela. Mantenha juntos os arquivos dependentes da biblioteca nativa.

A origem e as licenças são listadas em `THIRD_PARTY.md`. O VoxMobs não baixa esses arquivos sozinho; isso mantém o mod sem chamadas de API/rede para instalar voz. A síntese TTS formântica é própria e funciona sem modelos ou rede.

## Limites

O modelo small de reconhecimento tem menor precisão em ruído, sotaques e nomes de entidades de mods. A síntese formântica é original e offline, mas ainda soa sintética; perfis masculinos/femininos são timbres selecionados, não vozes humanas gravadas.
