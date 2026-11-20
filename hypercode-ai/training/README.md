# HyperCode AI — treinamento e avaliação

## Arquitetura universal e pensamento mútuo

As sete redes não são especialistas por linguagem ou domínio. Cada rede recebe o mesmo fluxo de tokens, vê os mesmos dados e aprende a mesma tarefa geral de previsão do próximo token.

Em cada uma das dez etapas da arquitetura-alvo:
1. As sete redes executam sua própria camada causal de linguagem.
2. Os sete estados são reunidos em uma sequência de sete agentes.
3. Uma camada de comunicação faz atenção entre os sete estados para cada posição do texto. Cada rede recebe informação das outras seis.
4. Os estados atualizados seguem para a próxima etapa, repetindo a comunicação dez vezes.

Depois da décima etapa, as sete representações de 256 dimensões são concatenadas em uma representação coletiva de 1.792 dimensões. O núcleo de vinte camadas processa essa representação e produz os logits da resposta final. Não existe seleção de um único especialista nem divisão fixa de linguagens.

## Dimensões e parâmetros

| Parte | Configuração-alvo |
|---|---:|
| Redes universais | 7 |
| Camadas por rede | 10 |
| Largura por rede | 256 |
| Comunicação mútua | 10 etapas conectando os 7 estados |
| Largura coletiva | 7 × 256 = 1.792 |
| Núcleo | 20 camadas × 1.792 |
| Unidades dos sete especialistas | 17.920 |
| Unidades do núcleo | 35.840 |
| Parâmetros treináveis | calculados automaticamente com o vocabulário BPE treinado |

A contagem de parâmetros não é a mesma coisa que a contagem de unidades/células solicitada.

## Como o aprendizado funciona

O objetivo principal é causal next-token prediction: o modelo recebe os tokens anteriores e tenta prever o próximo token. A perda da saída coletiva é combinada com uma perda auxiliar de cada uma das sete saídas individuais. Todas as redes aprendem com os mesmos exemplos e a perda coletiva treina a síntese final.

O tokenizer procedural de 260 IDs permanece disponível para testes rápidos. O perfil-alvo usa BPE byte-level treinado no corpus, com 32.768 tokens solicitados e PAD/BOS/EOS/UNK reservados. A camada byte-level mantém cobertura para caracteres e código raros; as fusões subword reduzem o comprimento médio das sequências. O contexto-alvo sobe para 2.048 tokens. O tamanho real do vocabulário é lido do tokenizer.json e gravado nos checkpoints.

## Dados de treinamento

O arquivo seed_corpus.jsonl.gz contém exemplos originais criados para testar o pipeline. São poucos exemplos e não constituem um corpus suficiente para treinar um assistente útil.

O importador foi ajustado ao esquema atual do **The Stack v1.3**: lê `content`, identifica a linguagem por `lang` (ou `language` em shards antigos), e procura metadados SPDX em `licenses` ou campos equivalentes de licença do repositório. Preserva repositório, caminho, hash/commit e licenças aceitas. Ele filtra uma lista conservadora de licenças permissivas, remove duplicatas exatas e padrões de possíveis segredos.

A página oficial atual do The Stack v1.3 lista 358 linguagens de programação, com comentários/docstrings em diversas línguas naturais. O dataset é **gated**: você precisa abrir a página, ler e aceitar pessoalmente os termos antes de baixar os arquivos. As solicitações de remoção de dados são atualizadas nas versões utilizáveis; use a versão atual e preserve as licenças e a proveniência de cada fonte. O script não baixa dados nem aceita termos em nome do usuário.

**Não use este importador diretamente no The Stack v2.** A versão v2 exige acordo com Software Heritage e INRIA para download em massa e possui princípios adicionais para treinamento; este importador não implementa seu esquema.

Referências oficiais:
- https://huggingface.co/datasets/bigcode/the-stack
- https://huggingface.co/datasets/bigcode/the-stack-v2

O dataset contém duplicatas aproximadas; o script remove conteúdo idêntico e o treinamento separa por repositório para reduzir vazamento entre treino e validação. Uma avaliação séria ainda deve deduplicar por hash e por similaridade, e manter um conjunto de benchmark separado.

~~~bash
python -m pip install pyarrow tokenizers
python prepare_stack.py --input /data/the-stack-v1 --output corpus/stack_filtered.jsonl --max-per-language 15000
python train_bpe_tokenizer.py --data corpus/stack_filtered.jsonl --output artifacts/tokenizer.json --vocab-size 32768
~~~

## Treino de prova e treino-alvo

Teste do pipeline em CPU, com dimensões deliberadamente reduzidas:

~~~bash
python train.py --profile smoke --data seed_corpus.jsonl.gz --steps 80 --batch-size 4 --output artifacts/smoke
~~~

Treinamento da arquitetura-alvo. Requer CUDA e GPU com memória suficiente; o script recusa executar o perfil-alvo em CPU:

~~~bash
python train.py --profile target --data corpus/stack_filtered.jsonl --tokenizer-json artifacts/tokenizer.json --steps 100000 --batch-size 1 --gradient-accumulation-steps 8 --gradient-checkpointing --output artifacts/target
~~~

O tamanho do corpus, a quantidade de tokens, a validação e o orçamento de GPU determinam se o treinamento é suficiente. Um número de passos, isoladamente, não prova qualidade.

## Comparação e geração de código

evaluate.py calcula NLL da resposta de referência para a saída coletiva e para cada uma das sete cabeças individuais. Com --generate, pede a cada rede que gere uma resposta e também pede ao núcleo que gere a resposta coletiva. Registra os oito candidatos e faz verificações sintáticas estáticas.

~~~bash
python evaluate.py --checkpoint artifacts/target/hyperinter_checkpoint.pt --tokenizer-json artifacts/tokenizer.json --tasks coding_benchmark.jsonl --output benchmark-results --generate --max-new-tokens 128
~~~

sandbox_tests.py pode executar candidatos Python somente dentro de um contêiner Docker sem rede, com filesystem somente leitura, limites de memória/processos/CPU e timeout. Ele nunca executa código gerado diretamente no host:

~~~bash
python sandbox_tests.py --candidates benchmark-results/candidates.jsonl --tasks coding_benchmark.jsonl --output benchmark-results/sandbox.jsonl
~~~

As verificações estáticas não provam correção semântica. A avaliação dinâmica precisa de testes específicos por tarefa e runtime por linguagem.

## Fase 2 — ajuste supervisionado de instruções (SFT)

Depois do pré-treinamento causal, `finetune.py` carrega o checkpoint e treina pares `prompt`/`completion`. Os tokens da pergunta do usuário são mascarados com `-100`; somente os tokens da conclusão do assistente contribuem para a perda. A perda principal continua no núcleo coletivo, com perdas auxiliares nas sete redes.

~~~bash
python finetune.py --checkpoint artifacts/pretrain/hyperinter_checkpoint.pt --data corpus/instructions.jsonl.gz --tokenizer-json artifacts/tokenizer.json --steps 10000 --batch-size 1 --gradient-accumulation-steps 8 --gradient-checkpointing --output artifacts/sft
~~~

O corpus precisa ser de pares de instrução/resposta. O arquivo `seed_instructions.jsonl.gz` é composto de exemplos originais pequenos para verificar o pipeline; não é um dataset de escala suficiente para treinar um assistente geral.

## Treinamento progressivo por componentes

O orquestrador \`staged_train.py\` divide o treino sem transformar as redes em especialistas por linguagem. Todas as sete redes usam o mesmo corpus universal, a mesma tarefa causal e o mesmo contexto.

A sequência obrigatória é:

1. \`expert --expert-index 0\` até \`expert --expert-index 6\`: cada rede é treinada individualmente, sem comunicação entre redes nessa fase. A primeira rede aprende os embeddings compartilhados de tokens/posições; depois eles ficam congelados enquanto as seis redes restantes aprendem. Isso impede que cada fase desloque a base representacional das redes anteriores.
2. \`core\`: congela as sete redes e treina somente o núcleo para combinar as sete representações independentes.
3. \`communication\`: congela as redes e o núcleo, desbloqueia as dez camadas de comunicação e treina a troca de informações usando a perda da resposta coletiva.
4. \`joint\`: desbloqueia toda a arquitetura e faz o ajuste conjunto, com perda do núcleo e perdas auxiliares das sete saídas.

O programa impede avançar fora dessa ordem, salva um checkpoint separado por etapa, registra a perda de validação antes/depois e salva checkpoints intermediários com estado do otimizador para retomar uma etapa interrompida. A validação usa os mesmos lotes determinísticos antes e depois. Por padrão, uma regressão de validação reprova a etapa, mantém o checkpoint como pendente e bloqueia a próxima fase. Para retomar, carregue o checkpoint pendente e aumente o total de `--steps`. A opção `--allow-validation-regression` existe apenas para smoke tests curtos e CI.

### Comandos de execução

Inicie pela rede 1. O índice é zero-based:

~~~bash
python staged_train.py --profile target --stage expert --expert-index 0 --data corpus/stack_filtered.jsonl --tokenizer-json artifacts/tokenizer.json --steps 10000 --batch-size 1 --gradient-accumulation-steps 8 --gradient-checkpointing --output artifacts/staged
~~~

Treine a rede seguinte carregando o checkpoint anterior. Repita os índices de 1 a 6:

~~~bash
python staged_train.py --profile target --stage expert --expert-index 1 --data corpus/stack_filtered.jsonl --tokenizer-json artifacts/tokenizer.json --checkpoint artifacts/staged/expert_01/hyperinter_expert_01.pt --steps 10000 --batch-size 1 --gradient-accumulation-steps 8 --gradient-checkpointing --output artifacts/staged
~~~

Depois de concluir a rede 7:

~~~bash
python staged_train.py --profile target --stage core --data corpus/stack_filtered.jsonl --tokenizer-json artifacts/tokenizer.json --checkpoint artifacts/staged/expert_07/hyperinter_expert_07.pt --steps 20000 --batch-size 1 --gradient-accumulation-steps 8 --gradient-checkpointing --output artifacts/staged

python staged_train.py --profile target --stage communication --data corpus/stack_filtered.jsonl --tokenizer-json artifacts/tokenizer.json --checkpoint artifacts/staged/core/hyperinter_core.pt --steps 10000 --batch-size 1 --gradient-accumulation-steps 8 --gradient-checkpointing --output artifacts/staged

python staged_train.py --profile target --stage joint --data corpus/stack_filtered.jsonl --tokenizer-json artifacts/tokenizer.json --checkpoint artifacts/staged/communication/hyperinter_communication.pt --steps 20000 --batch-size 1 --gradient-accumulation-steps 8 --gradient-checkpointing --output artifacts/staged
~~~

O ajuste supervisionado de instruções (\`finetune.py\`) vem depois da integração conjunta e usa o checkpoint \`artifacts/staged/joint/hyperinter_joint.pt\`.

### Teste geral e configuração

Depois do estágio joint, gere as sete respostas individuais e a resposta coletiva, compare NLL, verifique sintaxe e revise a qualidade:

~~~bash
python evaluate.py --checkpoint artifacts/staged/joint/hyperinter_joint.pt --tokenizer-json artifacts/tokenizer.json --tasks coding_benchmark.jsonl --output artifacts/final-benchmark --generate --max-new-tokens 128
~~~

A resposta coletiva só deve ser promovida quando superar ou igualar a melhor saída individual no conjunto de validação e atingir critérios de correção funcional. NLL menor, sozinho, não prova que o código funciona. Rode testes dinâmicos em sandbox isolada por linguagem antes de aceitar o modelo.

A calibração final deve medir temperatura/top-k, limite de geração, contexto, taxa de repetição e correção dos códigos em um conjunto de validação separado. Não ajuste esses parâmetros usando o conjunto de teste final.

### Receita de treinamento ampliada

- BPE byte-level treinado exclusivamente no corpus de treino e armazenado como tokenizer.json; o SHA-256 do arquivo acompanha todos os checkpoints.
- Embeddings e posições compartilhados são atualizados somente na fase da rede 1 e congelados nas fases 2–7.
- As sete projeções individuais reutilizam os mesmos pesos de vocabulário (weight tying), com bias independente por rede.
- AdamW usa betas 0.9/0.95, weight decay seletivo, fused optimizer quando suportado, BF16 em CUDA, clipping global e acumulação de gradientes.
- O scheduler WSD aplica warmup, taxa estável e decaimento linear nos 10% finais. Checkpoints salvam estado do otimizador e RNG Python/Torch/CUDA para retomada mais fiel.
- Contexto-alvo de 2.048 tokens; subir para 4.096/8.192 deve ocorrer numa fase de mid-training separada, com validação de memória e estabilidade.

Essas escolhas são inspiradas em receitas públicas de treinamento de modelos de linguagem. A receita não substitui ablações no corpus e arquitetura reais, nem transforma os dados de demonstração em treinamento de escala.

## Evidência de teste realizada

smoke_evidence.json registra um treino de prova executado em CPU. Ele confirma atualizações reais de pesos e melhora da perda de validação na configuração reduzida. A avaliação também compara as sete saídas individuais com a saída coletiva; os candidatos gerados nessa prova não passaram na verificação sintática. Isso não é treinamento nem validação do modelo-alvo. Consulte `smoke_evidence.json` para os números medidos.

## Testes estruturais

Os testes verificam dimensões-alvo, peso de vocabulário compartilhado, BPE e offsets SFT, scheduler WSD, embeddings congelados após a primeira rede, entrada comum, comunicação mútua, gradientes nos ramos e núcleo, máscara causal, oito saídas, campos/licenças do The Stack v1.3 e separação por repositório.

~~~bash
python -m pytest tests -q
~~~
