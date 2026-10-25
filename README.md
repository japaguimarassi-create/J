# MotionForge Studio

MotionForge é um editor web responsivo para animação 2D/3D, com linguagem própria FORGE, timeline de quadros-chave e uma IA auxiliar local. O código canônico fica em `web/`; o backend e a IA ficam em `server.py` e `ai/`.

## Recursos implementados

- Editor visual responsivo com Canvas 2D, viewport 3D, câmera controlável, timeline, seleção de objetos, inspetor de propriedades, edição de script e exportação para JSON e `.forge`.
- Linguagem declarativa FORGE v0.1 com `scene`, `background`, `circle`, `rect`, `text`, `cube`, `key` e `key3`. O parser valida comandos permitidos, nomes e keyframes; não executa JavaScript.
- Um único modelo-aluno inicializado do zero com **249.984 parâmetros treináveis**, Transformer causal de 2 camadas, vocabulário byte-BPE de 7.000 tokens e contexto de 256 tokens.
- Assistente do aluno baseado em exemplos revisados e reordenação neural. Quando a correspondência é baixa, o aluno se abstém; texto livre gerado pelo protótipo não é tratado como confiável.
- Brainstorm de três professores locais — Qwen3.6 27B, Gemma 4 12B e gpt-oss 20B. Cada um propõe, avalia os três candidatos e vota de novo na resposta final. Uma amostra só pode entrar no corpus de treino quando **os três aprovam a síntese final com nota mínima 4/5**.
- Pesquisa web acionada pelo usuário, com títulos, trechos e URLs para conferir na fonte original.
- GitHub Actions para testes, contagem de parâmetros, treino reproduzível e publicação do checkpoint como artefato.

## Estado do treinamento

O aluno tem pesos próprios; os parâmetros dos professores não são somados nem copiados. A destilação é supervisionada por texto, não por logits dos professores. O corpus semente em `data/seed.jsonl` tem exemplos curtos escritos para a gramática FORGE. Exemplos produzidos no brainstorm são auditados em `data/brainstorm-audit.jsonl` e só entram em `data/distilled.jsonl` após a aprovação unânime e se a opção de salvar estiver marcada.

A queda da perda de treino/validação não prova competência geral. Um aluno de 249.984 parâmetros não equivale a modelos de dezenas de bilhões; por isso, a IA usa recuperação de exemplos e recusa assuntos fora da cobertura conhecida.

## Executar localmente

Requisitos: Python 3.11+, PyTorch compatível com o sistema e Node.js 22 para rodar os testes. No ambiente Python:

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
node --test tests/test_forge.mjs
python -m ai.student
```

Inicie o servidor local:

```bash
python server.py
```

Abra [http://127.0.0.1:8000](http://127.0.0.1:8000). O servidor se limita a `127.0.0.1`; não o exponha à rede sem autenticação. A visualização 3D carrega Three.js por CDN. A pesquisa usa a internet apenas quando chamada explicitamente.

## Brainstorm com os três modelos locais

Instale o [Ollama](https://ollama.com/) e baixe os pesos apropriados para a máquina:

```bash
ollama pull qwen3.6:27b
ollama pull gemma4:12b
ollama pull gpt-oss:20b
ollama list
python server.py
```

No editor, abra Forge AI, escreva a tarefa e clique em **Brainstorm**. Para guardar a resposta para destilação, marque **Guardar consenso para treinar o aluno**. Se qualquer um dos três revisores finais reprovar, a resposta é mostrada para leitura, mas não é adicionada ao corpus.

Os tamanhos de download publicados são aproximadamente 18–19 GB para Qwen3.6:27b, 7,7–8 GB para Gemma4:12b e 14 GB para gpt-oss:20b. Os três são chamados em sequência para limitar o pico de memória, mas ainda exigem muito armazenamento e memória; não é realista executar esse trio em um celular comum. Referências: [Qwen3.6 no Ollama](https://ollama.com/library/qwen3.6), [Gemma 4 no Ollama](https://ollama.com/library/gemma4), [gpt-oss no Ollama](https://ollama.com/library/gpt-oss).

## Treinar o modelo-aluno de 249.984 parâmetros

```bash
python -m ai.train --data data/seed.jsonl --data data/distilled.jsonl --out artifacts/student.pt --epochs 8 --batch-size 2
```

O segundo arquivo pode ainda não existir; nesse caso, o treino usa o corpus semente. O processo salva `artifacts/student.pt` com estado do modelo e tokenizer, além de `artifacts/student.metrics.json`. Você também pode clicar em **Treinar aluno** no editor; essa ação chama o mesmo treinamento local.

O workflow **Train MotionForge student** executa testes e treinamento no GitHub Actions, depois publica o checkpoint como artefato por 30 dias. Baixe-o em [Actions](https://github.com/japaguimarassi-create/J/actions) → execução do workflow → **Artifacts**.

## GitHub Pages

O deploy estático é opcional. Para ativá-lo, abra **Settings → Pages** e escolha **GitHub Actions** como fonte de build. Em **Settings → Secrets and variables → Actions → Variables**, crie `MOTIONFORGE_PAGES_ENABLED=true`, e execute o workflow **Deploy MotionForge Studio**. A página estática oferece a interface e o preview, mas as rotas `/api/...` precisam do backend local; GitHub Pages não hospeda `server.py` nem os modelos do Ollama.

## Limites conhecidos

- FORGE v0.1 não tem loops, variáveis, rigging, partículas, áudio ou renderização final de vídeo.
- O preview 3D da primeira versão depende de Three.js por CDN e WebGL.
- O brainstorm exige os três modelos instalados localmente.
- Consenso entre modelos é uma barreira de qualidade, não uma prova de verdade; confira fontes e código antes de treinar com novos exemplos.
