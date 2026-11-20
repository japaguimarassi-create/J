# HyperCode AI

Chat Android e projeto de pesquisa de uma rede neural coletiva universal para programação.

## Arquitetura pretendida

- Sete redes neurais completas, todas universais e treinadas com os mesmos dados.
- Cada rede recebe o mesmo contexto e executa dez camadas de 256 unidades.
- Após cada camada, há comunicação por atenção entre os sete estados. Nenhuma rede é escolhida isoladamente.
- As sete representações de 256 dimensões são concatenadas em um estado coletivo de 1.792 dimensões.
- O núcleo coletivo executa vinte camadas de 1.792 unidades e produz a única resposta final.
- O treinamento usa previsão causal do próximo token, com perda principal na saída coletiva e perdas auxiliares nas sete redes.

## Estado real

- Código da arquitetura universal e comunicação mútua: implementado no diretório training.
- Tokenização procedural: doze etapas de texto e doze de código; idioma identificado pela primeira frase e vocabulário técnico em inglês.
- Treino smoke com pesos atualizados: executado em CPU numa arquitetura reduzida; evidência em training/smoke_evidence.json.
- Testes estruturais: seis aprovados.
- Treinamento da arquitetura-alvo 7×(10×256)+20×1792: ainda não executado.
- Geração de código no teste smoke: candidatos foram comparados; nenhum passou a verificação sintática. A perda coletiva foi menor que a média das sete saídas individuais, mas isso não prova competência de programação.
- O chat Android ainda não executa os pesos PyTorch. O código da interface informa essa limitação explicitamente.

## Build

A compilação do APK é manual e condicionada à confirmação exata "agora compile". Commits de código e testes não compilam o aplicativo automaticamente. Não execute o workflow de APK antes dessa confirmação.

## Treinamento e avaliação

Consulte training/README.md para preparar o corpus licenciado, treinar a arquitetura-alvo, gerar código pelas sete redes e pelo núcleo, comparar NLL e validar candidatos. O perfil-alvo exige CUDA e um corpus grande; o script recusa simular o treino-alvo em CPU.
