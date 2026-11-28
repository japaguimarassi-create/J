# KLOD Evolution

KLOD Evolution é uma base experimental de IA criada do zero para treinamento local, conversa com checkpoints próprios, memória de conversas, análise e criação de arquivos, validação estática de código e seleção comparativa de modelos.

## Escala solicitada

A especificação-alvo registra 40.000 estágios lógicos e 60.000 unidades virtuais por estágio: 2,4 bilhões de unidades. Uma rede densa com 60.000 unidades entre estágios teria aproximadamente 144 trilhões de pesos (cerca de 288 TB em FP16), sem contar otimizador e ativações. Essa rede não foi materializada nem treinada.

O runtime inicial usa uma rede configurável e pequena, com atenção causal e especialistas roteados. Os números virtuais são metadados de pesquisa, não uma alegação de que a rede gigantesca existe.

## Componentes

- klod/model.py: modelo causal byte-level com roteamento top-1 entre especialistas.
- klod/train.py: treinamento a partir de TXT/JSONL, validação reservada e early stopping.
- klod/runtime.py: carregamento de checkpoint e geração.
- klod/memory.py: histórico persistente por conversa em SQLite.
- klod/tools.py: análise e criação de arquivos dentro de um workspace autorizado.
- klod/code_tools.py: validação estática de Python, JSON, TOML, XML, JavaScript (se Node estiver instalado) e metadados de APK/JAR.
- klod/evolution.py: seleção por gerações, sobreviventes, mutações de arquitetura e benchmark de tarefas.
- klod/benchmarks.py: compara saídas com respostas de referência, inclusive tarefas de programação.
- klod/server.py: API HTTP e interface web.

## Instalação

Requer Python 3.11+.

~~~bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
~~~

No Android/Termux, o treinamento com PyTorch pode não estar disponível em todas as builds. Nesse caso, treine em Linux com PyTorch e use a API nesse ambiente.

## Dados de treinamento

Adicione dados autorizados em data/train.txt ou data/train.jsonl. O JSONL aceita registros com text, content, messages ou pares prompt/completion. Um exemplo está em data/conversations.example.jsonl.

Use dados com permissão de uso, remova credenciais e informações pessoais e mantenha conjuntos de validação separados quando possível.

## Treinamento com validação e parada antecipada

~~~bash
python -m klod.train --data data/train.txt --steps 1000 --batch-size 4 --seq-len 128 --eval-every 50 --patience 8 --out runs/klod.pt
~~~

Para validação em um arquivo independente:

~~~bash
python -m klod.train --data data/train.jsonl --validation-data data/validation.jsonl --steps 5000 --eval-every 100 --patience 10 --out runs/klod.pt
~~~

O checkpoint salvo corresponde ao melhor resultado de validação observado, e não necessariamente ao último passo. data/bootstrap.txt é apenas material mínimo para teste técnico; não é corpus suficiente para um assistente competente.

## Seleção evolutiva com avaliação de tarefas

Cada geração treina candidatos em condições comparáveis. Os melhores são mantidos como sobreviventes; os descendentes recebem mutações em largura, cabeças, profundidade, especialistas, taxa de aprendizado e dropout. Cada candidato também é avaliado em data/benchmark.jsonl.

~~~bash
python -m klod.evolution --data data/train.txt --benchmark-data data/benchmark.jsonl --generations 3 --population 4 --elite-count 1 --steps 80 --seq-len 24
~~~

O fitness combina F1 médio de tokens e correspondência exata do benchmark. Em caso de empate, favorece menor perda em dados reservados, menos parâmetros e menor tempo de treinamento. O conjunto de benchmark precisa ser separado do corpus de treinamento.

Para promover explicitamente o melhor checkpoint:

~~~bash
python -m klod.evolution --data data/train.txt --benchmark-data data/benchmark.jsonl --generations 3 --population 4 --elite-count 1 --steps 80 --seq-len 24 --promote
~~~

A evolução atual procura arquiteturas melhores e treina os pesos de cada candidato do zero; ela ainda não herda nem cruza pesos entre gerações. Benchmarks finitos podem ser sobreajustados, por isso uma aprovação exige também testes novos, revisão humana e testes de segurança.

Se o destino já existir, a promoção é recusada por padrão. Use --overwrite-checkpoint somente quando realmente quiser substituir o arquivo. O controlador pode encerrar apenas os próprios workers filhos que excederem o tempo ou falharem. Não existe desligamento de processos externos.

## Benchmark de conversa e programação

~~~bash
python -m klod.benchmarks --checkpoint runs/klod.pt --data data/benchmark.jsonl
~~~

As métricas incluem correspondência exata, similaridade textual e F1 de tokens. Elas medem semelhança com as respostas de referência, não inteligência geral.

## Executar a interface

Execute a partir da pasta klod-evolution/:

~~~bash
KLOD_CHECKPOINT=runs/klod.pt uvicorn klod.server:app --host 127.0.0.1 --port 8000
~~~

Abra http://127.0.0.1:8000. Sem checkpoint, a API informa que o modelo ainda não foi treinado.

O histórico é gravado localmente em runtime_data/memory.sqlite3, podendo ser apagado pelo botão Limpar conversa ou pelo endpoint DELETE /api/conversations/{id}. O workspace padrão é workspace/. Caminhos que escapem desse diretório são rejeitados.

A validação de código é estática. Python é analisado com AST; JavaScript usa node --check, quando disponível, sem executar o arquivo. APK/JAR são inspecionados somente pelos metadados do ZIP; nenhum conteúdo é extraído ou executado. A primeira versão não executa código recebido nem compila projetos arbitrários.

## Estado

Esta é uma fundação executável, não uma IA de nível comercial. Nenhum grande corpus foi fornecido, nenhum treinamento massivo ocorreu e nenhum benchmark externo foi vencido. A próxima etapa é treinamento em corpus autorizado maior, avaliação por categoria, melhoria de raciocínio e ferramentas de programação e execução de builds em ambiente isolado e limitado.
