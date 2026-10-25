# Reality Engine AI

Mod experimental para Minecraft Java Edition 1.7.10 com Forge 10.13.4.1614.

## Regra do chat

A solicitação só é interceptada quando a primeira palavra é exatamente CRIE, sem diferenciar maiúsculas de minúsculas. Espaços externos são removidos. "quero criar", "/crie algo" e "crielobo" são ignorados. Escrever apenas "crie" mostra a sintaxe, sem gerar conteúdo.

## Implementado no protótipo 0.1.0

- Núcleo local, sem serviços externos nem chaves de API.
- Interpretador determinístico por palavras-chave.
- Artefatos itemizados com descrição em NBT.
- Blocos universais com a descrição salva em TileEntity.
- Criaturas genéricas nomeadas, com atributos básicos e IA de caminhada/fuga.
- Dimensões novas com terreno padrão e escolha de bioma por palavras-chave.
- Testes da barreira do chat e workflow para compilar/testar.

## Limites técnicos explícitos

Esta versão não é uma IA neural de propósito geral. Ela não transforma qualquer frase em código novo nem implementa automaticamente qualquer lei física, poder ou geometria. Os itens e blocos são representações universais, não armas com poderes arbitrários. A entidade tem comportamento genérico e escala limitada para reduzir riscos de travamento. As dimensões usam o gerador padrão do Minecraft; a descrição usada para escolher bioma fica em memória nesta versão, portanto a persistência completa dos metadados após reinicialização ainda precisa ser validada.

Build e testes automatizados ajudam a detectar erros, mas não provam 100% de funcionamento. Ainda é necessário testar a instalação e o jogo em uma instância Forge real de 1.7.10.

## Exemplos

- CRIE uma espada de energia
- crie um bloco de cristal
- CrIe um dragão de 100 metros
- crie uma dimensão de neve
- crie um planeta desértico

## Instalação

1. Use Minecraft Java 1.7.10 com Forge 10.13.4.1614.
2. Baixe o JAR do artefato do GitHub Actions quando o workflow terminar com sucesso.
3. Coloque o JAR na pasta mods da instância.
4. No single-player, envie uma mensagem de chat começando com crie. Em servidores dedicados, o mod precisa estar instalado no servidor.

Não instale em servidores de terceiros sem autorização.

## Compilação

Requer JDK 8 e Gradle 5.6.4. Execute gradle clean test build.

## Referências técnicas

- Exemplo ForgeGradle 1.2: https://github.com/anatawa12/ForgeGradle-example
- Guia de workspace legado: https://legacymoddingmc.github.io/wiki/forge-workspace-setup/
- JavaDoc Forge 1.7.10 DimensionManager: https://legacymcmodding.github.io/Forge-JavaDoc/generated/1.7.10-10.13.4.1614/net/minecraftforge/common/DimensionManager.html
