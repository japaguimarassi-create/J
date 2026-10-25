# Arquitetura do MotionForge

## Componentes

1. A interface web guarda o script de origem, apresenta preview 2D/3D e exporta arquivos de texto .forge.
2. O parser FORGE é determinístico, não executa código arbitrário e valida cenas, objetos, nomes e intervalos de tempo.
3. O aluno é um Transformer causal de bytes UTF-8 com 247.890 parâmetros. Treina em corpus pequeno e tem contexto de 256 tokens.
4. O assistente calcula correspondência lexical dos exemplos e usa verossimilhança do modelo treinado para reordenar candidatos; com cobertura baixa, abstém-se.
5. O protocolo de professores Ollama faz propostas, críticas cruzadas, síntese e aprovação final unânime. O registro completo fica em JSONL.
6. Pesquisa web é uma função explícita; links devolvidos devem ser abertos e verificados. Nenhuma instrução da página é executada automaticamente.

## Treino e avaliação

O treino combina prompts e respostas curadas em um fluxo de tokens, mede perda de validação e salva checkpoint mais métricas. A queda na perda só indica que o aluno se ajustou ao corpus; não demonstra que a geração livre seja boa. Por isso a primeira versão não usa o aluno para compor livremente resposta ao usuário.

## Decisões e riscos

- Modelos-professores são locais no Ollama; precisam ser baixados e executados pelo usuário.
- Os três modelos são chamados sequencialmente para controlar pico de memória. Isso reduz RAM simultânea, mas não o custo total de descarregar/carregar.
- Checkpoints, dados gerados por professores e ambientes virtuais ficam fora do Git; Actions pode treinar um artefato novo.
- A preview 3D usa Three.js por CDN, enquanto o preview 2D funciona localmente.
- Ainda não existe renderizador de vídeo/exportação final; a exportação desta fase é o script .forge.
