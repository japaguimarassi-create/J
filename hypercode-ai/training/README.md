# HyperCode AI — treinamento e avaliação

## Arquitetura universal e pensamento mútuo

As sete redes não são especialistas por linguagem ou domínio. Cada rede recebe o mesmo fluxo de tokens, vê os mesmos dados e aprende a mesma tarefa geral de previsão do próximo token.

Em cada uma das dez etapas da arquitetura-alvo:
1. As sete redes executam sua própria camada causal de linguagem.
2. Os sete estados são reunidos em uma sequência de sete agentes.
3. Uma camada de comunicação faz atenção entre os sete estados para cada posição do texto. Cada rede recebe informação das outras seis.
4. Os estados atualizados seguem para a próxima etapa, repetindo a comunicação dez vezes.

Depois da décima etapa, as sete representações de 256 dimensões são concatenadas em uma representação coletiva de 1.792 dimensões. O núcleo de vinte camadas processa essa representação e produz os logits da resposta final. Não existe seleção de um único especialista nem divisão fixa de linguagens.

## Dimensões e contagem de parâmetros

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

Com as dimensões FFN, atenção, embeddings e cabeças auxiliares, a implementação-alvo tem **456.728.352 parâmetros treináveis**. Isso é diferente da contagem de unidades/células acima.

## Como o aprendizado funciona

O objetivo principal é causal next-token prediction: o modelo recebe os tokens anteriores e tenta prever o próximo token. A perda da saída coletiva é combinada com uma perda auxiliar de cada uma das sete saídas individuais. Todas as redes aprendem com os mesmos exemplos e a perda coletiva treina a síntese final.

O tokenizer mantém doze estágios para linguagem natural e doze para código. A língua natural é identificada pela primeira frase, e o dicionário de programação em inglês permanece ativo para palavras-chave, APIs e termos técnicos. A representação final usa bytes UTF-8 reversíveis com vocabulário fixo de 260 IDs; isso é simples e robusto, mas menos eficiente que BPE.

## Dados de treinamento

O arquivo seed_corpus.jsonl.gz contém exemplos originais criados para testar o pipeline. São poucos exemplos e não constituem um corpus suficiente para treinar um assistente útil.

Para pré-treinamento de verdade, prepare um subconjunto local do BigCode The Stack. O script prepare_stack.py filtra arquivos Parquet por linguagem e por lista conservadora de licenças SPDX e mantém repositório, caminho, commit e licença em cada registro. Cada arquivo permanece sujeito à licença original; mantenha avisos e proveniência e leia os termos atuais antes de baixar ou usar o conjunto. O script não baixa dados nem aceita termos pelo usuário.

~~~bash
python -m pip install pyarrow
python prepare_stack.py --input /data/the-stack --output corpus/stack_filtered.jsonl --max-per-language 15000
~~~

## Treino de prova e treino-alvo

Teste do pipeline em CPU, com dimensões deliberadamente reduzidas:

~~~bash
python train.py --profile smoke --data seed_corpus.jsonl.gz --steps 80 --batch-size 4 --output artifacts/smoke
~~~

Treinamento da arquitetura-alvo. Requer CUDA e GPU com memória suficiente; o script recusa executar o perfil-alvo em CPU:

~~~bash
python train.py --profile target --data corpus/stack_filtered.jsonl --steps 100000 --batch-size 1 --gradient-checkpointing --output artifacts/target
~~~

O tamanho do corpus, a quantidade de tokens, a validação e o orçamento de GPU determinam se o treinamento é suficiente. Um número de passos, isoladamente, não prova qualidade.

## Comparação e geração de código

evaluate.py calcula NLL da resposta de referência para a saída coletiva e para cada uma das sete cabeças individuais. Com --generate, pede a cada rede que gere uma resposta e também pede ao núcleo que gere a resposta coletiva. Registra os oito candidatos e faz verificações sintáticas estáticas.

~~~bash
python evaluate.py --checkpoint artifacts/target/hyperinter_checkpoint.pt --tasks coding_benchmark.jsonl --output benchmark-results --generate --max-new-tokens 128
~~~

sandbox_tests.py pode executar candidatos Python somente dentro de um contêiner Docker sem rede, com filesystem somente leitura, limites de memória/processos/CPU e timeout. Ele nunca executa código gerado diretamente no host:

~~~bash
python sandbox_tests.py --candidates benchmark-results/candidates.jsonl --tasks coding_benchmark.jsonl --output benchmark-results/sandbox.jsonl
~~~

As verificações estáticas não provam correção semântica. A avaliação dinâmica precisa de testes específicos por tarefa e runtime por linguagem.

## Evidência de teste realizada

smoke_evidence.json registra um treino de prova executado em CPU. Ele confirma atualizações reais de pesos e melhora da perda de validação na configuração reduzida. A avaliação também compara as sete saídas individuais com a saída coletiva; os candidatos gerados nessa prova não passaram na verificação sintática. Isso não é treinamento nem validação do modelo-alvo de 456,7 milhões de parâmetros.

## Testes estruturais

Os testes verificam dimensões-alvo, passagem do mesmo contexto pelos sete ramos, comunicação entre redes, gradientes em todos os ramos e no núcleo, máscara causal e pipelines de doze estágios.

~~~bash
python -m pytest tests -q
~~~
