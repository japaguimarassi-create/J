# HyperCode AI

Aplicativo Android de chat para assistência em programação, acompanhado de uma arquitetura experimental de sete especialistas e um núcleo GPT causal.

## Estado da versão 0.1

- Interface Android nativa e chat local: implementados.
- Detecção do idioma pela primeira frase: implementada para português, inglês, espanhol e francês.
- Vocabulário técnico inglês: incluído no pipeline de treinamento.
- Sete especialistas e núcleo central: definidos no modelo PyTorch.
- 12 estágios de processamento textual e 12 estágios de processamento de código: definidos.
- Pré-treinamento GPT: código implementado, ainda não executado com corpus real.
- Pesos GPT no APK: não incluídos.
- Respostas no APK: modo determinístico inicial, não um LLM treinado.

## Build do APK

O GitHub Actions compila o APK debug em cada push que altera esta pasta. Abra a aba Actions do repositório e baixe o artefato hypercode-debug-apk quando o job terminar com sucesso.

## Treinamento

Consulte training/README.md. O perfil smoke testa o pipeline em escala reduzida. O perfil target representa a arquitetura solicitada e exige GPU CUDA com grande memória e um corpus licenciado de programação e linguagem natural.

## Contagem de unidades

7 × (10 × 256) = 17.920 unidades especializadas.

20 × 1.792 = 35.840 unidades centrais.

O núcleo possui exatamente o dobro das unidades dos sete especialistas juntos.
