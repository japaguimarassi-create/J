# Migração do computador AOC para Linux

Ferramentas para preservar os arquivos de usuário do computador antigo, verificar a cópia e restaurar os dados no Linux.

## Objetivo

O projeto cria uma pasta MIGRACAO_AOC em um HD externo, pendrive com espaço suficiente ou unidade de rede. O conteúdo é organizado em files/ e descrito em MIGRATION_MANIFEST.json. Cada arquivo copiado recebe uma verificação SHA-256.

O programa copia a pasta do usuário por padrão, incluindo arquivos ocultos e dados de aplicativos que estejam dentro desse perfil. Isso pode preservar imagens, gravações, documentos, arquivos locais de e-mail, saves e dados de jogos. Ele não transforma automaticamente programas Windows em programas Linux e não garante que um jogo antigo rode no Linux.

## Requisitos

- Python 3.10 ou mais recente.
- Um disco externo com espaço livre maior que os dados a preservar.
- Para criar USB pelo script Bash: um ambiente Linux, lsblk, findmnt, blockdev, sha256sum e privilégios administrativos.
- Um pendrive separado para o instalador Linux. Ele será apagado durante a criação.

## 1. Descobrir o hardware

No computador antigo:

py -3 migrate.py info

No Linux:

python3 migrate.py info

Guarde o resultado para identificar processador e arquitetura antes de baixar uma ISO.

## 2. Simular o backup

Windows PowerShell:

py -3 migrate.py backup --destination E:\MIGRACAO_AOC --label AOC --dry-run

Linux:

python3 migrate.py backup --destination /media/$USER/HD/MIGRACAO_AOC --label AOC --dry-run

Sem --source, o programa usa a pasta do usuário atual. Para adicionar outra pasta, repita --source:

py -3 migrate.py backup --source "C:\Users\NOME" --source "D:\Jogos" --destination E:\MIGRACAO_AOC --label AOC

Não escolha C:\, C:\Windows, / ou pastas do próprio sistema como origem. Para arquivos em outras unidades, indique apenas as pastas que realmente contêm dados pessoais.

## 3. Fazer e verificar a cópia

Remova --dry-run para executar:

py -3 migrate.py backup --destination E:\MIGRACAO_AOC --label AOC

Depois execute a verificação:

py -3 migrate.py verify --backup E:\MIGRACAO_AOC

O backup pode ser executado novamente. Arquivos idênticos serão reconhecidos; arquivos alterados serão copiados de novo. Erros de leitura são registrados no manifesto e fazem o programa retornar código de erro.

Mantenha o computador original e o backup sem alterações até verificar todos os arquivos.

## 4. Preparar o instalador Linux

O alvo inicial sugerido é Linux Mint 22.3 XFCE, desde que o computador tenha processador x86-64 compatível. Baixe a ISO somente do site oficial:

https://linuxmint.com/download.php

Leia o procedimento oficial de verificação:

https://linuxmint.com/verify.php

Obtenha o SHA-256 da ISO a partir dos arquivos de soma publicados pelo projeto. Não use um hash de terceiros nem pule essa verificação.

Em Linux, grave a ISO em um pendrive vazio usando:

sudo bash usb/make_boot_usb.sh /caminho/linuxmint-22.3-xfce-64bit.iso SHA256_OFICIAL_DE_64_CARACTERES

O script mostra os discos, bloqueia o disco que contém o sistema em execução, bloqueia o disco onde a ISO está guardada, exige que o destino esteja desmontado e exige a confirmação literal ERASE:/dev/.... O pendrive escolhido será apagado por completo.

No Windows, use o Rufus ou balenaEtcher oficial para gravar a ISO. Não tente executar o script Bash no PowerShell.

## 5. Instalar Linux

1. Mantenha o backup externo verificado e não o selecione no instalador.
2. Inicialize pelo pendrive e teste o Linux no modo live.
3. Confira vídeo, teclado, mouse, rede e áudio.
4. Só abra o instalador após confirmar que o backup está íntegro.
5. A escolha de particionamento é manual. A opção de apagar disco elimina os dados do disco selecionado; não a escolha até identificar com certeza o disco interno e confirmar que há duas cópias dos arquivos importantes.
6. Após instalar, conecte o disco de backup e restaure os arquivos.

O script não particiona nem instala Linux no disco interno automaticamente. Essa etapa continua no instalador oficial, com inspeção visual do disco de destino.

## 6. Restaurar os dados no Linux

Padrão (cria ~/Desktop/ARQUIVOS_AOC):

python3 migrate.py restore --backup /media/$USER/HD/MIGRACAO_AOC

Verifique novamente o backup antes da restauração:

python3 migrate.py verify --backup /media/$USER/HD/MIGRACAO_AOC

Por padrão, arquivos existentes com conteúdo diferente não são sobrescritos. O relatório fica em RESTORE_REPORT.json.

## Limitações importantes

- O backup lê o perfil do usuário; ele não copia automaticamente o sistema operacional, drivers, partições de boot ou todos os programas instalados.
- Dados de e-mail podem estar em nuvem ou em arquivos locais. Arquivos locais presentes no perfil são copiados, mas contas e senhas precisam ser configuradas novamente no novo sistema.
- Saves e recursos de jogos são copiados quando estão dentro das pastas selecionadas. Compatibilidade depende do jogo, da arquitetura e de suas dependências.
- Arquivos protegidos, danificados, criptografados ou bloqueados podem gerar falhas. Leia o relatório e repita a cópia com o aplicativo de origem fechado.
- O SHA-256 confirma que os bytes copiados correspondem ao arquivo lido; não garante que o arquivo original não estivesse corrompido.
- Uma cópia em um único HD externo não é redundância. Faça uma segunda cópia das gravações e imagens mais importantes.
