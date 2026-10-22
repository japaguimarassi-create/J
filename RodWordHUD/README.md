# Rod Word HUD

Aplicativo Android nativo para organizar palpites para o desafio da palavra secreta do canal RodPrimata.

## Recursos

- Mini modelo local de classificação com uma matriz de 50.000 pesos treináveis, treinada no aparelho com um pequeno conjunto inicial de exemplos em português.
- Entrada manual de título, transcrição curta ou pistas visíveis; geração e ordenação de cinco palpites.
- Atalho para abrir um link do vídeo no YouTube ou pesquisar contexto na web.
- HUD flutuante móvel, com baixa frequência de atualização e sem animações contínuas.
- Ao tocar em “INSERIR PALPITE”, tenta preencher somente o campo de texto focado. Se o campo não for acessível, copia o palpite para a área de transferência.
- Não lê a senha nem tenta importar a sessão da conta. O app abre YouTube ou o navegador instalado, onde sua sessão permanece gerenciada pelo próprio serviço.
- Não envia comentários e não repete envios automaticamente. A publicação é sempre manual, depois de revisar o texto.

## Permissões

Para usar o HUD, conceda “Sobrepor a outros apps” e habilite o serviço de acessibilidade do Rod Word HUD nas configurações do Android. O serviço só executa a inserção depois de um toque explícito no HUD. Desative a acessibilidade ou remova a sobreposição nas configurações do Android para interromper o recurso.

## Contexto do vídeo

A pesquisa pública inicial não identificou com segurança o vídeo específico recém-publicado nem a palavra secreta. Por isso, o app não inventa título, transcrição ou resposta: cole o link exato e acrescente as pistas ou a transcrição disponível para orientar os palpites. A pontuação exibida é relativa ao conjunto de candidatos, não uma probabilidade calibrada de acerto.

Canal: https://www.youtube.com/@rodprimata/videos

## Compilar no GitHub Actions

O workflow `.github/workflows/rod-word-hud.yml` compila o projeto nesta pasta e publica o artefato `rod-word-hud-debug-apk`. Em uma execução bem-sucedida, baixe `app-debug.apk` na seção Artifacts da execução do workflow.

Para compilar localmente, com Java 17, Android SDK 35 e Gradle 8.11.1:

```bash
gradle --no-daemon -p RodWordHUD :app:assembleDebug
```

O APK de depuração não é uma versão assinada para publicação na Google Play.
