# KLOD Evolution

KLOD Evolution é uma base experimental de IA criada do zero para treinamento local, conversa com checkpoints próprios, memória de conversas, análise e criação de arquivos, validação estática de código e seleção comparativa de modelos.

## Escala solicitada

A especificação-alvo registra 40.000 estágios lógicos e 60.000 unidades virtuais por estágio: 2,4 bilhões de unidades. Uma rede densa com 60.000 unidades entre estágios teria aproximadamente 144 trilhões de pesos (cerca de 288 TB em FP16), sem contar otimizador e ativações. Essa rede não foi materializada nem treinada.

O runtime inicial usa uma rede configurável e pequena, com atenção causal e especialistas roteados. Os números virtuais são metadados de pesquisa, não uma alegação de que a rede gigantesca existe.

## Componentes

- klod/model.py: modelo causal byte-level com roteamento top-1 entre especialistas.
- klod/train.py: treinamento a partir de arquivos TXT ou JSONL locais.
- klod/runtime.py: carregamento de checkpoint e geração.
- klod/memory.py: histórico persistente por conversa em SQLite.
- klod/tools.py: análise e criação de arquivos dentro de um workspace autorizado.
- klod/code_tools.py: validação estática de Python, JSON, TOML, XML, JavaScript (se Node estiver instalado) e metadados de APK/JAR.
- klod/evolution.py: treina candidatos isolados e seleciona pelo menor cross-entropy em uma parte reservada do corpus.
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

## Treinamento

Adicione dados autorizados em data/train.txt ou data/train.jsonl. Para JSONL, cada linha pode conter o campo text.

~~~bash
python -m klod.train --data data/train.txt --steps 1000 --batch-size 4 --seq-len 128 --out runs/klod.pt
~~~

data/bootstrap.txt é apenas material mínimo para teste técnico; não é corpus suficiente para um assistente competente.

## Seleção evolutiva treinável

A seleção agora treina cada candidato no mesmo corpus, reserva uma parte final para validação e compara a cross-entropy nessa parte não vista durante o treinamento.

~~~bash
python -m klod.evolution --data data/train.txt --rounds 4 --steps 80 --seq-len 24
~~~

Para promover explicitamente o checkpoint do melhor candidato:

~~~bash
python -m klod.evolution --data data/train.txt --rounds 4 --steps 80 --seq-len 24 --promote
~~~

Se o destino já existir, a promoção é recusada por padrão. Use --overwrite-checkpoint somente quando realmente quiser substituir o arquivo. O controlador pode encerrar apenas os próprios workers filhos que excederem o tempo ou falharem. Não existe desligamento de processos externos.

A cross-entropy mede previsão de próximos bytes, não qualidade geral de respostas, lógica ou programação. Modelos aprovados ainda precisam passar por benchmarks de tarefa, revisão humana e testes de segurança.

## Benchmark de conversa e programação

O arquivo data/benchmark.jsonl contém tarefas de referência pequenas. Avalie um checkpoint:

~~~bash
python -m klod.benchmarks --checkpoint runs/klod.pt --data data/benchmark.jsonl
~~~

As métricas incluem correspondência exata, similaridade textual e F1 de tokens. Elas medem semelhança com as respostas de referência, não inteligência geral.

## Executar a interface

~~~bash
KLOD_CHECKPOINT=runs/klod.pt uvicorn klod.server:app --host 127.0.0.1 --port 8000
~~~

Execute a partir de klod-evolution/ com o pacote instalado ou com PYTHONPATH definido. Abra http://127.0.0.1:8000. Sem checkpoint, a API informa que o modelo ainda não foi treinado.

O histórico é gravado localmente em runtime_data/memory.sqlite3, podendo ser apagado pelo endpoint DELETE /api/conversations/{id}. O workspace padrão é workspace/. Caminhos que escapem desse diretório são rejeitados.

A validação de código é estática. Python é analisado com AST; JavaScript usa node --check, quando disponível, sem executar o arquivo. APK/JAR são inspecionados somente pelos metadados do ZIP; nenhum conteúdo é extraído ou executado. A primeira versão não executa código recebido nem compila projetos arbitrários.

## Estado

Esta é uma fundação executável, não uma IA de nível comercial. Nenhum grande corpus foi fornecido, nenhum treinamento massivo ocorreu e nenhum benchmark externo foi vencido. A próxima etapa é treinar com um corpus autorizado maior, medir resultados por categoria, expandir ferramentas de programação e implementar execução de builds em ambiente isolado e limitado.
