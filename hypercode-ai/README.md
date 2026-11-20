# HyperCode AI

Chat Android e projeto de pesquisa de uma rede neural coletiva universal para programação.

## Arquitetura pretendida

- Sete redes neurais completas, todas universais e treinadas com os mesmos dados.
- Cada rede recebe o mesmo contexto e executa dez camadas de 256 unidades.
- Após cada camada, há comunicação por atenção entre os sete estados. Nenhuma rede é escolhida isoladamente.
- As sete representações de 256 dimensões são concatenadas em um estado coletivo de 1.792 dimensões.
- O núcleo coletivo executa vinte camadas de 1.792 unidades e produz a única resposta final.
- Uma rede-base universal é pré-treinada primeiro; seus pesos inicializam os sete ramos. Em seguida vêm o treino individual, o núcleo, a comunicação mútua, a integração conjunta e o SFT com mascaramento do prompt.

## Estado real

- Código da arquitetura universal e comunicação mútua: implementado no diretório training.
- Tokenizer procedural de 260 IDs mantido para smoke tests; novo tokenizer alvo BPE byte-level de até 32.768 IDs, treinado a partir do corpus e versionado pelo SHA-256.
- Treino smoke com pesos atualizados: executado em CPU numa arquitetura reduzida; evidência em training/smoke_evidence.json.
- Testes estruturais: 20 testes definidos, incluindo transferência dos pesos da fundação para os sete ramos; execução da nova suíte aguardando CI.
- Pré-treinamento causal smoke: executado por 80 passos com pesos atualizados e perda de validação reduzida.
- Ajuste supervisionado smoke: executado por 100 passos, mascarando o prompt e treinando apenas a resposta do assistente.
- Pipeline progressivo smoke anterior: validado em CI com sete redes, núcleo, comunicação, integração conjunta e avaliação das oito saídas. A execução revisada agora acrescenta o pré-treino da fundação e os novos testes.
- Treinamento da arquitetura-alvo (sete ramos de 10×256 e núcleo de 20×1792): ainda não executado; o total de parâmetros depende agora do tamanho efetivo do BPE e deve ser medido no checkpoint. Requer GPU CUDA BF16 e corpus grande/licenciado.
- Geração e comparação: 56 candidatos (sete redes + núcleo em sete tarefas) foram comparados. O NLL coletivo caiu de 4,600 antes do SFT para 4,089 após; a verificação sintática estrita final aprovou 0 candidatos. Isso não prova competência de programação.
- O chat Android ainda não executa os pesos PyTorch. O código da interface informa essa limitação explicitamente.
- Perfil smoke continua com dimensões pequenas e tokenizer byte-level; perfil alvo configurado para BPE byte-level de 32k e contexto 2.048.
- Nova fundação universal e receita de treino: AdamW com weight decay seletivo, WSD, acumulação de gradientes, clipping, BF16 e RNG state nos checkpoints; aguardando validação da revisão completa em CI.
- O APK não foi recompilado; a compilação continua condicionada à confirmação manual exata `agora compile`.

## Build

A compilação do APK é manual e condicionada à confirmação exata "agora compile". Commits de código e testes não compilam o aplicativo automaticamente. Não execute o workflow de APK antes dessa confirmação.

## Treinamento e avaliação

Consulte training/README.md para preparar o corpus licenciado, treinar a arquitetura-alvo, gerar código pelas sete redes e pelo núcleo, comparar NLL e validar candidatos. O perfil-alvo exige CUDA e um corpus grande; o script recusa simular o treino-alvo em CPU.
