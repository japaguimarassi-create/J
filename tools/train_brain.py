import json, os, random, re, time, unicodedata
from pathlib import Path
import numpy as np

ROOT = Path("src/main/resources/assets/realityengineai/brain")
ROOT.mkdir(parents=True, exist_ok=True)
VOCABULARY, EMBEDDING, HIDDEN = 2048, 128, 224
CLASSES = "entity_car block_crystal block_generic entity_dragon entity_hostile entity_creature item_sword item_tool item_food item_generic dimension_desert dimension_cold dimension_forest dimension_space dimension_infernal dimension_generic query_mods query_blocks query_items query_entities query_dimensions command_enter ask_help ambiguous structure_house structure_castle structure_tower structure_bridge structure_city structure_maze terrain_plain terrain_desert terrain_mountain terrain_snow terrain_volcanic map_procedural block_machine block_corrupted item_staff item_amulet item_dagger".split()
OUTPUTS = len(CLASSES)
PARAMETER_COUNT = VOCABULARY*EMBEDDING + EMBEDDING + EMBEDDING*HIDDEN + HIDDEN + HIDDEN*OUTPUTS + OUTPUTS
SEED = 171025
RAW = {
"entity_car":"carro como entidade|carro que se move|entidade de automóvel|caminhão como mob|moto com rodas|veículo pilotável|ônibus como criatura|tanque dirigível como entidade|carro spawnável como mob|veículo que segue o jogador|bicicleta entidade",
"block_crystal":"bloco de cristal luminoso|bloco de ametista|cristal sólido para construir|bloco cristalino que emite luz|bloco de quartzo brilhante|cristal em formato de bloco|bloco de energia azul|bloco de gema roxa|bloco de cristal transparente|bloco que ilumina a sala|glowing crystal block",
"block_generic":"bloco de pedra azul|bloco de obsidiana personalizado|bloco sólido de metal|bloco que cura ao clicar|bloco de areia colorida|bloco personalizado para construção|bloco que concede velocidade|bloco decorativo funcional|bloco de material novo|bloco de madeira escura|bloco sólido chamado ônix",
"entity_dragon":"dragão com asas|entidade dragão|mob dragão gigante|dragão voador para o mundo|criatura dragão roxa|spawnar dragão personalizado|monstro dragão com cauda|dragão que anda pelo mapa|entidade de dragão lendário|dragão como mob|dragon entity",
"entity_hostile":"monstro hostil que ataca|boss inimigo|criatura agressiva|zumbi personalizado que persegue|mob que ataca jogadores|entidade inimiga|monstro que persegue criaturas|boss hostil para o mundo|adversário agressivo|inimigo que segue jogador|hostile mob",
"entity_creature":"criatura amigável|animal novo|mob que caminha|entidade viva personalizada|animal que segue jogador|criatura de estimação|ser vivo com nome próprio|entidade bípede amigável|mob pacífico|criatura com textura própria|custom creature",
"item_sword":"espada de energia|katana azul|espada de pedra|sabre de cristal|lâmina corpo a corpo|item espada de dano alto|espada personalizada no inventário|espada de fogo|espada encantada|item cortante tipo espada|sword item",
"item_tool":"picareta de cristal|machado de ferro como item|ferramenta para minerar|picareta personalizada|machado que quebra pedra|ferramenta de mineração no inventário|pá como item|item de ferramenta|picareta resistente|ferramenta para coletar minério|pickaxe item",
"item_food":"comida que recupera fome|pão especial|maçã que cura|fruta personalizada como item|carne comestível|alimento no inventário|item de comida|pão mágico que recupera energia|refeição especial|fruta que dá regeneração|food item",
"item_generic":"item chamado amuleto misterioso|artefato de cura|objeto encantado no inventário|item mágico personalizado|artefato chamado núcleo|objeto como item|relíquia que concede força|item chamado essência|acessório de inventário|artefato com efeito|objeto especial para inventário",
"dimension_desert":"dimensão de deserto|planeta desértico|mundo de dunas|dimensão coberta de areia|universo desértico|novo mundo com bioma deserto|desert dimension|dimensão quente e seca|planeta com dunas|dimensão arenosa|mundo de terreno desértico",
"dimension_cold":"dimensão de neve|mundo de gelo|dimensão congelada|planeta frio e nevado|snow dimension|mundo coberto de geleiras|dimensão de frio extremo|universo de neve|planeta gelado|dimensão com gelo|mundo congelado",
"dimension_forest":"dimensão de floresta|mundo com árvores altas|dimensão de selva|forest dimension|planeta florestal|mundo com mata densa|dimensão com árvores e grama|mundo verde com florestas|dimensão arborizada|universo de selva|dimensão cheia de árvores",
"dimension_space":"dimensão no espaço|mundo sem céu|dimensão da galáxia|planeta espacial|space dimension|universo vazio com estrelas|dimensão cósmica|mundo no vazio|planeta do espaço|universo lunar|dimensão de estrelas",
"dimension_infernal":"dimensão infernal|mundo de lava e fogo|mundo vulcânico|dimensão de vulcão|infernal dimension|dimensão cheia de lava|planeta de chamas|mundo de netherrack|universo de fogo|mundo infernal escuro|dimensão de fogo",
"dimension_generic":"nova dimensão|planeta personalizado|mundo novo|dimensão própria|new dimension|universo diferente|espaço de jogo dimensional|novo mundo dimensional|dimensão customizada|planeta com terreno próprio|dimension",
"query_mods":"lista de mods instalados|quais mods estão carregados|mostrar todos os mods|mod list|quais mods estão ativos|nomes dos mods instalados|catálogo de mods|modificações funcionando|listar mods do forge|consultar mods carregados|mods neste Minecraft",
"query_blocks":"liste os blocos registrados|catálogo de blocos|quantos blocos existem|block registry|listar blocos|consultar registros de blocos|blocos disponíveis|buscar blocos registrados|blocos do jogo|registro de blocos|quais blocos posso usar",
"query_items":"liste os itens registrados|catálogo de itens|quantos itens existem|item registry|listar itens|consultar registro de itens|itens disponíveis|mostrar itens existentes|itens do forge|catalogar itens|quais itens estão instalados",
"query_entities":"liste as criaturas registradas|quantas entidades existem|entity registry|mobs registrados|consultar entidades|lista de mobs|criaturas disponíveis|catálogo de entidades|entidades do jogo|mobs instalados|entidades registradas",
"query_dimensions":"liste as dimensões|quais dimensões existem|mundos registrados|dimension registry|consultar dimensões criadas|lista de dimensões|quantas dimensões existem|mostrar dimensões|mundos dimensionais|registro de dimensões|dimensões disponíveis",
"command_enter":"entrar na dimensão 3|ir para dimensão 4|teleportar para dimensão 12|entrar na última dimensão|enter dimension 5|visitar o mundo que criei|ir para a dimensão nova|entrar nessa dimensão|viajar para dimensão 7|entrar no planeta que criei|teleportar para o mundo dimensional",
"ask_help":"ajuda|quais comandos existem|como funciona|o que você sabe fazer|mostrar capacidades|help|comandos disponíveis|como usar essa IA|explique os comandos|quais são suas funções|como criar coisas",
"ambiguous":"faça algo incrível|crie aquilo|quero algo poderoso|surpreenda-me|make something|uma coisa legal|crie algo|não sei o que criar|faça qualquer coisa|invente uma coisa|quero algo diferente",
"structure_house":"construa uma casa de madeira|crie uma casa de pedra|construção de casa|edifício pequeno para morar|build a house|cabana de madeira|crie uma garagem com paredes e teto|abrigo de blocos|casa de dois andares|construção residencial|casa com janelas",
"structure_castle":"construa um castelo de pedra|crie uma fortaleza medieval|construção castelo|castelo com torres e muralhas|build a castle|forte de pedra|cidadela fortificada|castelo grande|castelo com muralhas|fortaleza com ameias|castelo para o mapa",
"structure_tower":"construa uma torre alta|crie uma torre de pedra|estrutura vertical alta|torre de observação|build a tower|torre com janelas|torre de vigia|construção em formato de torre|torre moderna de blocos|torre de madeira|arranha-céu em formato de torre",
"structure_bridge":"construa uma ponte sobre rio|crie uma ponte de madeira|construção de ponte|ponte de pedra entre montanhas|build a bridge|ponte com cercas laterais|passagem elevada entre terrenos|ponte comprida|ponte para atravessar água|estrutura ligando margens|ponte suspensa de blocos",
"structure_city":"construa uma cidade do zero|crie uma cidade com ruas|estrutura urbana|cidade pequena de blocos|build a city|bairro com casas e ruas|centro urbano com prédios|cidade com avenidas|vila organizada|pequena metrópole|área urbana completa",
"structure_maze":"construa um labirinto|crie um labirinto de pedra|construção cheia de corredores|maze structure|labirinto com paredes altas|percurso de paredes e caminhos|labirinto quadrado|maze de blocos|labirinto para explorar|estrutura de corredores|labirinto grande",
"terrain_plain":"gere um terreno plano|crie uma planície gramada|faça terreno quase plano|área plana de terra|generate flat terrain|campo aberto|superfície de grama e terra|nivelar pedaço de terreno|terreno de pedra plano|planície no mundo|área aberta sem construções",
"terrain_desert":"gere terreno desértico|terreno de areia e dunas|paisagem de deserto|terreno arenoso com elevações|generate desert terrain|área de areia e arenito|crie dunas no terreno|solo de deserto ondulado|terreno seco|terreno de areia sem edifícios|paisagem árida de areia",
"terrain_mountain":"gere terreno montanhoso|crie uma cadeia de montanhas|paisagem de montanhas|montanhas de pedra no terreno|generate mountain terrain|serra alta|terreno com picos e vales|crie uma cordilheira|montanhas naturais de blocos|terreno acidentado|paisagem rochosa com montanhas",
"terrain_snow":"gere terreno coberto de neve|paisagem congelada|solo nevado com elevações|snow terrain|área com blocos de neve|terreno gelado com neve|paisagem de inverno|terreno de gelo e neve|área branca de neve no solo|terreno frio com neve|neve no chão com relevo",
"terrain_volcanic":"gere terreno vulcânico|terreno de netherrack|paisagem com lava e rocha|volcanic terrain|terreno escuro de vulcão|área rochosa infernal|solo de lava solidificada|terreno perto de vulcão|paisagem quente e vulcânica|pedra preta e netherrack|área infernal de terreno",
"map_procedural":"crie um mapa do zero|gere um mapa procedural|mapa completo de jogo|generate a map|região de mundo com terreno|mapa novo com montanhas e planícies|mapa de aventura|mapa novo em área vazia|construa um mapa de jogo|mapa procedural de mundo aberto|base de um mapa Minecraft",
"block_machine":"crie um bloco de máquina|bloco de tecnologia interativo|bloco de computador|bloco que representa máquina|bloco de redstone personalizado|bloco tecnológico com textura própria|máquina em forma de bloco|bloco de circuito|bloco eletrônico para o mundo|bloco de tecnologia para clicar|machine block",
"block_corrupted":"crie um bloco corrompido|bloco infectado de energia roxa|bloco de corrupção|bloco corrompido escuro|corrupted block|bloco contaminado|bloco roxo com textura quebrada|bloco de terreno infectado|bloco de matéria corrompida|bloco com fissuras de corrupção|bloco contaminado personalizado",
"item_staff":"crie um cajado mágico|bastão de energia como item|varinha para lançar poderes|staff item|cajado que concede velocidade|item de magia com cabo|bastão místico no inventário|vara mágica|cajado de luz|varinha de poder personalizada|cajado que ativa efeito ao clicar",
"item_amulet":"crie um amuleto de proteção|amuleto mágico como item|amulet item|colar de energia para inventário|talismã de defesa|amuleto que protege o jogador|pingente de cristal|relíquia de proteção|acessório mágico em item|amuleto que aplica resistência|talismã personalizado",
"item_dagger":"crie uma adaga de cristal|punhal como item|dagger item|adaga corpo a corpo|faca de combate como item|punhal de energia|lâmina curta para o inventário|adaga mágica|adaga de pedra|item de arma curta|punhal personalizado"
}
EXTRA = {
"entity_car":"automóvel com movimento como entidade|carro que anda sozinho pelo mundo|entidade de caminhão com rodas|veículo dirigível no mundo|mob parecido com carro|crie um automóvel móvel",
"block_crystal":"cristal brilhante no mundo como bloco|bloco de cristal para iluminar cavernas|bloco de gema luminosa|bloco de cristal azul sólido|bloco de ametista que emite luz|material cristalino registrado como bloco",
"block_generic":"bloco sólido chamado basalto|bloco de tijolo verde para construir|bloco de pedra com alta resistência|cubo de madeira com textura própria|bloco customizado para colocar no chão|novo bloco de minério",
"entity_dragon":"adicionar dragão voador ao mundo|dragão que patrulha a área|mob de dragão grande|dragão com textura de escamas|entidade alada parecida com dragão|criatura réptil com asas",
"entity_hostile":"monstro que procura jogadores para atacar|mob inimigo com IA de perseguição|boss agressivo para a arena|criatura hostil contra o jogador|zumbi que luta contra jogadores|entidade perigosa que causa dano",
"entity_creature":"animal pacífico que caminha e olha ao redor|mob amigável com skin própria|criatura que vaga sem atacar|novo animal para o Minecraft|entidade dócil que acompanha jogador|personagem NPC amigável",
"item_sword":"adicionar katana ao inventário|lâmina de obsidiana como item|item de espada lendária|espada dourada que causa dano|arma espada com textura exclusiva|sabre no inventário do jogador",
"item_tool":"adicionar picareta ao inventário|machado customizado como item|ferramenta que minera blocos|item de pá de pedra|picareta com textura própria|ferramenta para quebrar minérios",
"item_food":"item comestível para recuperar fome|comida que restaura pontos de fome|alimento customizado de Minecraft|item de maçã comestível|pão restaurador no inventário|fruta que recupera vida e fome",
"item_generic":"relíquia para guardar no inventário|objeto chamado Núcleo Antigo|item genérico mágico|essência registrada como item|objeto carregável no inventário|item simples com nome próprio",
"dimension_desert":"mundo separado com areia e dunas|dimensão com bioma desértico|planeta dimensional de areia|mundo dimensional de arenito|outra dimensão seca|dimensão coberta por cactos",
"dimension_cold":"dimensão nova com gelo|mundo separado coberto por neve|planeta dimensional congelado|dimensão com geleiras azuis|outra dimensão gelada|mundo de inverno permanente",
"dimension_forest":"mundo separado de mata densa|dimensão com árvores gigantes|planeta coberto de floresta|outra dimensão cheia de selva|mundo dimensional verde|dimensão de árvores e cipós",
"dimension_space":"mundo separado no espaço sideral|dimensão cósmica com vazio|planeta sem céu normal|outra dimensão de estrelas|mundo espacial com baixa gravidade visual|dimensão lunar",
"dimension_infernal":"outro mundo de netherrack e lava|dimensão vulcânica hostil|planeta com rios de lava|mundo separado de fogo|dimensão de cinzas e rocha quente|bioma dimensional infernal",
"dimension_generic":"crie um espaço dimensional próprio|outro mundo separado do principal|mundo adicional com regras próprias|nova área dimensional|planeta independente para explorar|dimensão customizada sem tema",
"query_mods":"mostrar os mods Forge carregados agora|consultar lista de modificações instaladas|quais extensões estão ativas|mostrar nomes e identificadores dos mods|ver mods que estão funcionando|imprimir catálogo de mods",
"query_blocks":"pesquisar os blocos disponíveis no registro|mostrar identificadores de blocos|quais blocos foram registrados pelos mods|imprimir todos os blocos disponíveis|buscar bloco pelo nome|consultar IDs de blocos",
"query_items":"pesquisar os itens disponíveis no registro|mostrar identificadores dos itens|quais itens foram registrados pelos mods|imprimir catálogo completo de itens|buscar item pelo nome|consultar IDs de itens",
"query_entities":"pesquisar entidades do registro|mostrar tipos de criatura carregados|quais entidades os mods adicionaram|imprimir lista de entidades|consultar identificadores de mobs|buscar criatura registrada",
"query_dimensions":"quais dimensões foram registradas|mostrar IDs dos mundos dimensionais|pesquisar dimensão disponível|imprimir catálogo de dimensões|listar mundos extras do mod|consultar dimensão por ID",
"command_enter":"teleporte-me para dimensão 8|viajar até a dimensão 5|mude meu mundo para dimensão 4|entrar no mundo dimensional de neve|ir ao mundo criado anteriormente|usar o portal para outra dimensão",
"ask_help":"me mostre como usar o Reality Engine|quero aprender os comandos desta IA|explique o que posso criar|listar funções disponíveis|como funciona o comando de criação|ensine os comandos básicos",
"ambiguous":"faça algo sem explicar o tipo|quero que invente qualquer coisa|crie alguma coisa legal|não especifiquei o que criar|me surpreenda sem detalhes|execute uma criação aleatória",
"structure_house":"construa um abrigo com paredes e telhado|uma cabana para morar|casa compacta com porta e janelas|edifício residencial de madeira|construa uma moradia pequena|uma residência de blocos de pedra",
"structure_castle":"forte medieval com torres e muralhas|construa uma cidadela fortificada|castelo com ameias no alto|fortaleza de pedra com portão|castelo medieval para o mundo|um bastião com quatro torres",
"structure_tower":"construa torre de observação alta|estrutura estreita e vertical|torre de vigia feita de pedra|prédio alto em forma de torre|torre com pavimentos|torre alta com topo aberto",
"structure_bridge":"ponte para conectar duas margens|estrutura que cruza um rio|passarela elevada de madeira|construa um viaduto de blocos|ponte com corrimões|ponte comprida sobre um vale",
"structure_city":"bairro com ruas e edifícios|uma área urbana com avenidas|cidade organizada em quarteirões|centro urbano com casas|construa uma pequena metrópole|vila com ruas e prédios",
"structure_maze":"labirinto com caminhos e paredes|corredores entre muros altos|estrutura de labirinto para explorar|maze com rotas confusas|construa um percurso de paredes|labirinto fechado de pedra",
"terrain_plain":"terreno aberto nivelado|gere uma superfície plana com grama|planície sem prédios nem casas|área de solo plano para construir|terreno de terra sem relevo alto|nivelar o solo de um campo",
"terrain_desert":"paisagem seca com dunas onduladas|gere areia e arenito como relevo|terreno árido sem edifícios|solo desértico com elevações naturais|crie uma região de dunas|terreno arenoso e seco",
"terrain_mountain":"cadeia de picos rochosos|terreno alto com vales profundos|região montanhosa com elevação natural|gere uma serra de pedra|paisagem de picos e encostas|terreno de montanhas íngremes",
"terrain_snow":"solo coberto de blocos de neve|terreno nevado sem edifícios|paisagem de inverno montanhosa|gere uma área congelada|superfície branca de neve|terreno frio com camada de neve",
"terrain_volcanic":"solo de rocha vulcânica|terreno de netherrack com ondas|região com pedra quente e lava visual|paisagem com picos vulcânicos|chão infernal de rocha escura|terreno vulcânico irregular",
"map_procedural":"crie uma região inédita no mapa|gere uma área explorável do mundo|mapa novo procedural para aventura|mapa de mundo aberto|crie um território inteiro|construir uma região nova com relevo",
"block_machine":"bloco de circuito eletrônico|bloco tecnológico interativo|bloco de máquina industrial|um bloco eletrônico que responde ao clique|bloco computacional com luz|máquina registrada como bloco",
"block_corrupted":"bloco infectado roxo|bloco com rachaduras corruptas|bloco de matéria contaminada|bloco escuro de corrupção|bloco corrompido com linhas luminosas|bloco que parece infectado",
"item_staff":"cajado de energia no inventário|bastão mágico clicável|item de cajado que concede poderes|vara arcana como item|staff mágico para segurar|cajado que ativa efeitos ao usar",
"item_amulet":"talismã de resistência como item|amuleto que protege ao usar|objeto de amuleto no inventário|pingente de proteção mágico|item de proteção chamado amuleto|talismã com efeito de resistência",
"item_dagger":"adaga curta como item de arma|punhal personalizado no inventário|faca de combate do tipo adaga|adaga metálica com textura própria|arma curta de cristal|item de punhal para lutar"
}
for label, extra in EXTRA.items():
    RAW[label] += "|" + extra
EXTRA2 = {
"entity_car":"carro que anda como mob|entidade de veículo com rodas|carro independente no mundo|moto como criatura mecânica|caminhão dirigível como entidade|automóvel com IA de movimento",
"block_crystal":"bloco de quartzo brilhante|bloco de cristal lilás|bloco mineral luminoso|cristal grande como bloco sólido|bloco translúcido com luz|bloco de pedra preciosa",
"block_generic":"bloco de basalto personalizado|bloco de tijolos escuros|bloco de cobre para construir|bloco sólido de obsidiana|bloco decorativo colocado no chão|bloco de material próprio",
"entity_dragon":"criatura dragão voadora|mob de dragão que patrulha|dragão com cauda longa como entidade|ser alado gigantesco|entidade réptil que respira fogo|dragão NPC de Minecraft",
"entity_hostile":"inimigo que ataca o jogador|mob hostil que persegue criaturas|boss agressivo com IA|entidade inimiga que causa dano|monstro que busca alvos|criatura que ataca ao se aproximar",
"entity_creature":"animal dócil para o mundo|entidade que caminha e olha|mob amigável que segue o dono|criatura pacífica personalizada|ser vivo que não ataca|NPC animal com skin exclusiva",
"item_sword":"espada de diamante personalizada|katana para combate|espada para o inventário|lâmina mágica como item|sabre de metal|arma espada com textura",
"item_tool":"picareta especial como item|ferramenta de minerar no inventário|machado personalizado para cortar|item pá de madeira|picareta de cristal resistente|ferramenta que o jogador segura",
"item_food":"alimento que recupera fome|carne cozida especial|maçã mágica comestível|comida no inventário|fruta restauradora como item|pão que o jogador pode comer",
"item_generic":"objeto que caiba no inventário|item chamado núcleo antigo|artefato de magia simples|relíquia carregável|item decorativo sem bloco próprio|objeto personalizado como item",
"dimension_desert":"região dimensional de dunas|dimensão arenosa e quente|novo planeta com desertos|mundo de areia e cactos separado|mundo extra com bioma árido|dimensão coberta de arenito",
"dimension_cold":"mundo separado de inverno|dimensão de geleiras e neve|planeta com solo congelado|dimensão de gelo azul|mundo extra nevado|reino de neve",
"dimension_forest":"dimensão de floresta tropical|mundo separado coberto de árvores|planeta de selva densa|dimensão com copa de árvores|mundo extra cheio de vegetação|selva dimensional",
"dimension_space":"dimensão sem céu e com vazio|mundo espacial separado|planeta lunar dimensional|novo mundo sideral|dimensão de galáxias|mundo extra com tema espacial",
"dimension_infernal":"dimensão de magma e netherrack|novo mundo de lava|planeta infernal extra|dimensão com fogo e cinzas|mundo de rocha vulcânica|reino de calor extremo",
"dimension_generic":"dimensão independente|novo mundo com regras próprias|planeta sem tema específico|dimensão adicional para explorar|mundo separado personalizado|universo diferente no jogo",
"query_mods":"quais mods do Forge estão carregados|mostrar lista de mods atual|consulta dos mods instalados|imprimir os nomes dos mods|buscar modificações em execução|mods nesta instância",
"query_blocks":"mostrar nomes e IDs dos blocos|listar todos os blocos do registro|quais blocos posso usar|consultar registro de blocos|blocos adicionados por mods|pesquisar bloco pelo ID",
"query_items":"mostrar nomes e IDs dos itens|listar todos os itens do registro|quais itens posso usar|consultar registro de itens|itens adicionados por mods|pesquisar item pelo ID",
"query_entities":"mostrar nomes de entidades registradas|listar mobs instalados|quais criaturas existem no registro|consultar entidade pelo nome|entidades dos mods|ID de criatura",
"query_dimensions":"mostrar IDs das dimensões registradas|quais mundos extras estão disponíveis|consulta do registro dimensional|exibir dimensões criadas|buscar dimensão pelo ID|listar mundos separados",
"command_enter":"teleportar para dimensão 9|entrar no mundo dimensional 6|viajar para o mundo registrado|mover jogador para dimensão 10|ir à dimensão personalizada|visitar dimensão número 7",
"ask_help":"ensine os comandos do mod|quais tarefas essa IA executa|instruções para usar o bot|explique como criar blocos e itens|mostre recursos disponíveis|como solicitar construção",
"ambiguous":"faça algo interessante sem detalhes|não tenho ideia específica|escolha algo aleatório para criar|invente objeto sem especificação|realize criação surpresa|crie uma coisa qualquer",
"structure_house":"casa com telhado inclinado|casa de madeira com janelas|chalé de pedra para morar|construção residencial com entrada|abrigo com paredes e cobertura|moradia pequena com cômodos",
"structure_castle":"castelo com ponte levadiça|fortaleza com torres nos cantos|bastião medieval de pedra|castelo fortificado|castelo com ameias e portão|fortaleza com quatro torres",
"structure_tower":"torre de pedra com vários andares|estrutura em pé muito alta|torre com topo|torre de observação|edifício estreito na vertical|farol em formato de torre",
"structure_bridge":"passarela sobre água|ponte com dois pilares|viaduto que cruza um vale|passagem elevada entre margens|ponte de pedra com parapeito|estrutura para cruzar um rio",
"structure_city":"cidade com quarteirões|bairro com prédios e avenidas|cidade com ruas e casas|conjunto urbano de edifícios|vila organizada com estradas|metrópole pequena com quadras",
"structure_maze":"labirinto retangular de pedra|paredes formando um percurso|estrutura de corredores e becos|maze para explorar|labirinto com entrada e saída|caminhos complexos em paredes",
"terrain_plain":"planície lisa de terra|superfície plana de grama|terreno aberto sem casas|solo nivelado para construir|campo plano de blocos|área de terreno sem prédios",
"terrain_desert":"dunas de areia em relevo|terreno desértico ondulado|paisagem árida de arenito|solo arenoso com pequenas colinas|área de deserto sem construções|relevo natural de dunas",
"terrain_mountain":"relevo com montanhas altas|serra com picos e encostas|paisagem de vales rochosos|terreno acidentado com cumes|cordilheira de pedra|região montanhosa natural",
"terrain_snow":"relevo coberto de neve|paisagem congelada de inverno|terreno branco com ondulações|solo gelado e nevado|neve em terreno natural|área nevada sem edifícios",
"terrain_volcanic":"solo vulcânico escuro|relevo de rocha infernal|paisagem com montículos vulcânicos|terreno de cinza e netherrack|área de pedra vulcânica|solo irregular de vulcão",
"map_procedural":"mapa de aventura novo|nova região para explorar|mapa procedural com biomas|território inédito do mundo|terreno base de um mapa|região grande com relevo gerado",
"block_machine":"bloco computadorizado interativo|bloco tecnológico com circuito|máquina como bloco|bloco de controle eletrônico|bloco futurista que responde ao clique|cubo mecânico com função",
"block_corrupted":"bloco com energia corrupta|bloco infectado cheio de fissuras|bloco de contaminação roxa|matéria corrompida em forma de bloco|bloco sombrio de corrupção|bloco violeta com rachaduras",
"item_staff":"item de cajado mágico|bastão mágico no inventário|cajado usável que dá velocidade|varinha de feitiço como item|bastão encantado|cajado de energia para segurar",
"item_amulet":"talismã defensivo como item|amuleto usável pelo jogador|pingente que concede resistência|item mágico chamado amuleto|relíquia protetora no inventário|talismã de regeneração",
"item_dagger":"punhal curto para combate|adaga de metal como item|arma semelhante a faca|lâmina curta no inventário|adaga que pode ser segurada|punhal de pedra como arma"
}
for label, extra in EXTRA2.items():
    RAW[label] += "|" + extra
EXAMPLES = {key: list(dict.fromkeys(value.split("|"))) for key, value in RAW.items()}

def normalize(text):
    return "".join(ch for ch in unicodedata.normalize("NFKD", text.lower()) if not unicodedata.combining(ch))

def hash_bucket(text):
    value = 0
    for char in text:
        value = (31 * value + ord(char)) & 0xffffffff
    return (value & 0x7fffffff) % VOCABULARY

def feature_ids(text):
    words = re.findall(r"[a-z0-9]+", normalize(text))
    return np.asarray(sorted({hash_bucket(w) for w in words} | {hash_bucket(words[i] + " " + words[i+1]) for i in range(len(words)-1)}), dtype=np.int32)

def augment(text):
    return [text, "crie " + text, "por favor crie " + text, "eu quero " + text, "adicione ao mundo: " + text, "create " + text, text + " no Minecraft"]

def split_data():
    rng = random.Random(SEED)
    train_x, train_y, val_x, val_y, test_x, test_y = [], [], [], [], [], []
    for target, label in enumerate(CLASSES):
        phrases = list(EXAMPLES[label])
        rng.shuffle(phrases)
        n_test = max(2, len(phrases)//5)
        n_val = max(2, len(phrases)//5)
        test_phrases, val_phrases = phrases[:n_test], phrases[n_test:n_test+n_val]
        train_phrases = phrases[n_test+n_val:]
        for phrase in train_phrases:
            for sample in augment(phrase):
                train_x.append(feature_ids(sample)); train_y.append(target)
        test_x.extend(feature_ids(x) for x in test_phrases); test_y.extend([target]*len(test_phrases))
        val_x.extend(feature_ids(x) for x in val_phrases); val_y.extend([target]*len(val_phrases))
    order = list(range(len(train_x))); rng.shuffle(order)
    return ([train_x[i] for i in order], np.asarray([train_y[i] for i in order], np.int32),
            val_x, np.asarray(val_y, np.int32), test_x, np.asarray(test_y, np.int32))

def softmax(logits):
    v = np.exp(np.clip(logits-logits.max(axis=1, keepdims=True), -60.0, 0.0))
    return v / v.sum(axis=1, keepdims=True)

def forward(features, params):
    embed, bias, w1, b1, w2, b2 = params
    x = np.empty((len(features), EMBEDDING), np.float32)
    for i, ids in enumerate(features): x[i] = embed[ids].mean(axis=0)
    x += bias; z = x @ w1 + b1; hidden = np.maximum(z, 0.0)
    return x, z, hidden, hidden @ w2 + b2

def evaluate(features, labels, params):
    _, _, _, logits = forward(features, params)
    p = softmax(logits)
    loss = float(-np.log(np.maximum(p[np.arange(len(labels)), labels], 1e-9)).mean())
    return loss, np.argmax(logits, axis=1)

def metrics(labels, preds):
    matrix = np.zeros((OUTPUTS, OUTPUTS), np.int64)
    for actual, predicted in zip(labels, preds): matrix[int(actual), int(predicted)] += 1
    f1 = []
    for i in range(OUTPUTS):
        tp = int(matrix[i,i]); fp = int(matrix[:,i].sum()-tp); fn = int(matrix[i,:].sum()-tp)
        den = 2*tp+fp+fn; f1.append(0.0 if den == 0 else 2*tp/den)
    return {"accuracy": float(np.mean(labels == preds)), "macro_f1": float(np.mean(f1)),
            "confusion_matrix": matrix.tolist(), "per_class_f1": {CLASSES[i]: f1[i] for i in range(OUTPUTS)}}

def train():
    if set(EXAMPLES) != set(CLASSES): raise ValueError("Classifier classes and data do not match.")
    train_x, train_y, val_x, val_y, test_x, test_y = split_data()
    rng = np.random.default_rng(SEED)
    params = [rng.normal(0, .02, (VOCABULARY, EMBEDDING)).astype(np.float32), np.zeros(EMBEDDING, np.float32),
              rng.normal(0, .045, (EMBEDDING, HIDDEN)).astype(np.float32), np.zeros(HIDDEN, np.float32),
              rng.normal(0, .045, (HIDDEN, OUTPUTS)).astype(np.float32), np.zeros(OUTPUTS, np.float32)]
    m = [np.zeros_like(v) for v in params]; v = [np.zeros_like(x) for x in params]
    max_generations = max(1, int(os.getenv("REAI_MAX_EPOCHS", "500000")))
    time_budget = max(15, int(os.getenv("REAI_MAX_TRAIN_SECONDS", "150")))
    patience_limit, no_improvement, min_delta = 28, 0, .00005
    best_loss, best_params, best_gen = float("inf"), None, 0
    step, generations, stop_reason = 0, 0, "generation_budget"
    start_time, batch_size = time.monotonic(), 64
    for generation in range(max_generations):
        if time.monotonic() - start_time >= time_budget:
            stop_reason = "time_budget"; break
        order = rng.permutation(len(train_x))
        for start in range(0, len(order), batch_size):
            batch = order[start:start+batch_size]
            feats = [train_x[int(i)] for i in batch]; y = train_y[batch]
            x = np.empty((len(batch), EMBEDDING), np.float32)
            for row, ids in enumerate(feats): x[row] = params[0][ids].mean(axis=0)
            x += params[1]; z = x @ params[2] + params[3]; hidden = np.maximum(z, 0.0)
            dropout_mask = (rng.random(hidden.shape) >= 0.20).astype(np.float32) / 0.80
            hidden = hidden * dropout_mask
            p = softmax(hidden @ params[4] + params[5])
            gl = p.copy(); gl += .02/OUTPUTS; gl[np.arange(len(batch)), y] -= 1; gl /= len(batch)
            gw2 = hidden.T @ gl + .0001*params[4]; gb2 = gl.sum(axis=0)
            gh = (gl @ params[4].T) * dropout_mask; gz = gh * (z > 0); gw1 = x.T @ gz + .0001*params[2]; gb1 = gz.sum(axis=0)
            gx = gz @ params[2].T; gbias = gx.sum(axis=0); ge = np.zeros_like(params[0])
            for row, ids in enumerate(feats): np.add.at(ge, ids, gx[row]/max(1, len(ids)))
            grads = [ge, gbias, gw1, gb1, gw2, gb2]
            norm = np.sqrt(sum(float(np.sum(g*g)) for g in grads))
            if norm > 5: grads = [g*(5/norm) for g in grads]
            step += 1
            for i, (param, grad) in enumerate(zip(params, grads)):
                m[i] = .9*m[i] + .1*grad; v[i] = .999*v[i] + .001*grad*grad
                param -= .004*(m[i]/(1-.9**step))/(np.sqrt(v[i]/(1-.999**step))+1e-8)
        generations = generation + 1
        val_loss, val_pred = evaluate(val_x, val_y, params)
        if val_loss < best_loss - min_delta:
            best_loss, best_params, best_gen, no_improvement = val_loss, [p.copy() for p in params], generations, 0
        else: no_improvement += 1
        if generations == 1 or generations % 10 == 0:
            train_loss, _ = evaluate(train_x, train_y, params)
            print("generation", generations, "train_loss", round(train_loss,4),
                  "validation_loss", round(val_loss,4), "validation_accuracy", round(float(np.mean(val_pred==val_y)),4))
        if no_improvement >= patience_limit:
            stop_reason = "validation_plateau"; break
    if best_params is None: best_params, best_gen, best_loss = params, generations, evaluate(val_x,val_y,params)[0]
    params = best_params
    train_loss, train_pred = evaluate(train_x,train_y,params); val_loss,val_pred=evaluate(val_x,val_y,params); test_loss,test_pred=evaluate(test_x,test_y,params)
    train_m,val_m,test_m=metrics(train_y,train_pred),metrics(val_y,val_pred),metrics(test_y,test_pred)
    weights=np.concatenate([p.astype("<f4",copy=False).ravel() for p in params])
    if len(weights)!=PARAMETER_COUNT: raise AssertionError("Parameter count mismatch: "+str(len(weights)))
    path=ROOT/"weights.bin"
    with path.open("wb") as out: out.write(b"REAI300K2"); weights.tofile(out)
    report={"model":"Reality Engine AI Minecraft 1.7.10 intent classifier",
      "architecture":{"vocabulary_buckets":VOCABULARY,"embedding_width":EMBEDDING,"hidden_width":HIDDEN,"output_classes":OUTPUTS,"scalar_parameters":int(len(weights))},
      "dataset":{"source":"curated project-specific prompt corpus","base_prompts":sum(len(v) for v in EXAMPLES.values()),
        "training_utterances_augmented":len(train_x),"validation_prompts":len(val_x),"test_prompts":len(test_x),
        "split_rule":"distinct base prompts split before augmentation"},
      "training":{"generation_budget_requested":max_generations,"time_budget_seconds":time_budget,"generations_executed":generations,
        "best_validation_generation":best_gen,"optimizer":"Adam with gradient clipping, weight decay and label smoothing",
        "early_stopping_patience":patience_limit,"stop_reason":stop_reason},
      "metrics":{"train_loss":train_loss,"validation_loss":val_loss,"test_loss":test_loss,"train_accuracy":train_m["accuracy"],
        "validation_accuracy":val_m["accuracy"],"test_accuracy":test_m["accuracy"],"test_macro_f1":test_m["macro_f1"],
        "class_labels":CLASSES,"per_class_f1":test_m["per_class_f1"],"test_confusion_matrix":test_m["confusion_matrix"]},
      "limits":["This compact classifier is not a general-purpose language model.",
        "Training loss is not forced to zero; held-out metrics select a checkpoint.",
        "Online research is stored with sources and does not silently alter neural weights."],
      "weights_file_bytes":path.stat().st_size}
    (ROOT/"training_report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps({"parameter_count":len(weights),"base_prompts":report["dataset"]["base_prompts"],
      "training_utterances":len(train_x),"validation_accuracy":round(val_m["accuracy"],4),
      "test_accuracy":round(test_m["accuracy"],4),"test_macro_f1":round(test_m["macro_f1"],4),
      "generations":generations,"stop_reason":stop_reason,"weights_file_bytes":path.stat().st_size}))
    if path.stat().st_size != 9+PARAMETER_COUNT*4 or OUTPUTS != len(CLASSES): raise AssertionError("Invalid model file layout")

if __name__ == "__main__": train()
