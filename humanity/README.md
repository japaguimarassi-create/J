# HUMANITY — Simulação de evolução de uma civilização

Protótipo 3D de vida artificial e evolução cultural, feito para navegador e dispositivos móveis. O mundo começa como uma vila agrícola pré-industrial. Não há eletricidade, internet, motores, computadores ou tecnologias modernas dentro da vila; as descobertas dependem de experimentação simulada, materiais, habilidades e transmissão social.

## Executar

Abra `humanity/index.html` por um servidor estático ou publique a pasta `humanity` em um serviço de hospedagem estática. O navegador precisa de internet para carregar Three.js 0.161 pelo CDN.

## Simulação atual

- Mundo 3D com terreno irregular reproduzível, rio, floresta, casas, fogueira, campos de cultivo e artefatos que aparecem quando uma tecnologia é descoberta.
- 24 habitantes iniciais; limite atual de 180.
- Necessidades individuais: fome, energia, saúde, sociabilidade e idade.
- Recursos da vila: alimento, água, madeira, pedra, argila, fibras, minério e sementes.
- Estações, crescimento de lavouras, plantio, colheita, pesca/forrageamento e coleta.
- Animais domesticados com idade, reprodução e mortalidade.
- Infância com dependência de cuidadores, envelhecimento e morte.
- Vínculos, parentesco, herança parcial de traços e habilidades.
- Conhecimento individual, invenções sujeitas a pré-requisitos, habilidades e custos de materiais.
- Aprendizagem social de técnicas e de um vocabulário simbólico emergente.
- Memória episódica de ações e memória autobiográfica de eventos importantes.
- Salvamento automático e manual em IndexedDB; localStorage é usado como fallback.
- Importação de personagens humanoides GLB/FBX, clips de animação e elementos de cenário GLB/FBX.
- Elementos importados podem ser espalhados pelo cenário por nome de arquivo: árvores recebem cópias adicionais; casas, muros e objetos recebem posições iniciais. Os modelos externos são locais à sessão e precisam ser importados novamente após recarregar.

## Arquitetura neural por habitante

Cada pessoa tem três módulos artificiais treinados online dentro da simulação:

| Módulo | Arquitetura | Papel |
|---|---:|---|
| Política de ação | 14 → 256 → 8 | Escolher entre 8 ações |
| Avaliador | 14 → 32 → 1 | Estimar valor e calcular vantagem |
| Modelo preditivo | 22 → 24 → 4 | Prever fome, energia, saúde e sociabilidade depois de uma ação |

A rede de decisão usa atualização por gradiente de política; o avaliador usa uma atualização actor-critic simplificada; o modelo preditivo aprende com transições observadas. A memória de trabalho retém até 96 experiências recentes. Há também até 64 eventos autobiográficos registrados por pessoa.

Cada habitante contém aproximadamente 6.736 pesos treináveis. No limite de 180 habitantes, isso representa aproximadamente 1.212.480 pesos distribuídos entre agentes. A rede não é um modelo de linguagem e não foi pré-treinada com dados humanos: ela aprende somente por recompensas e transições dentro deste ambiente.

## Personagens e animações 3D

O modelo procedural de pessoa é apenas um substituto visual. Para personagens realistas:

1. Crie ou exporte um personagem humanoide já rigado em GLB ou FBX.
2. Na simulação, use **Modelo humano 3D** para importar o personagem.
3. Use **Animações 3D** para selecionar um ou vários arquivos de animação compatíveis.
4. Use **Elementos da vila 3D** para importar modelos GLB/FBX de árvores, casas, celeiros, muros e objetos. Nomeie os arquivos com termos como `tree`, `house`, `wall`, `fence` ou equivalentes em português para melhorar a distribuição automática.

Fontes recomendadas:

- [Ara 3D Gen](https://ara3dgen.com/): criador de personagens humanoides com pele, cabelo, roupas, rig e exportação GLB/FBX. Verifique os termos dos ativos que exportar.
- [Quaternius Universal Animation Library](https://quaternius.com/packs/universalanimationlibrary.html): mais de 120 animações humanoides; a página declara licença CC0 e inclui locomoção, sentar, rastejar e outras ações.
- [Quaternius Universal Animation Library 2](https://quaternius.com/packs/universalanimationlibrary2.html): pacote complementar com 130+ animações, incluindo agricultura e pesca; o autor declara CC0.
- [Quaternius Medieval Village MegaKit](https://quaternius.com/packs/medievalvillagemegakit.html): mais de 300 peças modulares de vila, em FBX, OBJ, Blend e glTF, com licença CC0. Baixe o pacote, extraia os arquivos e importe os GLB/FBX pelo botão **Elementos da vila 3D**.
- [SupaVoxel — Animate 3D Model](https://supavoxel.com/tools/animate-3d-model): ferramenta no navegador que anuncia retargeting de animações CC0 para personagens humanoides e exportação GLB.
- [SupaVoxel — Animate 3D Model](https://supavoxel.com/tools/animate-3d-model): ferramenta no navegador que anuncia retargeting de animações CC0 para personagens humanoides e exportação GLB.

**Compatibilidade:** o importador deste protótipo não executa retargeting automático. Clipes importados separadamente precisam usar nomes de ossos/trilhas compatíveis com o esqueleto do personagem. Quando os rigs forem diferentes, faça retargeting antes de importar. A simulação tenta selecionar clipes por nomes como walk, idle, farm, harvest, chop, fish, build e talk; se não encontrar um clipe adequado, usa uma animação de caminhada/repouso disponível.

## Limitações que ainda existem

- O mundo, edifícios, vegetação e animais ainda usam geometria procedural simplificada; não são um cenário fotorealista completo.
- Os personagens só ficam realistas depois que o utilizador importa um ou mais modelos humanos rigados.
- O importador de cenário distribui modelos por regras simples de nome e dimensão; ele não reconstrói automaticamente um mapa modular completo nem entende a semântica dos objetos.
- O importador não retargeta esqueletos automaticamente.
- O vocabulário é simbólico: transmissão de palavras e conceitos, não conversação humana livre com gramática.
- A cognição é uma aproximação de vida artificial, não uma cópia do cérebro humano.
- Não há ainda percepção visual real, audição, linguagem natural aberta, sistema político completo, medicina detalhada, clima meteorológico completo ou economia histórica aprofundada.
- O estado da simulação é salvo no dispositivo. Arquivos de personagens, animações e cenário importados não são incorporados ao salvamento e precisam ser selecionados novamente depois de recarregar ou trocar de dispositivo.

## Próximas etapas técnicas

1. Testes de equilíbrio populacional e calibração dos ciclos de fome, colheita e água.
2. Sistema de relações familiares, amizade, cooperação, conflito e luto com efeitos comportamentais.
3. Comunicação composicional: combinar símbolos em frases e associar símbolos a objetos/ações observadas.
4. Experimentos materiais com hipóteses, tentativas, falhas, validação e aperfeiçoamento de ferramentas.
5. Modelos GLB para casas, ferramentas, vegetação, animais e recursos.
6. LOD, instanciamento de malhas e atualização neural em lotes para centenas de agentes no celular.

## Licença

O código do protótipo é disponibilizado sob MIT. Three.js e ativos externos mantêm suas próprias licenças.
