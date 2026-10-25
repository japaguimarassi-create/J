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

## Treino-base confirmado no GitHub Actions

Execução mais recente: [workflow #40202721759](https://github.com/japaguimarassi-create/J/actions/runs/40202721759). O checkpoint treinado e as métricas estão disponíveis como artefato dessa execução.

- Parâmetros treináveis: **249.984**; contagem exata validada.
- Corpus: **54 exemplos**; 46 treino e 8 validação.
- Passos efetivos: **48**, em CPU.
- Perda de validação: **23,38756 antes → 15,93496 depois**, uma redução de aproximadamente 31,9%.
- Exemplos de consenso dos professores incluídos: **0**. Esta é a rodada-base baseada no corpus de exemplo revisado; a destilação de saídas reais começa apenas após o brainstorm local com aprovação final unânime.

A métrica demonstra ajuste ao corpus pequeno, não competência geral nem percepção visual própria. O aluno de 249.984 parâmetros aprende texto e scripts, não pixels. O artefato do checkpoint está em [Artifacts do workflow](https://github.com/japaguimarassi-create/J/actions/runs/40202721759) e expira após 30 dias.

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

## Aprendizado com referências visuais

A aba **Aprender** trata a IA como um aprendiz iniciante: observar → explicar → planejar → testar → revisar. Inclui links de estudo para animação, quadros-chave e storyboard; também permite guardar imagens e vídeos curtos no IndexedDB do próprio navegador, junto com notas escritas.

Ao iniciar um Brainstorm com referências habilitadas, o navegador reduz imagens a JPEGs pequenos e extrai até quatro quadros de imagens/vídeos. Esses quadros e as notas são enviados ao backend local; somente o professor Gemma recebe os pixels via Ollama. Qwen e gpt-oss recebem o texto das notas e analisam as propostas. O vídeo é usado como quadros visuais — o áudio ainda não é analisado.

O modelo-aluno de 249.984 parâmetros **não possui visão nativa**. Ele aprende texto revisado, incluindo descrições e orientações geradas a partir das referências quando os três professores aprovam a resposta. A imagem original não é colocada diretamente nos pesos do aluno. Isso permite ensinar procedimentos e código FORGE sem alegar uma capacidade visual que o modelo pequeno não tem.

O material guardado na biblioteca fica no navegador. As imagens só são transmitidas ao servidor local quando você aciona Brainstorm e mantém a opção de usar referências marcada. O servidor grava notas e quantidade de quadros na auditoria; não armazena cópias dos JPEGs enviados. Links externos podem ter direitos de uso próprios; confira suas licenças antes de redistribuir mídia.

## Limites conhecidos

- FORGE v0.1 não tem loops, variáveis, rigging, partículas, áudio ou renderização final de vídeo.
- O preview 3D da primeira versão depende de Three.js por CDN e WebGL.
- O brainstorm exige os três modelos instalados localmente.
- Consenso entre modelos é uma barreira de qualidade, não uma prova de verdade; confira fontes e código antes de treinar com novos exemplos.

## MotionForge Cut — edição e montagem de vídeo

Abra o [MotionForge Cut](./web/video.html) pelo botão **Editor de vídeo** na interface principal. O editor oferece um monitor de prévia, timeline multifaixa e um fluxo voltado também para telas de celular.

- Importa imagens, vídeos, áudio/música e arquivos ZIP com mídias. A extração ZIP ocorre no navegador, com limite de 150 entradas e 500 MB descompactados por arquivo ZIP.
- Monta faixas simultâneas de vídeo, imagem, música/áudio e texto/legendas; clipes podem ser arrastados para mudar o tempo e redimensionados pelo menu de duração.
- Permite proporções 16:9, 9:16 e 1:1, reprodução, ajuste de posição na timeline, texto sobreposto, exportação WebM em tempo real e salvamento do plano em JSON.
- A Forge AI pode receber o pedido de edição, metadados das mídias, notas/transcrição digitadas e até quatro quadros visuais reduzidos de imagens/vídeos. A análise depende do backend local e dos três modelos Ollama configurados.
- Os arquivos de mídia ficam no navegador durante a sessão. O JSON salvo guarda a estrutura da montagem, não incorpora os arquivos originais; mantenha os arquivos de origem para reabrir o projeto.
- Limites atuais: o áudio é usado na timeline e na exportação, mas não é transcrito automaticamente nem entendido diretamente pelo modelo. Para análise de fala/letra, cole uma transcrição nas notas. A exportação usa WebM e renderiza em tempo real; mantenha a aba aberta até terminar. O suporte a codecs depende do navegador.

Para abrir localmente, execute `python server.py` e acesse `http://127.0.0.1:8000/video.html`. O botão da interface principal também abre o editor.

## APK Android com orquestrador invisível de três IAs

O APK abre o editor dentro de um WebView nativo e coordena a IA pelo backend MotionForge. O fluxo não abre sites externos, não exige copiar respostas e não mostra um navegador no processo de brainstorming.

O botão **Orquestrar com 3 IAs** envia o pedido e o contexto da timeline ao endpoint `/api/brainstorm`. O backend executa o fluxo existente de três professores locais (Qwen 3.6 27B, Gemma 4 12B e GPT-OSS 20B), sintetiza as respostas e devolve um resultado. Um plano de edição só pode ser aplicado depois de ser exibido para revisão.

**Os modelos rodam na máquina/servidor que hospeda Ollama, não dentro do APK nem no Moto G04S.** O trio usa aproximadamente 40 GB de downloads e exige memória e poder computacional consideráveis. O GitHub Actions pode compilar o APK e validar o código, mas não é um serviço permanente de inferência. O GitHub Models foi aposentado em 30 de julho de 2026, então a arquitetura usa Ollama em vez desse endpoint descontinuado.

### Construir o APK

O workflow [MotionForge Android APK](https://github.com/japaguimarassi-create/J/actions/workflows/android-apk.yml) compila o APK de depuração a cada alteração relevante no branch `motionforge-editor`. Quando terminar, abra a execução mais recente e baixe o artefato **MotionForge-Cut-Android-debug**. Os artefatos ficam disponíveis por 30 dias.

Build manual em um ambiente com Android SDK, Java 17 e Gradle 8.9:

```bash
cd android
gradle --no-daemon assembleDebug
```

O APK gerado fica em `android/app/build/outputs/apk/debug/app-debug.apk`. É um APK de depuração; não é uma versão assinada para distribuição na Play Store.

## Orquestrador MotionForge

O arquivo `motionforge_agent.py` é o agente de inicialização: verifica o serviço Ollama, inicia `ollama serve` quando ele estiver ausente no host local, baixa os modelos faltantes (se houver espaço suficiente), valida que os três modelos estejam disponíveis e então inicia `server.py`. Ele coordena o backend; não é um quarto modelo de linguagem.

### Iniciar o agente em um host compatível

Requisitos: Python 3.11+, Ollama instalado, rede e espaço livre para os modelos. Execute no host que vai realizar a inferência:

```bash
python -m pip install -r requirements.txt
python motionforge_agent.py
```

Na primeira execução, o agente pode baixar Qwen 3.6 27B (aproximadamente 18–19 GB), Gemma 4 12B (7,7–8 GB) e GPT-OSS 20B (aproximadamente 14 GB). Isso não é realista no Moto G04S. Os modelos são carregados sequencialmente pelo backend; os pesos não são copiados para o APK.

O agente abre o backend na porta `8000`, vinculado à rede para que o celular possa acessá-lo. Ele gera uma chave aleatória caso `MOTIONFORGE_API_KEY` não esteja definida e a mostra no terminal. Copie essa chave para o campo de autenticação de **Configurar orquestrador** no APK. Para manter a mesma chave após reiniciar o agente, defina `MOTIONFORGE_API_KEY` como variável de ambiente antes de executá-lo. No APK, selecione **Orquestrador MotionForge · 3 IAs locais**, informe a URL base do host acessível pelo celular (por exemplo `http://IP-DO-SERVIDOR:8000` na mesma rede) e a chave; use **Testar conexão** e depois **Salvar**.

**Segurança:** nunca exponha a porta HTTP 8000 diretamente à internet pública. Para acesso remoto, use uma URL HTTPS atrás de um proxy/TLS com firewall. Uma chave compartilhada dentro de um APK pode ser extraída; para distribuir o app publicamente, é necessário autenticação por usuário e limites por conta.

Opções do agente:
- `MOTIONFORGE_AUTO_PULL=0`: não baixar automaticamente modelos ausentes.
- `MOTIONFORGE_TEACHERS=qwen3.6:27b,gemma4:12b,gpt-oss:20b`: configurar exatamente três modelos Ollama.
- `OLLAMA_BASE_URL=http://127.0.0.1:11434`: trocar o endpoint do serviço Ollama.
- `MOTIONFORGE_HOST=127.0.0.1`: restringir o backend ao host local; use o padrão de rede apenas quando precisar conectar o celular e tiver chave definida.

Sem um host Ollama ativo e acessível, o APK ainda monta e exporta vídeo localmente, mas o brainstorming com as três IAs não pode executar. Não há como fazer os modelos de 12B/20B/27B rodarem automaticamente num celular que não dispõe de recursos suficientes.
