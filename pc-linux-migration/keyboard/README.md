# Reconfiguração de teclado — AOC Linux

Este módulo usa **keyd** para criar um mapa artificial de teclas no nível do sistema. O remapeamento funciona independentemente do aplicativo e pode funcionar em sessões gráficas e terminais virtuais. Consulte a documentação oficial: https://github.com/rvaiya/keyd

## Mapeamento recebido e interpretação

Você confirmou que a primeira interpretação é a correta: por exemplo, ao pressionar a tecla física Q, o computador recebe/apresenta `'`; o objetivo é fazer o sistema receber Q novamente.

O perfil foi atualizado com o **mapa inverso**: cada sinal atualmente recebido é convertido na tecla que deveria ter sido pressionada. Exemplos: `apostrophe = q`, `comma = w`, `p = r`, `g = u`.

Foi incluída a tentativa `s = rightbrace` para recuperar a tecla Ç em layout ABNT2. **Essa tecla precisa ser confirmada com `keyd monitor` antes da ativação**, pois o código físico da tecla Ç varia conforme o teclado e o firmware. Se o monitor mostrar outro nome, ajuste o lado esquerdo dessa linha para o nome observado.

O perfil também contém as conversões inversas para todas as demais teclas informadas. A e M já estão corretas e não precisam de remapeamento.

## Instalação

No Linux Mint XFCE ou outra distribuição baseada em apt, abra o terminal na pasta deste módulo:

```bash
chmod +x install.sh rollback.sh identify.sh
./install.sh
```

O instalador:
- tenta instalar o pacote `keyd` pelos repositórios já configurados;
- valida o perfil antes de aplicá-lo;
- salva a configuração anterior em `/var/backups/aoc-keyboard`;
- ativa o serviço e recarrega o mapa.

Se o pacote não estiver disponível, siga a instalação indicada pelo projeto oficial keyd. O script não adiciona PPAs nem compila software automaticamente.

## Identificar as teclas reais

```bash
./identify.sh
```

O comando mostra os nomes das teclas e os identificadores dos dispositivos. Para inspecionar eventos físicos originais, pare temporariamente o serviço com `sudo systemctl stop keyd`, execute `sudo keyd monitor` e depois reative com `sudo systemctl start keyd`.

## Desfazer

```bash
./rollback.sh
```

Se uma configuração incorreta bloquear a digitação, a sequência de emergência do keyd é **Backspace + Esc + Enter**. Um teclado USB externo também pode ajudar a recuperar o acesso.

Os scripts Bash deste módulo são verificados automaticamente pelo GitHub Actions junto com os testes do migrador.

## Limites

- O programa corrige o sinal lógico enviado pelo teclado; não conserta teclas fisicamente quebradas, contatos intermitentes ou falhas no cabo/controlador.
- O perfil de exemplo é global para teclados identificados pelo keyd como teclado (`k:*`). Para afetar somente um dispositivo, substitua essa seleção pelo ID obtido no monitor.
- Layout regional (ABNT2, US etc.) e remapeamento são camadas diferentes. Primeiro configure o layout físico correto nas configurações do Linux; depois aplique apenas as substituições necessárias.
- Não aplique o exemplo sem conferir a tabela: ele altera seis teclas deliberadamente.
