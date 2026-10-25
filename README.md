# MotionForge Studio

Editor experimental de animação 2D/3D, linguagem própria FORGE e auxiliar de IA local. Projeto criado e versionado no GitHub, com interface responsiva, parser determinístico, treinamento reproduzível e testes.

## O que existe nesta primeira versão

- Editor web responsivo com exemplos 2D/3D, timeline, pré-visualização e exportação do script .forge.
- FORGE v0.1: declara cena, objetos, movimentos, rotações, escala e easing linear/suave.
- Modelo-aluno Transformer próprio com 247.890 parâmetros treináveis, aproximadamente 250 mil.
- Assistente que recupera exemplos verificados e usa os pesos treinados para reordená-los. Não apresenta geração livre incoerente como resposta confiável.
- Brainstorm local em três etapas: Qwen, Gemma e gpt-oss propõem, criticam e depois aprovam/reprovam a síntese; apenas aprovação unânime entra no corpus de destilação.
- Pesquisa web acionada pelo usuário, com URLs para conferência.
- GitHub Actions para executar testes e treinar o aluno.

## Limite técnico importante

Os 247.890 parâmetros são pesos novos do aluno, não a soma ou uma cópia dos modelos-professores. O corpus inicial tem exemplos-curtos de domínio; a perda de validação menor mostra adaptação a esse corpus, mas não prova competência geral. O teste local de referência (41 exemplos, 160 passos em CPU) reduziu a perda de validação de 28,1880 para 2,7475; geração livre ainda não é confiável. O brainstorm dos três modelos está implementado, mas os modelos-professores precisam ser instalados e executados localmente para produzir exemplos reais de consenso.

## Executar e treinar

Instale Python 3.11+, Node.js e as dependências:

    python -m venv .venv
    . .venv/bin/activate
    pip install -r ai/requirements.txt
    python ai/train.py --steps 160 --batch-size 4
    python ai/chat_server.py

Abra app/index.html por um servidor estático. O Three.js é carregado por CDN para a visualização 3D; o editor 2D e o parser são executados no navegador. O servidor local fica restrito a 127.0.0.1:8765.

## Três modelos-professores locais

Com Ollama instalado, obtenha modelos compatíveis com o seu hardware:

    ollama pull qwen3:8b
    ollama pull gemma4:e4b
    ollama pull gpt-oss:20b
    python ai/teacher_brainstorm.py "Crie uma animação 3D de uma esfera saltando"

Os três modelos são consultados sequencialmente para reduzir o pico de memória. Esses modelos têm vários bilhões de parâmetros e não são viáveis simultaneamente em um celular comum. Depois de revisar as fontes e o exemplo aprovado:

    python ai/train.py --extra-data data/teacher_generated.jsonl --steps 800 --batch-size 4

O arquivo de auditoria de brainstorming guarda propostas, críticas, notas e decisões.

## Pesquisa e revisão

A pesquisa externa só é feita quando o usuário aciona essa função. Os resultados são pistas para leitura, não fatos automaticamente verificados. Não execute código baixado da web. Execute todos os testes antes de publicar:

    python -m unittest discover -s tests -v
    node --test tests/forge.test.mjs

Veja docs/architecture.md, docs/forge-language.md e docs/research-notes.md para a arquitetura, sintaxe e fontes de pesquisa.
