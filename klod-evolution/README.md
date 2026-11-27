# KLOD Evolution

KLOD Evolution é uma base experimental de IA criada do zero para treinamento local, conversa com checkpoints próprios, análise e criação de arquivos e avaliação isolada de candidatos.

## Escala solicitada

A especificação-alvo registra 40.000 estágios lógicos e 60.000 unidades virtuais por estágio: 2,4 bilhões de unidades. Uma rede densa com 60.000 unidades entre estágios teria aproximadamente 144 trilhões de pesos (cerca de 288 TB em FP16), sem contar otimizador e ativações. Essa rede não foi materializada nem treinada.

O runtime inicial usa uma rede configurável e pequena, com atenção causal e especialistas roteados. Os números virtuais são metadados de pesquisa, não uma alegação de que a rede gigantesca existe.

## Componentes

- klod/model.py: modelo causal byte-level com roteamento top-1 entre especialistas.
- klod/train.py: treinamento a partir de arquivos TXT ou JSONL locais.
- klod/runtime.py: carregamento de checkpoint e geração.
- klod/tools.py: análise e criação de arquivos dentro de um workspace autorizado.
- klod/evolution.py: avaliação de candidatos em processos filhos isolados e encerramento do worker que falhar ou exceder o tempo.
- klod/server.py: API HTTP e interface web.

## Instalação

Requer Python 3.10+.

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

## Avaliação evolutiva

~~~bash
python -m klod.evolution --rounds 4
~~~

O avaliador cria workers separados, testa inicialização, formato, valores finitos e inferência, e encerra somente o worker que falhar ou travar. A seleção não comprova qualidade de conversa ou programação: isso exige benchmarks com respostas esperadas, revisão humana e dados representativos.

A promoção é manual e opcional:

~~~bash
python -m klod.evolution --rounds 4 --promote
~~~

Não há objetivos ilimitados, autoalteração irrestrita, acesso automático ao sistema operacional ou desligamento de processos externos. O controlador só pode terminar os próprios workers de avaliação. Candidatos aprovados tecnicamente não são considerados perfeitos.

## Executar a interface

~~~bash
uvicorn klod.server:app --host 127.0.0.1 --port 8000
~~~

Abra http://127.0.0.1:8000. Defina KLOD_CHECKPOINT=runs/klod.pt para ativar geração. Sem checkpoint, a API informa que o modelo ainda não está treinado.

O workspace padrão é workspace/. A API impede caminhos que escapem desse diretório. A primeira versão não executa código arbitrário; análise e criação de arquivos não equivalem a um sandbox seguro.

## Estado

Esta é uma fundação executável, não uma IA de nível comercial. Nenhum grande corpus foi fornecido, nenhum treinamento massivo ocorreu e nenhum benchmark externo foi vencido. Próximos ciclos: corpus licenciado, tokenizer dedicado, benchmarks de programação, avaliação humana, memória de conversas e execução de builds em contêineres.
