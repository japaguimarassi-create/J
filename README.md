# MotionForge Studio

Editor original, adaptado a celular, para animações 2D/3D, com a linguagem FORGE e uma IA auxiliar local.

**Estado:** MVP em construção. O repositório contém o editor visual, parser/interpolador FORGE, backend local, pesquisa web opcional, colaboração entre três modelos-professores e pipeline de destilação para um único modelo-aluno com exatamente **249.984 parâmetros treináveis**. O modelo-aluno não vem pré-treinado: precisa passar pelo treinamento documentado antes de ser tratado como assistente útil.

## Executar

Requisitos: Python 3.10+; para treinar, PyTorch conforme requirements.txt.

~~~bash
python server.py
~~~

Abra http://127.0.0.1:8000. A edição, o preview 2D, a timeline e a exportação FORGE funcionam sem IA. O preview 3D usa Three.js por CDN e precisa de conexão à internet; o backend local e a IA são executados na máquina que inicia o servidor.

## Três professores → um aluno

Modelos configuráveis no Ollama, selecionados por papéis complementares:

- **Qwen3.8 27B** — programação, tarefas agentivas e pesquisa.
- **Gemma 4 12B** — apoio multimodal; a integração de imagem ainda não é exposta no MVP.
- **gpt-oss 20B** — raciocínio, crítica e avaliação estruturada.

Instale o [Ollama](https://ollama.com/) numa máquina compatível e execute, um por vez:

~~~bash
ollama pull qwen3.8:27b
ollama pull gemma4:12b
ollama pull gpt-oss:20b
~~~

Então reinicie o servidor e use **Brainstorm com 3 modelos**. Cada professor gera uma proposta independente; depois, cada professor avalia as três propostas. O backend agrega os votos, seleciona a proposta melhor pontuada e pede uma síntese final. As chamadas são sequenciais e solicitam o descarregamento do modelo entre chamadas para reduzir a memória retida. Isso não elimina o requisito de RAM para carregar o professor maior. A lista pode ser sobrescrita pela variável MOTIONFORGE_TEACHERS com três nomes separados por vírgulas.

Os pesos publicados pelo catálogo oficial do Ollama são grandes: Qwen3.8 27B ~18 GB, Gemma 4 12B ~7,7–8 GB e gpt-oss 20B ~14 GB. O trio não é adequado ao Moto G04S. Use outro computador local com memória suficiente. Fontes: [Qwen3.8](https://ollama.com/library/qwen3.8), [Gemma 4](https://ollama.com/library/gemma4), [gpt-oss 20B](https://ollama.com/library/gpt-oss%3A20b), [documentação OpenAI gpt-oss](https://developers.openai.com/api/docs/models/gpt-oss-20b).

## Treinar o aluno de 250K

O número de parâmetros não é a soma dos parâmetros dos professores. O aluno tem arquitetura e pesos próprios: um Transformer causal compacto, inicializado do zero e treinado com exemplos revisados pelos professores. A configuração tem **249.984 parâmetros exatos** (contagem verificada pelo código).

Cada brainstorm pode salvar uma amostra em data/distilled.jsonl; o checkbox no painel controla essa gravação. Para treinar, use o botão **Treinar aluno 250K** ou execute:

~~~bash
python -m pip install -r requirements.txt
python -m ai.train --data data/seed.jsonl --data data/distilled.jsonl --out artifacts/student.pt --epochs 8
~~~

data/seed.jsonl oferece exemplos iniciais do editor. Eles são apenas um ponto de partida: um modelo de 250K parâmetros não retém o conhecimento geral dos professores e precisa de muitos exemplos bons, variados e revisados. Uma pequena amostra pode causar sobreajuste. O comando salva os pesos locais em artifacts/student.pt, ignorado pelo Git.

O painel usa o aluno treinado se o checkpoint existir; caso contrário, usa o workflow de três professores. O servidor não afirma que o aluno foi treinado quando o arquivo não existe.

## Exemplo FORGE

~~~forge
scene "Orbit Study" fps=24 width=960 height=540
background color=#0b1020

circle orb x=120 y=270 radius=28 color=#65e8d4
rect ground x=0 y=442 width=960 height=98 color=#17233a
text heading x=42 y=64 value="MOTIONFORGE" size=28 color=#eaf2ff

key orb at=0 x=120 y=270 scale=1
key orb at=24 x=480 y=154 scale=1.35
key orb at=48 x=820 y=270 scale=1

cube core x=0 y=0 z=0 size=1.2 color=#65e8d4
key3 core at=0 rotationY=0 rotationX=0
key3 core at=48 rotationY=6.28 rotationX=1.0
~~~

Veja [FORGE](docs/FORGE-LANGUAGE.md) e [arquitetura de IA](docs/AI-ARCHITECTURE.md).

## Privacidade e segurança

- O servidor local se vincula a 127.0.0.1 por padrão.
- A linguagem FORGE é analisada por uma lista permitida de comandos; o editor não executa o texto como JavaScript.
- A pesquisa é opt-in e envia a consulta ao DuckDuckGo.
- Os prompts e as amostras de treino ficam no computador local.
- Não exponha o servidor numa rede não confiável sem autenticação e controles adicionais.
- Confira as licenças dos modelos, datasets e dependências antes de redistribuir ou usar comercialmente.

## Desenvolvimento

~~~bash
node --test tests/test_forge.mjs
python -m py_compile server.py ai/student.py ai/train.py
~~~

## Licença

Nenhuma licença do projeto foi escolhida ainda. Confirme direitos autorais, termos dos modelos e das dependências antes da redistribuição.
