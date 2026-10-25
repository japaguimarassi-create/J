# Forge AI: três professores, um aluno de 249.984 parâmetros

## Professores escolhidos para este domínio

Os três são papéis complementares para programação, design de animação e revisão crítica; isso não significa que sejam universalmente os melhores modelos para toda tarefa.

1. **Qwen3.6:27b**: programação, tarefas agentivas e elaboração de soluções. [Catálogo Ollama](https://ollama.com/library/qwen3.6).
2. **Gemma4:12b**: modelo de workstation com capacidades de raciocínio, código e multimodalidade. [Catálogo Ollama](https://ollama.com/library/gemma4).
3. **gpt-oss:20b**: raciocínio e tarefas estruturadas com pesos abertos. [Catálogo Ollama](https://ollama.com/library/gpt-oss) e [anúncio OpenAI](https://openai.com/index/introducing-gpt-oss/).

O catálogo indica downloads aproximados de 18–19 GB, 7,7–8 GB e 14 GB, respectivamente. O consumo total de RAM depende da quantização, runtime e contexto. O backend chama os modelos sequencialmente com `keep_alive=0`: isso reduz o pico de memória, mas pode recarregar pesos muitas vezes e deixar o brainstorm lento. A integração não exige API paga; requer Ollama e os modelos locais.

## Protocolo de brainstorm e aprovação

1. Cada professor propõe uma solução independente para o mesmo pedido e contexto FORGE.
2. Cada professor avalia os três candidatos em correção, utilidade e viabilidade, com notas de 1 a 5.
3. O backend calcula a média, apresenta a pontuação e seleciona o candidato mais bem avaliado.
4. O modelo associado ao candidato vencedor sintetiza uma resposta levando em conta as críticas.
5. **Os três professores votam novamente na resposta final.** Cada voto precisa ser JSON válido, conter `approve=true` e nota de pelo menos 4/5.
6. A resposta só vira exemplo de destilação quando os três votos finais aprovam e a opção de salvar foi marcada. Todo brainstorm fica em `data/brainstorm-audit.jsonl`; respostas recusadas não entram em `data/distilled.jsonl`.

Esse processo é avaliação automatizada, não consenso matemático infalível. Os modelos podem cometer erros correlacionados ou se avaliar mal. A auditoria e a validação do parser ajudam a detectar problemas, mas exemplos devem ser revisados antes de treinar. Prompts do sistema pedem justificativas curtas, sem exigir raciocínio privado detalhado.

## Arquitetura do aluno

O aluno é um Transformer causal, inicializado do zero, com embeddings de entrada/saída compartilhados e exatamente 249.984 parâmetros treináveis:

| Componente | Cálculo | Parâmetros |
|---|---:|---:|
| Embedding de tokens | 7.000 × 32 | 224.000 |
| Embedding posicional | 256 × 32 | 8.192 |
| Dois blocos Transformer | 2 × 8.864 | 17.728 |
| LayerNorm final | 32 × 2 | 64 |
| **Total** | | **249.984** |

Cada bloco contém LayerNorm, projeções QKV e de saída, feed-forward 32→64→32 e viés relativo de atenção com 4 cabeças × 80 buckets. A saída compartilha os pesos do embedding de tokens; não há matriz de saída adicional.

O tokenizer Byte-BPE tem vocabulário fixo de 7.000 tokens e aprende merges no corpus de treino. A janela de contexto é de 256 tokens. O tamanho da arquitetura é constante, mas a qualidade depende de quantidade, diversidade e correção dos exemplos.

## Treino e limites

`ai/train.py` inicializa o modelo e o tokenizer, divide exemplos de treino/validação, mede a perda e salva `artifacts/student.pt` com estado e tokenizer. O aluno aprende por previsão do próximo token a partir de exemplos supervisionados. Não há destilação de logits, transferência direta dos pesos dos professores ou cópia de conhecimento completa.

Um dataset pequeno pode gerar sobreajuste e texto livre incoerente. Por isso, a interface usa recuperação de exemplos revisados e reordenação por probabilidade do aluno, com recusa quando a correspondência do pedido é baixa. Uma perda menor é evidência de ajuste ao corpus, não prova de competência geral.

## Pesquisa e privacidade

- A pesquisa externa é iniciada pelo usuário e retorna links para verificação.
- Texto da web e prompts são dados não confiáveis; o backend não executa código vindo das páginas.
- O servidor local fica em `127.0.0.1`; não exponha o serviço à rede sem autenticação.
- O log de brainstorm guarda prompts, contexto de cena, propostas e votos. Não envie dados sensíveis no editor.
