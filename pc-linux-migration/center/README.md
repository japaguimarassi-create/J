# AOC Migration Center

Painel web leve com agente local para preparar e auditar um backup criptografado antes da migração do computador AOC para Linux.

## O que faz

- Interface local no navegador, servida pelo próprio agente Python.
- Varredura de uma ou mais pastas escolhidas pelo usuário.
- Cofre em pasta nova e vazia, preferencialmente em HD externo.
- Criptografia de cada arquivo com AES-256-GCM.
- Derivação da chave por scrypt; a senha não é salva.
- Manifesto, nomes de arquivos e caminhos também ficam criptografados.
- Verificação autenticada dos dados e SHA-256 após cada cópia.
- Até três tentativas por arquivo; falhas impedem aprovação.
- Nova varredura da origem ao final para detectar mudanças na lista de arquivos.
- Verificação posterior do cofre com a senha.

## Requisitos

- Windows 10/11 ou Linux.
- Python 3.10+.
- Dependência instalada pelo inicializador: `cryptography`.
- HD externo com espaço livre suficiente. O programa exige uma pasta de destino nova e vazia.

## Iniciar no Windows

1. Baixe esta pasta do repositório ou clone a branch.
2. Abra `center`.
3. Execute `start_windows.bat`.
4. Aguarde a instalação da dependência e abra `http://127.0.0.1:8765` se o navegador não abrir automaticamente.

## Iniciar no Linux

Na pasta `center`, execute:

```bash
bash start_linux.sh
```

Depois abra `http://127.0.0.1:8765`.

## Uso

1. Informe uma pasta por linha. Se deixar vazio, o agente usa a pasta do usuário atual.
2. Acrescente explicitamente pastas de jogos que estejam fora do perfil do usuário.
3. Informe o caminho de uma pasta nova e vazia em outro disco.
4. Analise o computador. Corrija as falhas de leitura antes de continuar.
5. Crie uma senha forte de pelo menos 12 caracteres e guarde-a separadamente.
6. Crie o backup e aguarde o resultado.
7. Faça uma verificação posterior usando o caminho do cofre e a mesma senha.

O cofre contém `vault.json` com parâmetros públicos e salt aleatório, `manifest.enc` com o inventário criptografado e `objects/` com os arquivos criptografados. Sem a senha correta, o conteúdo não pode ser autenticado nem descriptografado. Perder a senha significa perder o acesso ao backup.

## Segurança e limites

- O agente escuta somente em `127.0.0.1`, não em uma interface de rede pública.
- Não há upload, telemetria ou conexão com serviço remoto.
- Não publique o cofre no GitHub.
- A senha não é transmitida para serviços externos nem armazenada em arquivo.
- O AES-GCM autentica os dados; SHA-256 confere que o conteúdo descriptografado corresponde ao conteúdo lido da origem.
- A aprovação só ocorre se todos os arquivos encontrados forem copiados, autenticados e verificados, sem erros, e se a nova varredura mantiver a mesma lista.
- Uma varredura sem erros não prova que o usuário selecionou todas as pastas importantes. Verifique e inclua pastas adicionais, especialmente saves de jogos, gravações, arquivos de e-mail e pastas fora do perfil.
- Arquivos bloqueados, arquivos em uso, links simbólicos, conteúdo de nuvem não baixado localmente, partições não montadas e dados de outros usuários podem não ser incluídos.
- O sistema não copia o Windows, drivers ou programas instalados. Ele preserva arquivos selecionados.
- A verificação de integridade não substitui uma segunda cópia independente.
- O agente não particiona nem instala Linux. A instalação permanece manual e só deve ocorrer depois de verificar o cofre e confirmar o disco correto. Mantenha o computador original intacto até testar a restauração e os dados no Linux.

## Formato do cofre

- Cifra: AES-256-GCM com nonce aleatório de 96 bits por arquivo.
- KDF: scrypt (N=32768, r=8, p=1), salt aleatório de 128 bits.
- Manifesto: também autenticado e criptografado com AES-256-GCM.
- SHA-256: verificação adicional de conteúdo e tamanho.

## Testes

Na raiz do repositório:

```bash
python -m pip install -r pc-linux-migration/center/requirements.txt
python -m unittest discover -s pc-linux-migration/tests -v
python -m py_compile pc-linux-migration/center/agent.py
```
