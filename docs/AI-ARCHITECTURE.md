# Forge AI: três professores, um aluno de 249.984 parâmetros

## Escolha dos professores

A seleção não significa que três modelos sejam universalmente os melhores. Ela usa papéis complementares relevantes ao produto e catálogos publicados:

1. **Qwen3.8 27B** para programação, tarefas agentivas e elaboração de soluções. Catálogo: https://ollama.com/library/qwen3.8
2. **Gemma 4 12B** como professor multimodal mais compacto neste trio. Catálogo: https://ollama.com/library/gemma4
3. **gpt-oss 20B** para raciocínio, revisão e saídas estruturadas. OpenAI: https://developers.openai.com/api/docs/models/gpt-oss-20b

O catálogo do Ollama indica tamanhos de download aproximados de 18 GB, 7,7–8 GB e 14 GB, respectivamente. Os tamanhos dos artefatos não são requisitos completos de RAM: a execução também depende de quantização, runtime e contexto. Os três são carregados em sequência com keep_alive=0; o professor maior ainda precisa caber na máquina. A integração multimodal de Gemma não é ativada pelo MVP, apenas fica disponível como opção para evolução.

## Protocolo de debate

1. Cada professor gera uma proposta independente usando o mesmo pedido e contexto FORGE.
2. Cada professor avalia os três candidatos e atribui notas de 1 a 5 em correção, utilidade e viabilidade.
3. O backend agrega as notas, apresenta o placar e seleciona o candidato mais bem avaliado.
4. O professor associado ao candidato vencedor produz uma síntese final baseada nas propostas e críticas.
5. Se o usuário habilitar a opção, a síntese final é salva como exemplo JSONL local para destilação.

Isso é um debate de propostas e avaliação, não consenso matemático infalível. Os resultados podem sofrer de erros correlacionados, pontuação inconsistente ou vieses. Revise exemplos antes de usá-los como treino. O sistema pede avaliações breves, não raciocínio privado detalhado.

## Arquitetura do aluno

O aluno é um Transformer causal compacto, inicializado do zero e com embeddings de entrada/saída compartilhados:

| Componente | Cálculo | Parâmetros |
|---|---:|---:|
| Embedding de tokens | 7000 × 32 | 224.000 |
| Embedding posicional | 256 × 32 | 8.192 |
| Dois blocos Transformer | 2 × 8.864 | 17.728 |
| LayerNorm final | 32 × 2 | 64 |
| **Total treinável** | | **249.984** |

Cada bloco contém LayerNorm, projeções QKV e de saída, feed-forward 32→64→32 e viés relativo de atenção com 4 cabeças × 80 buckets. Os pesos do cabeçalho de saída são empatados com o embedding de tokens, então não há matriz de saída adicional.

O tokenizer é byte-level BPE com vocabulário fixo de 7.000 tokens. O modelo recebe até 256 tokens por janela. Esse tamanho fixo mantém a arquitetura exatamente em 249.984 parâmetros; entradas raras podem ter tokens não vistos durante o treino.

## O que “treinado” significa aqui

Os pesos do aluno são próprios; não são uma soma nem média dos pesos dos professores. A destilação é supervisionada por texto: prompts e respostas consensuais são gravados em data/distilled.jsonl; ai/train.py aprende a prever a sequência a partir dos exemplos. O pipeline não implementa destilação de logits nem ajuste fino dos pesos dos professores.

Um dataset pequeno não transfere a capacidade geral de modelos de dezenas de bilhões de parâmetros. O aluno pode sobreajustar e produzir respostas fracas, repetitivas ou incorretas; comece por tarefas estreitas do editor, construa muitos exemplos verificados e mantenha um conjunto de avaliação separado antes de usar o aluno como padrão. A loss de treino não é medida suficiente de qualidade.

## Privacidade e fronteiras

- O runtime do aluno é local.
- O brainstorming requer Ollama local e os três modelos instalados.
- A busca é iniciada explicitamente pelo usuário e envia a consulta ao DuckDuckGo.
- O conteúdo retornado pela web é tratado como fonte não confiável.
- O backend se vincula a 127.0.0.1; não o exponha numa rede sem autenticação.
- Não guarde segredos pessoais, tokens ou dados sensíveis no dataset.
