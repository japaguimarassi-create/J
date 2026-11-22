# Guia de instalação — computador AOC

## Distribuição inicial

O projeto aponta para Linux Mint 22.3 XFCE como primeira opção para avaliação de um computador antigo. O XFCE é a edição leve do Mint. A edição 22.3 é LTS e o projeto informa suporte até abril de 2029.

Antes de escolher, confirme o processador: a ISO indicada é de 64 bits (x86-64). Se o processador for apenas 32 bits, não use essa ISO. Se houver placa NVIDIA muito antiga, confira as notas de versão e teste o modo live antes de instalar.

Requisitos publicados pelo Linux Mint 22.3: 2 GB de RAM (4 GB recomendados), 20 GB de espaço em disco (100 GB recomendados) e resolução de 1024×768.

Fontes oficiais:
- Download: https://linuxmint.com/download.php
- Notas da versão: https://www.linuxmint.com/rel_zena.php
- Verificação da ISO: https://linuxmint.com/verify.php
- Guia de instalação: https://linuxmint-installation-guide.readthedocs.io/en/latest/

## Ordem segura

1. Rode migrate.py info e guarde o resultado.
2. Conecte um HD externo diferente do disco interno.
3. Faça a simulação e depois o backup.
4. Rode verify e confirme zero falhas.
5. Faça uma segunda cópia das gravações e imagens insubstituíveis.
6. Crie o pendrive de instalação usando uma ISO oficial verificada.
7. Inicialize pelo USB em modo live e avalie o funcionamento.
8. Instale somente quando os dados estiverem seguros.

## Atenção ao particionamento

A instalação não é automatizada por este repositório. O instalador gráfico do Linux pode apagar partições. O disco externo de backup deve ficar desconectado durante a escolha de partições para reduzir o risco de selecioná-lo por engano.

Se o objetivo for manter o Windows inicializável, não escolha a opção de apagar o disco. Se o objetivo for substituir o Windows, ainda assim confirme o modelo e a capacidade do disco interno antes de autorizar o apagamento.

Não apague nem doe o computador antigo até confirmar que imagens, gravações, e-mail e saves estão acessíveis no Linux.
