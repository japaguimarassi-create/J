# HyperCode AI

Chat Android e projeto de pesquisa de uma rede neural coletiva universal para programação.

## Arquitetura pretendida

- Sete redes neurais completas, todas universais e treinadas com os mesmos dados.
- Cada rede recebe o mesmo contexto e executa dez camadas de 256 unidades.
- Após cada camada, há comunicação por atenção entre os sete estados. Nenhuma rede é escolhida isoladamente.
- As sete representações de 256 dimensões são concatenadas em um estado coletivo de 1.792 dimensões.
- O núcleo coletivo executa vinte camadas de 1.792 unidades e produz a única resposta final.
- O treinamento é progressivo: sete redes universais individualmente, núcleo, comunicação mútua, integração conjunta e SFT com mascaramento do prompt.

## Estado real

- Código da arquitetura universal e comunicação mútua: implementado no diretório training.
- Tokenização procedural: doze etapas de texto e doze de código; idioma identificado pela primeira frase e vocabulário técnico em inglês.
- Treino smoke com pesos atualizados: executado em CPU numa arquitetura reduzida; evidência em training/smoke_evidence.json.
- Testes estruturais: quatorze verificações; CI do GitHub valida arquitetura, pré-treino, SFT, sequência progressiva e avaliação coletiva.
- Pré-treinamento causal smoke: executado por 80 passos com pesos atualizados e perda de validação reduzida.
- Ajuste supervisionado smoke: executado por 100 passos, mascarando o prompt e treinando apenas a resposta do assistente.
- Pipeline progressivo smoke: validado em CI com sete redes, núcleo, comunicação, integração conjunta e avaliação das oito saídas.
- Treinamento da arquitetura-alvo 7×(10×256)+20×1792 (456.728.352 parâmetros): ainda não executado; requer GPU CUDA com memória suficiente e corpus grande/licenciado.
- Geração e comparação: 56 candidatos (sete redes + núcleo em sete tarefas) foram comparados. O NLL coletivo caiu de 4,600 antes do SFT para 4,089 após; a verificação sintática estrita final aprovou 0 candidatos. Isso não prova competência de programação.
- O chat Android ainda não executa os pesos PyTorch. O código da interface informa essa limitação explicitamente.
- O perfil de teste ainda usa 260 IDs byte-level e contexto 256; antes do treino de produção, a configuração precisa migrar para BPE e contexto maior.
- O APK não foi recompilado após essas alterações de rede; o workflow Android exige confirmação manual exata `agora compile`.

## Build

A compilação do APK é manual e condicionada à confirmação exata "agora compile". Commits de código e testes não compilam o aplicativo automaticamente. Não execute o workflow de APK antes dessa confirmação.

## Treinamento e avaliação

Consulte training/README.md para preparar o corpus licenciado, treinar a arquitetura-alvo, gerar código pelas sete redes e pelo núcleo, comparar NLL e validar candidatos. O perfil-alvo exige CUDA e um corpus grande; o script recusa simular o treino-alvo em CPU.
