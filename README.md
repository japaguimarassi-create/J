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

## APK Android com navegador interno e IA local

O projeto Android fica em `android/`. O aplicativo abre o MotionForge Cut dentro de um WebView nativo, sem mandar o usuário para o Chrome, e oferece seletor de arquivos Android para importar mídia e ZIP. A interface de edição e os controles de IA ficam no próprio app.

O botão **Configurar IA local** permite escolher:
- **Ollama direto**: chama `/api/chat` no endereço definido e usa o modelo indicado, com quadros visuais quando o modelo aceitar imagens.
- **Backend MotionForge**: chama `/api/brainstorm` no servidor Python e usa o fluxo de três professores descrito acima.

Para Ollama no mesmo telefone, o endereço padrão é `http://127.0.0.1:11434`. Se o serviço estiver em outro computador/dispositivo da mesma rede, informe o IP local dele e a porta `11434`. Para o backend de três professores, use a porta do servidor MotionForge (normalmente `8000`). Os dispositivos precisam alcançar o endereço configurado; o teste no botão de configuração verifica `/api/tags` ou `/api/status`.

**Os pesos dos modelos não estão embutidos no APK.** O aplicativo contém o editor e a ponte Android para conversar com o serviço local configurado. Para usar Gemma 4, Qwen e gpt-oss, os pesos desses modelos precisam estar instalados em um serviço Ollama compatível e acessível; o fluxo de três professores precisa também do backend Python. Isso evita afirmar que modelos de vários gigabytes cabem no APK ou rodam automaticamente em um celular com memória limitada.

### Construir o APK

O workflow [MotionForge Android APK](https://github.com/japaguimarassi-create/J/actions/workflows/android-apk.yml) compila o APK de depuração a cada alteração relevante no branch `motionforge-editor`. Quando terminar, abra a execução mais recente e baixe o artefato **MotionForge-Cut-Android-debug**. Os artefatos ficam disponíveis por 30 dias.

Build manual em um ambiente com Android SDK, Java 17 e Gradle 8.9:

```bash
cd android
gradle --no-daemon assembleDebug
```

O APK gerado fica em `android/app/build/outputs/apk/debug/app-debug.apk`. É um APK de depuração; não é uma versão assinada para distribuição na Play Store.

## Backend remoto com GitHub Models

O projeto inclui `cloud_backend.py`, uma API leve para o APK. Ela não baixa nem carrega pesos grandes: encaminha os pedidos ao GitHub Models usando um token guardado no servidor. O modo padrão usa `openai/gpt-4o`; opcionalmente, `MOTIONFORGE_GITHUB_MODELS` aceita até três IDs de modelos separados por vírgula. Com mais de um modelo, o backend pede propostas independentes e depois sintetiza o resultado, consumindo mais chamadas e limites de inferência.

### Implantar a API remota

1. Abra o [Render](https://render.com/) e conecte a conta GitHub.
2. Escolha **New → Blueprint**, selecione este repositório e a branch `motionforge-editor`. O arquivo `render.yaml` configura o serviço `motionforge-cloud-backend`.
3. Nas variáveis de ambiente do serviço, defina `GITHUB_MODELS_TOKEN` com um token GitHub autorizado para inferência em GitHub Models (permissão `models:read`) e `MOTIONFORGE_API_KEY` com uma chave longa exclusiva para proteger o backend. Não coloque o token de inferência no APK ou no repositório.
4. Aguarde a implantação e copie a URL HTTPS atribuída ao serviço pelo Render.
5. No APK, abra **Configurar IA local**, selecione **Backend MotionForge · local/remoto**, cole a URL HTTPS como endereço base, informe a mesma `MOTIONFORGE_API_KEY` no campo de chave e toque em **Testar conexão**. Depois, salve.

O endpoint `/health` verifica a disponibilidade pública do serviço; `/api/status` e `/api/brainstorm` exigem a chave de acesso. A chave enviada pelo APK protege o endpoint contra acessos casuais, mas uma chave incluída em um APK pode ser extraída. Não redistribua uma versão privada do app com uma chave compartilhada; para distribuição pública, use autenticação por usuário e limites de uso por conta.

### Limites

- O backend remoto usa inferência hospedada do GitHub Models; não executa fisicamente o trio Qwen/Gemma/GPT-OSS local do projeto.
- Os limites gratuitos de GitHub Models variam por modelo e podem causar respostas HTTP 429. Usar mais de um modelo consome mais chamadas.
- O plano gratuito do Render pode suspender a instância após 15 minutos sem tráfego; a primeira solicitação posterior pode demorar cerca de um minuto para despertar. É adequado para testes, não para disponibilidade contínua.
- O APK e o editor continuam funcionando para montagem e exportação mesmo quando a API está indisponível.
