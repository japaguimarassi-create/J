# HyperCode AI — treinamento

O objetivo causal é prever o próximo token a partir dos tokens anteriores, como no pré-treinamento de um GPT decoder-only.

## Arquitetura-alvo

- 7 especialistas independentes.
- Cada especialista: 10 blocos causais, largura 256.
- Os sete estados são concatenados: 7 × 256 = 1.792 dimensões.
- Núcleo de fusão: 20 blocos causais com largura 1.792.
- Contagem de unidades do núcleo: 20 × 1.792 = 35.840.
- Contagem total dos especialistas: 7 × 10 × 256 = 17.920.
- O núcleo tem exatamente o dobro da contagem de unidades dos especialistas combinados.

Especialistas: Lua/Python, Web/JavaScript, Java, C/C++, C#, algoritmos/dados e depuração/revisão.

## Tokenização procedural

Há 12 estágios para linguagem natural e 12 para código. O caminho final usa bytes UTF-8 reversíveis, evitando perda de caracteres e mantendo vocabulário fixo de 260 IDs. Os pipelines também extraem estrutura léxica, idioma, comentários, literais, operadores, identificadores e candidatos morfológicos.

A primeira frase identifica o idioma principal. O perfil selecionado é usado junto do vocabulário técnico em inglês, mantido para conceitos e palavras-chave de programação.

## Formato do corpus

Um registro JSONL por linha:

~~~json
{"text":"Em Lua, uma função pode retornar vários valores.","language":"pt","kind":"text","domain":"lua_python"}
{"text":"local function add(a, b) return a + b end","language":"en","kind":"code","domain":"lua"}
{"text":"const sum = (a, b) => a + b;","language":"en","kind":"code","domain":"web"}
~~~

O corpus precisa conter exemplos licenciados para uso, explicações e pares de código/teste de boa qualidade. As linhas acima mostram apenas o formato e não treinam um chatbot útil.

## Teste rápido

Instale PyTorch no ambiente de treinamento e execute:

~~~bash
python train.py --profile smoke --data corpus.jsonl --steps 50 --batch-size 2
~~~

## Treinamento-alvo

O perfil target implementa as dimensões solicitadas, mas requer GPU CUDA com bastante memória e um corpus grande. O script interrompe explicitamente se não houver CUDA, em vez de fingir que um treino reduzido corresponde ao modelo-alvo:

~~~bash
python train.py --profile target --data corpus.jsonl --steps 100000 --batch-size 8 --output artifacts
~~~

O APK desta versão não contém o checkpoint nem executa inferência do modelo treinado. Ele fornece a interface de chat e o modo inicial baseado em regras. Integração de runtime e distribuição dos pesos são etapas separadas.
