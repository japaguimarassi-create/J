# VoxMobs — Minecraft Forge 1.20.1

Projeto independente de mobs conversacionais com TTS autoral, reconhecimento de voz local e cérebro neural offline de 100.000 parâmetros.

O pacote completo é distribuído no arquivo de origem codificado em `.voxmobs-source/part-*.b64`. No clone, reconstrua os fontes com:

```bash
bash rebuild-source.sh
cd VoxMobs-1.20.1
gradle --no-daemon test build
```

A branch inclui um workflow GitHub Actions que reconstrói a fonte, executa os testes e compila o mod para Forge 1.20.1.

Consulte [VOXMOBS.md](VOXMOBS.md) para arquitetura e limitações.
