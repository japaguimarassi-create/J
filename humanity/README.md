# HUMANITY — Simulação de evolução de uma civilização

Protótipo web 3D mobile-first de uma vila pré-industrial. A simulação roda no navegador usando Three.js e JavaScript, sem serviços de IA externos.

## Executar

Abra `humanity/index.html` por um servidor estático ou habilite GitHub Pages para servir a pasta/arquivo. É necessário acesso à internet para carregar Three.js pelo CDN.

## O que já existe

- Terreno, rio, floresta, casas, campos, fogueira e animais gerados proceduralmente.
- 24 habitantes iniciais com idade, saúde, fome, energia, sociabilidade, traços individuais e habilidades.
- Agentes com uma pequena rede neural MLP individual (10 entradas, 12 unidades ocultas, 8 ações).
- Atualização online por gradiente de política com recompensa, baseline e memória episódica curta.
- Ações de plantar, colher, coletar madeira, buscar água, construir, socializar, descansar e explorar.
- Envelhecimento, mortalidade, vínculos, reprodução probabilística e nascimentos.
- Progressão tecnológica condicionada a recursos e população.
- Animações procedurais simples de caminhada e repouso; inspeção de habitantes, velocidade, pausa e avanço manual.

## Limites científicos e técnicos

Este é um protótipo de vida artificial, não uma reprodução de um cérebro humano. Os nomes de regiões cerebrais são inspirações arquiteturais; não há equivalência biológica. O treinamento é online e local, baseado em recompensas simuladas. Não existe pré-treinamento em dados humanos, linguagem natural avançada, percepção visual real, genética complexa, cultura detalhada, medicina, clima completo ou economia robusta.

Os humanos 3D atuais são figuras procedurais simplificadas, não modelos anatômicos fotorealistas. As animações atuais são procedurais, não captura de movimento. O próximo estágio visual deve substituir os placeholders por personagens humanoides rigados GLB/FBX e clips retargetáveis.

## Fontes de modelos e animações para a próxima etapa

- [Ara 3D Gen](https://github.com/TuriaArt/3d-gen-TU): gerador aberto de personagens humanoides rigados, com exportação GLB/FBX e biblioteca de animações; conferir licenças e requisitos.
- [Moveset Free](https://extensions.blender.org/add-ons/moveset/): animações procedurais para rigs humanoides e exportação GLB/FBX.
- [Three procedural locomotion](https://github.com/PabloMesquida/three-procedural-locomotion): locomoção procedural para Three.js.
- [Quaternius Universal Animation Library](https://quaternius.com/): animações e assets 3D; conferir licença de cada pacote.

## Próximas etapas recomendadas

1. Persistência de mundo e estado dos agentes em IndexedDB.
2. Agricultura sazonal com ciclos de crescimento, estoque e fome real.
3. Reprodução com herança de traços, parentesco e cuidado infantil.
4. Aprendizagem social, linguagem emergente simplificada e transmissão de técnicas.
5. Sistema de experimentos e invenções com materiais, hipóteses, falhas e validação.
6. Personagens GLB rigados, retarget de animações de trabalho, cuidado, caça, construção e interação.
7. Otimização por lotes/LOD para centenas de habitantes em celulares.

## Licenças

O código deste protótipo é disponibilizado sob MIT. As dependências e assets externos mantêm suas próprias licenças.
