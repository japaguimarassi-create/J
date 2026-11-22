# AOC Migration Center

Painel web leve com agente local para criar, verificar e restaurar cofres criptografados antes e depois da migração do computador AOC.

## O que faz

- Interface local no navegador ou janela de aplicativo no Linux Mint.
- Varredura de uma ou mais pastas selecionadas; por padrão usa a pasta pessoal do usuário.
- Cofre numa pasta nova e vazia em outro disco.
- Criptografia de cada arquivo com AES-256-GCM.
- Derivação de chave por scrypt; a senha não é salva.
- Manifesto, nomes das origens e caminhos também ficam criptografados.
- Verificação autenticada e SHA-256 antes de aprovar o backup.
- Até três tentativas por arquivo e nova varredura para detectar arquivos que mudaram.
- Restauração em pasta nova: primeiro verifica todos os objetos; depois extrai para uma área temporária e só publica o resultado quando tudo foi restaurado.
- Não sobrescreve pastas existentes.

## Requisitos

- Windows 10/11 ou Linux Mint XFCE / outra distribuição Linux.
- Python 3.10+.
- Dependência instalada num ambiente virtual isolado: `cryptography`.
- HD externo com espaço livre suficiente.

## Iniciar no Windows

1. Baixe/extrai o repositório.
2. Abra `pc-linux-migration/center`.
3. Execute `start_windows.bat`.
4. O agente abre o navegador em `http://127.0.0.1:8765`.

## Iniciar no Linux

Na pasta `center`, execute:

```bash
bash start_linux.sh
```

Depois abra `http://127.0.0.1:8765`.

Para a janela integrada ao menu do Mint, use o instalador em `../os-layer/README.md`.

## Fazer backup de qualquer sistema

1. Abra a Ação **Fazer backup deste sistema**.
2. Deixe as origens vazias para incluir a pasta pessoal ou indique uma pasta por linha.
3. Acrescente manualmente as pastas de jogos e arquivos que estejam fora do perfil.
4. Escolha uma nova pasta de destino num disco externo diferente.
5. Analise as pastas e corrija as falhas de leitura.
6. Crie uma senha forte de pelo menos 12 caracteres e guarde-a fora do HD.
7. Crie o backup e aguarde a auditoria completa.
8. Execute depois a verificação do cofre.

## Restaurar para outro sistema

1. Abra a Ação **Restaurar para este sistema**.
2. Informe a pasta do cofre e a senha.
3. Escolha uma pasta de destino que ainda não exista.
4. Pressione **Restaurar arquivos**. O agente autentica todos os objetos antes de extrair qualquer arquivo.
5. Confira `AOC_RESTORE_REPORT.json` na pasta restaurada.

A restauração organiza os dados por pasta de origem. Ela não injeta AppData do Windows nas configurações Linux, não reinstala programas e não substitui automaticamente arquivos do perfil atual. Ao restaurar em Windows, os dados também são extraídos numa pasta separada para permitir uma comparação antes da mesclagem.

## Como o cofre é armazenado

- `vault.json`: parâmetros públicos e salt aleatório.
- `manifest.enc`: inventário criptografado e autenticado.
- `objects/`: arquivos individuais criptografados, com identificadores sem nomes de arquivo.

Sem a senha correta, os dados não podem ser autenticados nem descriptografados. Perder a senha significa perder o acesso. A cifra também não esconde o tamanho aproximado de cada arquivo, que pode ser inferido pelo tamanho dos objetos criptografados.

## Segurança e limites

- O agente escuta somente em `127.0.0.1`; não expõe o serviço para a rede.
- Não há upload, telemetria ou serviço remoto.
- Não publique o cofre no GitHub.
- O destino precisa estar numa unidade diferente da origem; o programa compara o identificador de volume.
- Links simbólicos, arquivos bloqueados, dados em nuvem ainda não baixados, volumes não montados e dados de outros usuários geram erros ou exigem inclusão manual.
- Uma varredura sem erros não prova que todas as pastas importantes foram selecionadas. Inclua explicitamente pastas fora do perfil.
- A aprovação significa que todos os arquivos encontrados nas pastas selecionadas passaram pelas verificações. Não é prova matemática de que nenhum dado fora dessas pastas exista.
- O projeto guarda arquivos, não uma imagem integral do Windows/Linux: sistema operacional, drivers, programas instalados, partições e boot não são restaurados.
- Mantenha o sistema original e outra cópia dos arquivos insubstituíveis até testar tudo.

## Formato do cofre

- AES-256-GCM, nonce aleatório de 96 bits por objeto.
- scrypt (N=32768, r=8, p=1), salt aleatório de 128 bits.
- Manifesto também autenticado e criptografado com AES-256-GCM.
- SHA-256 para validar conteúdo e tamanho.

## Testes

Na raiz do repositório:

```bash
python -m pip install -r pc-linux-migration/center/requirements.txt
python -m unittest discover -s pc-linux-migration/tests -v
python -m py_compile pc-linux-migration/center/agent.py
```
