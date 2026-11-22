# AOC Mint Edition

Camada de personalização do Linux Mint XFCE que adiciona o AOC Migration Center como uma janela de aplicativo no menu do sistema.

## Base selecionada

Linux Mint 22.3 XFCE (Zena), edição leve oficial do Linux Mint. A versão estável 22.3 é LTS, com suporte até abril de 2029. Use a imagem oficial e verifique sua autenticidade antes de gravar o pendrive.

- Download oficial: https://www.linuxmint.com/download.php
- Requisitos e notas: https://www.linuxmint.com/rel_zena.php
- Verificação da ISO: https://linuxmint.com/verify.php

AOC Mint Edition, neste estágio, é um perfil de desktop e uma aplicação de recuperação instalados sobre o Linux Mint. Não substitui o kernel, o instalador, o gerenciador de pacotes nem o projeto Linux Mint, e ainda não é uma distribuição ISO independente.

## Instalação

1. Instale o Linux Mint XFCE e faça as atualizações iniciais.
2. Baixe/extraia o repositório para a pasta pessoal.
3. Abra um terminal na raiz do projeto e execute:

```bash
bash pc-linux-migration/os-layer/install_aoc_mint.sh
```

Para abrir automaticamente a janela quando entrar no desktop:

```bash
bash pc-linux-migration/os-layer/install_aoc_mint.sh --autostart
```

4. Abra Menu > Administração > AOC Migration Center.

O instalador copia o agente para `~/.local/share/aoc-migration-center`, cria um ambiente virtual isolado, instala a dependência de criptografia e cria um atalho de aplicativo. A janela usa Chromium/Chrome em modo app quando disponível; Firefox ou o navegador padrão são alternativas.

Para remover apenas os atalhos:

```bash
bash pc-linux-migration/os-layer/uninstall_aoc_mint.sh
```

A remoção mantém a pasta do aplicativo e os cofres por segurança.

## Migração de ida e volta

- No Windows antigo, execute `center/start_windows.bat`, selecione o perfil do usuário e pastas adicionais e crie um cofre AES-256-GCM num disco externo.
- No Linux Mint, use a janela AOC Migration Center e a ação **Restaurar para este sistema**. A aplicação verifica primeiro o cofre inteiro; depois restaura os arquivos para uma pasta nova e separada.
- No Linux Mint, use **Fazer backup deste sistema** para guardar o perfil Linux e as pastas adicionais num novo cofre.
- Em outro computador Windows ou Linux com o agente, use a ação de restauração para recuperar o conteúdo do cofre.

A restauração não sobrescreve diretórios existentes e trabalha numa pasta temporária; só publica o resultado quando todos os arquivos forem autenticados e conferidos.

## O que pode ser restaurado

Documentos, imagens, vídeos, gravações, arquivos locais de e-mail, saves e outros arquivos presentes nas pastas selecionadas. Dados de jogos instalados em pastas externas precisam ser incluídos manualmente.

## O que não é uma imagem integral do sistema

Este fluxo não replica o Windows ou Linux por setores, não reinstala aplicativos, drivers, bootloader ou registro do Windows. Configurações do Windows dentro de AppData são preservadas como arquivos, mas muitos programas Windows não conseguem usar essas configurações no Linux. Ao retornar para Windows, os arquivos são extraídos para uma pasta de recuperação; não são mesclados automaticamente em perfis de usuário ativos.

Uma volta integral do sistema operacional exigiria uma imagem de disco independente e procedimento de recuperação do boot, com identificação manual dos discos. Isso ainda não está automatizado neste projeto. Mantenha o disco original e uma segunda cópia do backup até validar tudo.

## Testes

Na raiz do repositório:

```bash
python -m pip install -r pc-linux-migration/center/requirements.txt
python -m unittest discover -s pc-linux-migration/tests -v
python -m py_compile pc-linux-migration/center/agent.py
```
