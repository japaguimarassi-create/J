# KLOD Evolution

KLOD é uma IA experimental com dois níveis de escala: um núcleo híbrido denso-esparso com estágios lógicos roteados e especialistas independentes para conversa, programação, raciocínio, arquivos e desenvolvimento de jogos.

## Novo alvo: 20.000 x 40.000

- 20.000 estágios lógicos.
- 40.000 unidades ocultas por estágio.
- 800 milhões de posições lógicas de neurônios.
- Uma rede densa convencional exigiria aproximadamente 31.998.400.000.000 pesos.
- Somente os pesos em FP16 ocupariam cerca de 63,9968 TB decimais (aproximadamente 58,2 TiB).

A rede densa convencional completa não foi materializada nem treinada.

## Arquitetura híbrida

O novo modelo está em \`klod/hybrid_model.py\`. Ele combina:

1. **Caminho denso compartilhado:** uma transformação de baixa classificação (low-rank) é aplicada a todos os tokens em cada estágio ativo. Seus pesos são reutilizados entre estágios.
2. **Atenção causal fatorada:** projeções comprimem o estado de 40.000 dimensões para um espaço de atenção menor e o expandem novamente.
3. **Especialistas esparsos:** cada token seleciona apenas os melhores 2 entre 8 especialistas low-rank.
4. **Profundidade esparsa:** um roteador seleciona 8 estágios de um banco lógico de 20.000. O caminho denso e os especialistas são executados nesses estágios selecionados.
5. **Balanceamento de roteamento:** perdas auxiliares incentivam o uso de diferentes estágios e especialistas.

O perfil \`target\` utiliza um estado oculto de 40.000 dimensões e um banco de 20.000 estágios. Ele **não executa 20.000 camadas sequenciais em cada passagem**: seleciona 8 estágios e reutiliza os mesmos pesos densos e especialistas. Essa troca reduz drasticamente armazenamento e computação, mas não é matematicamente equivalente à rede densa não compartilhada.

## Estimativa de recursos

Gere o relatório:

~~~bash
python -m klod.shard_plan --out config/shard-plan.json
~~~

O relatório compara o alvo denso com a estimativa do núcleo híbrido, detalhando embeddings, roteadores, atenção, núcleo denso low-rank e especialistas.

A estimativa do modelo híbrido não inclui ativações, buffers de gradiente, fragmentação de memória ou workspaces da GPU. Ela não deve ser usada como garantia de VRAM necessária.

## Treinar o núcleo híbrido

Instalação:

~~~bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
~~~

Primeiro, validar no perfil pequeno:

~~~bash
python -m klod.train_hybrid --data data/bootstrap.txt --profile micro --steps 100 --seq-len 16 --batch-size 2 --out runs/klod-hybrid-micro.pt
~~~

Treinamento do perfil-alvo:

~~~bash
python -m klod.train_hybrid --data data/train.txt --profile target --device cuda --dtype bf16 --steps 100 --batch-size 1 --seq-len 32 --out runs/klod-hybrid-target.pt
~~~

O perfil-alvo estima 85.309.545 parâmetros, aproximadamente 170,619 MB em pesos FP16 e um piso de 1,364953 GB para parâmetros, gradientes e estados do AdamW em FP32. Esses números não incluem ativações, workspaces, fragmentação ou buffers e não são uma medição de VRAM. O perfil-alvo requer GPU e memória suficientes; o treinador bloqueia execução acidental em CPU, exceto quando \`--allow-cpu-target\` é informado explicitamente. O tamanho do corpus afeta diretamente a qualidade aprendida. \`data/bootstrap.txt\` é somente um arquivo de teste técnico.

O treinamento usa validação reservada e salva o melhor checkpoint observado. O checkpoint registra sua arquitetura, tamanho estimado, hash do corpus e métricas de validação.

## Executar a IA

O runtime reconhece checkpoints compactos antigos e checkpoints \`hybrid_dense_sparse\`:

~~~bash
KLOD_CHECKPOINT=runs/klod-hybrid-target.pt uvicorn klod.server:app --host 127.0.0.1 --port 8000
~~~

O modelo híbrido usa a mesma API de conversa do KLOD. Os especialistas funcionais continuam disponíveis separadamente.

## Especialistas complementares

O manifesto \`config/shards.json\` define módulos independentes:

- conversation
- programming
- reasoning
- files
- game_dev

Treine-os separadamente:

~~~bash
python -m klod.train_shards --manifest config/shards.json --profile small --steps 100 --seq-len 64
~~~

Cada especialista grava seu próprio checkpoint. Eles complementam o núcleo híbrido, mas não são fragmentos literais da matriz densa 20k x 40k.

## Evolução e seleção

O sistema evolutivo compara arquiteturas por validação e tarefas de referência. O próximo estágio de pesquisa é estender essa seleção ao perfil híbrido, avaliando simultaneamente largura, ranks, quantidade de especialistas, top-k e orçamento de estágios ativos.

## Limitações declaradas

- O perfil micro do CI valida o código, não prova que o perfil de 40.000 dimensões foi treinado.
- Nenhum corpus grande foi fornecido neste projeto.
- Nenhum checkpoint-alvo foi treinado ainda.
- O núcleo híbrido compartilha pesos entre estágios selecionados e usa projeções low-rank; ele é uma aproximação arquitetural, não a rede densa completa.
- A compilação automática de APK/JAR e a execução irrestrita de código não fazem parte desta versão.
