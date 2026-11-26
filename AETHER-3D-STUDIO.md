# Aether 3D Studio

Editor 3D no navegador, com interface responsiva para desktop e Android.

## Recursos incluídos

- Criação de cubos, esferas, cilindros, cones, toros, nós toroidais, planos e rochas procedurais.
- Seleção pela árvore da cena ou diretamente no viewport.
- Transformações de mover, girar e escalar com gizmos.
- Materiais físicos PBR com presets de cromo, aço, ouro, cerâmica, vidro, plástico, borracha, pedra e superfície orgânica.
- Controles de cor, rugosidade, metalização e clearcoat.
- Ambiente de estúdio com reflexos, iluminação direcional, sombras e tone mapping ACES.
- Importação de modelos GLB.
- Exportação GLB, OBJ, STL, captura PNG e projeto JSON.
- Salvamento local no navegador.
- Controles de toque, órbita e zoom para telas móveis.

## Executar

O projeto é estático. Abra por um servidor HTTP (não por `file://`) para que os módulos ES sejam carregados corretamente.

Com Python:

```bash
python -m http.server 8000
```

Depois abra `http://localhost:8000`.

A biblioteca Three.js 0.187.0 e seus módulos são carregados pelo CDN jsDelivr. É necessária conexão com a internet na primeira abertura e suporte a WebGL no navegador.

## Publicar com Vercel

1. Importe o repositório `japaguimarassi-create/J` na Vercel.
2. Selecione a branch `aether-3d-studio-v1`.
3. Defina o diretório raiz como `/` (raiz do repositório).
4. Use o preset `Other`, sem comando de build e com diretório de saída `.`.
5. Faça o deploy.

## Limites desta versão

Este é um editor procedural e manual, não um gerador de malhas por IA. A qualidade final depende da geometria, das texturas e da iluminação fornecidas. Esta versão inclui materiais PBR e um ambiente de estúdio procedural; não inclui escultura digital avançada, rigging, animação, texturas fotogramétricas ou geração de modelos por texto. O modo de alta qualidade pode consumir mais memória e processamento em celulares.

## Tecnologia

- Three.js 0.187.0
- WebGL
- JavaScript ES Modules
- HTML e CSS sem etapa de build
