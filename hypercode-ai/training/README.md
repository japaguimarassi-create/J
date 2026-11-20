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
| Parâmetros treináveis estimados pelo código | 456.728.352 |

A contagem de parâmetros não é a mesma coisa que a contagem de unidades/células solicitada.

## Como o aprendizado funciona

O objetivo principal é causal next-token prediction: o modelo recebe os tokens anteriores e tenta prever o próximo token. A perda da saída coletiva é combinada com uma perda auxiliar de cada uma das sete saídas individuais. Todas as redes aprendem com os mesmos exemplos e a perda coletiva treina a síntese final.

O tokenizer mantém doze estágios para linguagem natural e doze para código. A língua natural é identificada pela primeira frase, e o dicionário de programação em inglês permanece ativo para palavras-chave, APIs e termos técnicos. A representação final usa bytes UTF-8 reversíveis com vocabulário fixo de 260 IDs; isso é simples e robusto, mas menos eficiente que BPE.

## Dados de treinamento

O arquivo seed_corpus.jsonl.gz contém exemplos originais criados para testar o pipeline. São poucos exemplos e não constituem um corpus suficiente para treinar um assistente útil.

O script prepare_stack.py foi escrito para um subconjunto local em Parquet com colunas content, license e language, compatível com o formato do The Stack v1. Ele filtra um conjunto conservador de licenças SPDX e mantém repositório, caminho, commit e licença como proveniência. O The Stack é um conjunto com controle de acesso; é necessário ler e aceitar seus termos na página oficial antes de usar os arquivos. Cada trecho continua sujeito à licença original e pode exigir atribuição.

**Não use este importador diretamente no The Stack v2.** A versão v2 contém identificadores do Software Heritage e o conteúdo dos arquivos fica em armazenamento separado; download em massa exige acordo com Software Heritage e INRIA. É necessário aceitar pessoalmente os termos e obter acesso autorizado. O script não baixa dados nem aceita termos em nome do usuário.

Fonte: https://huggingface.co/datasets/bigcode/the-stack
Informações da versão v2: https://huggingface.co/datasets/bigcode/the-stack-v2

~~~bash
python -m pip install pyarrow
python prepare_stack.py --input /data/the-stack-v1 --output corpus/stack_filtered.jsonl --max-per-language 15000
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

## Fase 2 — ajuste supervisionado de instruções (SFT)

Depois do pré-treinamento causal, `finetune.py` carrega o checkpoint e treina pares `prompt`/`completion`. Os tokens da pergunta do usuário são mascarados com `-100`; somente os tokens da conclusão do assistente contribuem para a perda. A perda principal continua no núcleo coletivo, com perdas auxiliares nas sete redes.

~~~bash
python finetune.py --checkpoint artifacts/pretrain/hyperinter_checkpoint.pt --data corpus/instructions.jsonl.gz --steps 10000 --batch-size 1 --gradient-checkpointing --output artifacts/sft
~~~

O corpus precisa ser de pares de instrução/resposta. O arquivo `seed_instructions.jsonl.gz` é composto de exemplos originais pequenos para verificar o pipeline; não é um dataset de escala suficiente para treinar um assistente geral.

## Evidência de teste realizada

smoke_evidence.json registra um treino de prova executado em CPU. Ele confirma atualizações reais de pesos e melhora da perda de validação na configuração reduzida. A avaliação também compara as sete saídas individuais com a saída coletiva; os candidatos gerados nessa prova não passaram na verificação sintática. Isso não é treinamento nem validação do modelo-alvo. Consulte `smoke_evidence.json` para os números medidos.

## Testes estruturais

Os oito testes verificam dimensões-alvo, passagem do mesmo contexto pelos sete ramos, comunicação entre redes, gradientes em todos os ramos e no núcleo, máscara causal, geração de sete saídas individuais mais a resposta coletiva, pipelines de doze estágios e máscara SFT que impede a pergunta de contribuir para a perda.

~~~bash
python -m pytest tests -q
~~~
