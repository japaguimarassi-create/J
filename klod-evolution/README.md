# KLOD Evolution

KLOD Evolution é uma base experimental de IA com treinamento próprio, memória de conversas, ferramentas de arquivos, validação estática e especialistas independentes.

## Meta 40.000 x 60.000

A meta define 40.000 posições lógicas de camada e 60.000 neurônios virtuais por camada, totalizando 2,4 bilhões de posições de neurônios. Em uma arquitetura densa convencional, as matrizes entre camadas teriam aproximadamente 143.996.400.000.000 pesos, ou cerca de 288 TB em FP16 somente para os pesos.

Dividir uma matriz em blocos de 500 x 500 reduz o tamanho de cada arquivo de bloco, mas produz até 576 milhões de blocos de pesos para toda a rede. Esses blocos não podem ser treinados como peças independentes e simplesmente encaixados: o gradiente de cada bloco depende das ativações e dos erros propagados pelo restante da rede.

Por isso, esta versão implementa uma decomposição funcional prática: modelos especialistas independentes, cada qual com corpus, treinamento e checkpoint próprios. Eles compartilham o tokenizer e são selecionados por um roteador. Isso permite aumentar o número de especialistas e treiná-los separadamente, mas não afirma que a rede densa integral já existe.

## Especialistas

O manifesto config/shards.json define:
- conversation: diálogo e linguagem;
- programming: código e depuração;
- reasoning: matemática e raciocínio;
- files: análise e operações de documentos;
- game_dev: lógica e arquitetura de jogos.

Cada módulo salva seu checkpoint em runs/shards/<id>.pt. O runtime carrega os módulos sob demanda e mantém no máximo dois modelos na memória por padrão.

## Perfis de recursos

| Perfil | Camadas físicas | Largura | Cabeças | Especialistas |
|---|---:|---:|---:|---:|
| micro | 1 | 32 | 2 | 2 |
| small | 2 | 64 | 4 | 2 |
| medium | 4 | 128 | 4 | 4 |
| large | 6 | 256 | 8 | 4 |

O perfil informa o tamanho de cada modelo físico especialista, não o tamanho integral da meta lógica. Use medium ou large somente com memória e GPU suficientes.

## Treinar todos os especialistas separadamente

Na pasta klod-evolution:

~~~bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m klod.train_shards --manifest config/shards.json --profile small --steps 100 --seq-len 64
~~~

O treinador processa um especialista por vez, grava um checkpoint independente e produz runs/shards/training-report.json.

Para treinar somente um especialista:

~~~bash
python -m klod.train_shards --manifest config/shards.json --only programming --profile medium --steps 1000 --seq-len 128
~~~

Os especialistas também podem ser treinados em máquinas diferentes: execute o comando com --only para cada ID, use o mesmo manifesto e reúna os checkpoints no mesmo diretório de execução. Cada job independente precisa receber seu próprio ambiente e dados.

Para conferir o custo aproximado das configurações:

~~~bash
python -m klod.shard_plan --out config/shard-plan.json
~~~

## Usar os especialistas na API

Após treinar os módulos:

~~~bash
uvicorn klod.server:app --host 127.0.0.1 --port 8000
~~~

A API seleciona um especialista usando roteamento por palavras-chave. GET /api/shards lista os módulos treinados. O roteador atual é um baseline explicável, não um classificador neural treinado.

## Treinamento e dados

Os arquivos data/shards/*.jsonl são exemplos de inicialização e testes de CI. Eles são minúsculos e não ensinam competência robusta. Substitua ou amplie cada corpus com dados autorizados, representativos e de boa qualidade. Remova segredos e informações pessoais; mantenha validação separada.

A seleção evolutiva anterior continua disponível em klod/evolution.py. Ela pesquisa arquiteturas pequenas e compara validação e tarefas, mas não transforma shards especialistas em uma rede densa de 40.000 x 60.000.

## Limites atuais

- Nenhum modelo treinado nesta base materializa os 2,4 bilhões de neurônios virtuais.
- O CI treina apenas perfis micro por poucas etapas para validar a mecânica.
- A composição de especialistas por roteamento não é equivalente à propagação de gradientes em uma rede densa única.
- A execução arbitrária de código e a compilação de APK/JAR ainda não fazem parte do runtime.
- Atingir a meta densa exigiria uma infraestrutura distribuída de grande porte, armazenamento de centenas de terabytes para pesos e treinamento coordenado em todo o grafo.
