package br.com.realityengineai;

import java.text.Normalizer;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class CreationPlan {
    public static final String ENTITY="entity", BLOCK="block", ITEM="item", DIMENSION="dimension";
    public static final String STRUCTURE="structure", TERRAIN="terrain", MAP="map", QUERY="query", AMBIGUOUS="ambiguous";
    public final String kind, archetype, behavior, query;
    public final int radius;
    public final float confidence;
    private static final Pattern WORDS=Pattern.compile("[a-z0-9]+");
    private static final Pattern RADIUS=Pattern.compile("(?:raio\\s*(\\d+)|(\\d+)\\s*blocos)");
    private static final Pattern LEADING_COMMAND=Pattern.compile("^\\s*crie\\s+");

    private CreationPlan(String k,String a,String b,String q,int r,float c) {
        kind=k; archetype=a; behavior=b; query=q==null?"":q.trim(); radius=r; confidence=c;
    }

    public static CreationPlan resolve(String input) {
        String raw=input==null?"":input.trim();
        String v=normalize(LEADING_COMMAND.matcher(raw).replaceFirst("")).replaceAll("^[,.:;! ]+","").trim();
        if(v.isEmpty()) return ambiguous("empty");

        if(contains(v,"pesquise na internet","pesquisar na internet","pesquise online","pesquisar online","estude na internet",
                "aprenda na internet","investigue na internet","busque na internet","pesquise sobre","pesquisar sobre","deep research"))
            return plan(QUERY,"internet_research","retrieve_and_store_sources",extractResearchQuery(v),0,1.0F);
        if(contains(v,"lista de mods","mods instalados","mods carregados","quais mods","catalogo de mods","liste os mods"))
            return plan(QUERY,"query_mods","none","",0,1.0F);
        if(contains(v,"blocos registrados","listar blocos","catalogo de blocos","liste os blocos","itens registrados","listar itens","catalogo de itens"))
            return plan(QUERY,"query_registry","none","",0,1.0F);
        if(contains(v,"buscar registro","procure no mod","buscar item do mod","buscar bloco do mod"))
            return plan(QUERY,"query_registry_search","none",extractRegistryQuery(v),0,1.0F);
        if(contains(v,"entrar na dimensao","ir para dimensao","entrar dimensao","teleportar para dimensao","ir para a dimensao"))
            return plan(QUERY,"enter_dimension","none",v,0,1.0F);
        if(contains(v,"ajuda","o que sabe fazer","comandos","capacidades","como funciona"))
            return plan(QUERY,"help","none","",0,1.0F);

        if(isMapPrompt(v)) return plan(MAP,"procedural","generate_world_region",v,parseRadius(v,16),0.99F);
        if(has(v,"dimensao","dimensoes","planeta","universo","mundo","world")||contains(v,"mundo novo","new world")) {
            if(contains(v,"deserto","areia","duna")) return plan(DIMENSION,"desert","vanilla_terrain","",0,0.99F);
            if(contains(v,"neve","gelo","frio","congelado")) return plan(DIMENSION,"cold","vanilla_terrain","",0,0.99F);
            if(contains(v,"floresta","arvore","selva")) return plan(DIMENSION,"forest","vanilla_terrain","",0,0.99F);
            if(contains(v,"espaco","vazio","galaxia","estrela")) return plan(DIMENSION,"space","vanilla_terrain","",0,0.99F);
            if(contains(v,"infernal","lava","fogo","vulcao")) return plan(DIMENSION,"infernal","vanilla_terrain","",0,0.99F);
            return plan(DIMENSION,"generic","vanilla_terrain","",0,0.96F);
        }

        boolean explicitBlock=contains(v,"como bloco","em bloco","em forma de bloco","bloco de","bloco chamado","bloco personalizado","bloco que","um bloco","novo bloco","custom block");
        boolean explicitItem=contains(v,"como item","em forma de item","item chamado")
            ||has(v,"espada","sabre","katana","lamina","picareta","machado","ferramenta","comida","pao","fruta","alimento","carne","amuleto","varinha","cajado","bastao","adaga","punhal","armadura","capacete","item","artefato","objeto");
        if(explicitItem&&!contains(v,"como bloco","em forma de bloco")) {
            if(has(v,"espada","sabre","katana","lamina")) return plan(ITEM,"sword","melee","",0,0.99F);
            if(has(v,"picareta","machado","ferramenta")) return plan(ITEM,"tool","tool","",0,0.99F);
            if(has(v,"comida","pao","fruta","alimento","carne")) return plan(ITEM,"food","edible","",0,0.99F);
            if(has(v,"adaga","punhal","dagger")) return plan(ITEM,"dagger","melee","",0,0.99F);
            if(has(v,"cajado","bastao","varinha","staff")) return plan(ITEM,"staff","right_click_spell","",0,0.99F);
            if(contains(v,"artefato chamado amuleto","artefato chamado de amuleto")) return plan(ITEM,"artifact","recognized_effects_only","",0,0.92F);
            if(has(v,"amuleto","talism","amulet")) return plan(ITEM,"amulet","right_click_protection","",0,0.99F);
            return plan(ITEM,"artifact","recognized_effects_only","",0,0.92F);
        }

        boolean entity=has(v,"entidade","mob","criatura","npc","personagem","ser vivo")||contains(v,"como entidade","como mob","como criatura");
        boolean corruption=has(v,"corrompe","corromper","corrompendo","corrompida","corrompido","infecta","infectar","contamina","contaminar","transforma","transformar","corruptor","corruption");
        boolean nearby=has(v,"bloco","blocos","construcao","construcoes","terreno");
        if(entity) {
            if(corruption&&nearby) return plan(ENTITY,"corruptor","corrupt_nearby_blocks","",parseCorruptRadius(v),1.0F);
            if(has(v,"carro","veiculo","automovel","caminhao","moto","motocicleta","bicicleta","onibus","tanque")) return plan(ENTITY,"car","vehicle","",0,0.99F);
            if(has(v,"dragao")) return plan(ENTITY,"dragon","basic_ai","",0,0.99F);
            if(has(v,"hostil","agressivo","agressiva","inimigo","inimiga","boss","ataca","atacar")) return plan(ENTITY,"hostile_creature","hostile_ai","",0,0.98F);
            return plan(ENTITY,"creature","basic_ai","",0,0.96F);
        }
        if(explicitBlock) {
            if(contains(v,"cristal","cristalino","cristalina","ametista")) return plan(BLOCK,"crystal","emissive","",0,0.99F);
            if(contains(v,"maquina em bloco") && !contains(v,"bloco de maquina","bloco de tecnologia","bloco tecnologico","bloco de circuito","bloco de computador")) return plan(BLOCK,"generic","limited_interaction","",0,0.92F);
            if(contains(v,"bloco de maquina","bloco de tecnologia","bloco tecnologico","bloco de circuito","bloco de computador","redstone")) return plan(BLOCK,"machine","interactive_tech_block","",0,0.98F);
            if(contains(v,"corrompido","corrompida","corrupto","corrupta","infectado","infectada")) return plan(BLOCK,"corrupted","corruption_block","",0,0.98F);
            return plan(BLOCK,"generic","limited_interaction","",0,0.92F);
        }

        if(has(v,"carro","carros","veiculo","veiculos","automovel","automoveis","caminhao","caminhoes","moto","motocicleta","bicicleta","onibus","tanque"))
            return plan(ENTITY,"car","vehicle","",0,0.94F);
        if(has(v,"dragao")) return plan(ENTITY,"dragon","basic_ai","",0,0.92F);
        if(has(v,"hostil","agressivo","boss","monstro","zumbi")) return plan(ENTITY,"hostile_creature","hostile_ai","",0,0.89F);

        if(isMapPrompt(v)) return plan(MAP,"procedural","generate_world_region",v,parseRadius(v,16),0.99F);
        if(isTerrainPrompt(v)) {
            if(contains(v,"deserto","desertico","areia","duna")) return plan(TERRAIN,"desert","generate_terrain",v,parseRadius(v,12),0.98F);
            if(contains(v,"neve","gelo","congelado","snow","ice")) return plan(TERRAIN,"snow","generate_terrain",v,parseRadius(v,12),0.98F);
            if(contains(v,"montanha","montanhoso","serra","cordilheira","mountain")) return plan(TERRAIN,"mountain","generate_terrain",v,parseRadius(v,12),0.98F);
            if(contains(v,"vulcao","lava","infernal","nether")) return plan(TERRAIN,"volcanic","generate_terrain",v,parseRadius(v,12),0.98F);
            return plan(TERRAIN,"plain","generate_terrain",v,parseRadius(v,12),0.93F);
        }
        if(explicitStructure(v)) {
            if(contains(v,"casa","house","garagem")) return plan(STRUCTURE,"house","build_structure",v,0,0.99F);
            if(contains(v,"castelo","fortaleza","castle")) return plan(STRUCTURE,"castle","build_structure",v,0,0.99F);
            if(contains(v,"torre","tower")) return plan(STRUCTURE,"tower","build_structure",v,0,0.99F);
            if(contains(v,"ponte","bridge")) return plan(STRUCTURE,"bridge","build_structure",v,0,0.99F);
            if(contains(v,"cidade","city")) return plan(STRUCTURE,"city","build_structure",v,0,0.99F);
            if(contains(v,"labirinto","maze")) return plan(STRUCTURE,"maze","build_structure",v,0,0.99F);
            if(contains(v,"computador","computer","pc")) return plan(STRUCTURE,"computer","build_structure",v,0,0.96F);
            if(contains(v,"carro","veiculo","nave","aviao")) return plan(STRUCTURE,"vehicle","build_structure",v,0,0.92F);
            return plan(STRUCTURE,"generic","build_structure",v,0,0.88F);
        }

        OfflineBrain brain=RealityEngineAI.BRAIN;
        OfflineBrain.Prediction prediction=brain==null?new OfflineBrain.Prediction("ambiguous",0.0F):brain.predictDetailed(raw);
        if(prediction!=null&&prediction.confidence>=0.38F) {
            CreationPlan learned=fromModelLabel(prediction.label,prediction.confidence,v);
            if(learned!=null) return learned;
        }
        return ambiguous("type_not_explicit");
    }

    private static CreationPlan fromModelLabel(String label,float confidence,String value) {
        if(label==null) return null;
        if(label.startsWith("structure_")) return plan(STRUCTURE,label.substring(10),"build_structure",value,0,confidence);
        if(label.startsWith("terrain_")) return plan(TERRAIN,label.substring(8),"generate_terrain",value,parseRadius(value,12),confidence);
        if("map_procedural".equals(label)) return plan(MAP,"procedural","generate_world_region",value,parseRadius(value,16),confidence);
        if("block_machine".equals(label)) return plan(BLOCK,"machine","interactive_tech_block","",0,confidence);
        if("block_corrupted".equals(label)) return plan(BLOCK,"corrupted","corruption_block","",0,confidence);
        if("block_crystal".equals(label)) return plan(BLOCK,"crystal","emissive","",0,confidence);
        if("block_generic".equals(label)) return plan(BLOCK,"generic","limited_interaction","",0,confidence);
        if("item_staff".equals(label)) return plan(ITEM,"staff","right_click_spell","",0,confidence);
        if("item_amulet".equals(label)) return plan(ITEM,"amulet","right_click_protection","",0,confidence);
        if("item_dagger".equals(label)) return plan(ITEM,"dagger","melee","",0,confidence);
        if("item_sword".equals(label)) return plan(ITEM,"sword","melee","",0,confidence);
        if("item_tool".equals(label)) return plan(ITEM,"tool","tool","",0,confidence);
        if("item_food".equals(label)) return plan(ITEM,"food","edible","",0,confidence);
        if("item_generic".equals(label)) return plan(ITEM,"artifact","recognized_effects_only","",0,confidence);
        if("entity_car".equals(label)) return plan(ENTITY,"car","vehicle","",0,confidence);
        if("entity_dragon".equals(label)) return plan(ENTITY,"dragon","basic_ai","",0,confidence);
        if("entity_hostile".equals(label)) return plan(ENTITY,"hostile_creature","hostile_ai","",0,confidence);
        if("entity_creature".equals(label)) return plan(ENTITY,"creature","basic_ai","",0,confidence);
        if(label.startsWith("dimension_")) return plan(DIMENSION,label.substring(10),"vanilla_terrain","",0,confidence);
        if("query_mods".equals(label)) return plan(QUERY,"query_mods","none","",0,confidence);
        if("query_blocks".equals(label)||"query_items".equals(label)) return plan(QUERY,"query_registry","none","",0,confidence);
        if("query_entities".equals(label)) return plan(QUERY,"query_entities","none","",0,confidence);
        if("query_dimensions".equals(label)) return plan(QUERY,"query_dimensions","none","",0,confidence);
        if("command_enter".equals(label)) return plan(QUERY,"enter_dimension","none",value,0,confidence);
        if("ask_help".equals(label)) return plan(QUERY,"help","none","",0,confidence);
        return null;
    }

    private static boolean explicitStructure(String v) {
        if(contains(v,"construcao","construcoes","estrutura","estruturas","edificio","construa","construir","arquitetura","build a structure")) return true;
        if(has(v,"casa","casas","castelo","castelos","fortaleza","torre","ponte","cidade","labirinto","arena","garagem","templo","piramide","muro","base","arranha")) return true;
        return has(v,"computador","computer","pc")&&!contains(v,"como bloco","em bloco","em forma de bloco","como item");
    }

    private static boolean isMapPrompt(String v) {
        return contains(v,"mapa","mapas","map do zero","mundo do zero","novo mundo","new world","continente","ilha grande","world map","generate a map","create a map");
    }

    private static boolean isTerrainPrompt(String v) {
        return contains(v,"terreno","terrenos","paisagem","paisagens","bioma","biomas","planicie","montanha","montanhoso","serra",
            "cordilheira","deserto","dunas","solo nevado","terreno nevado","terreno vulcanico","terrain","landscape","mountain range");
    }

    public boolean isCreation() {
        return ENTITY.equals(kind)||BLOCK.equals(kind)||ITEM.equals(kind)||DIMENSION.equals(kind)||STRUCTURE.equals(kind)||TERRAIN.equals(kind)||MAP.equals(kind);
    }

    private static CreationPlan plan(String k,String a,String b,String q,int r,float c) { return new CreationPlan(k,a,b,q,r,c); }
    private static CreationPlan ambiguous(String a) { return plan(AMBIGUOUS,a,"none","",0,0.0F); }

    public static String normalize(String value) {
        String normalized=Normalizer.normalize(value==null?"":value.toLowerCase(Locale.ROOT),Normalizer.Form.NFD);
        return normalized.replaceAll("\\p{M}","").replace('ё','e');
    }

    private static boolean has(String value,String... words) {
        Matcher matcher=WORDS.matcher(value);
        Set<String> found=new HashSet<String>();
        while(matcher.find()) found.add(matcher.group());
        for(String word:words) {
            String normalized=normalize(word);
            if(normalized.indexOf(' ')>=0) { if(value.contains(normalized)) return true; }
            else if(found.contains(normalized)) return true;
        }
        return false;
    }

    private static boolean contains(String value,String... values) {
        for(String option:values) if(value.contains(normalize(option))) return true;
        return false;
    }

    private static int parseCorruptRadius(String value) {
        Matcher matcher=RADIUS.matcher(value);
        if(matcher.find()) {
            String digits=matcher.group(1)==null?matcher.group(2):matcher.group(1);
            try { return Math.max(1,Math.min(6,Integer.parseInt(digits))); }
            catch(NumberFormatException ignored) { return 3; }
        }
        return 3;
    }

    private static int parseRadius(String value) { return parseRadius(value,16); }
    private static int parseRadius(String value,int fallback) {
        Matcher matcher=RADIUS.matcher(value);
        if(matcher.find()) {
            String digits=matcher.group(1)==null?matcher.group(2):matcher.group(1);
            try { return Math.max(4,Math.min(64,Integer.parseInt(digits))); }
            catch(NumberFormatException ignored) { return fallback; }
        }
        return fallback;
    }

    private static String extractResearchQuery(String value) {
        String[] prefixes={"pesquise na internet sobre","pesquisar na internet sobre","pesquise online sobre","pesquisar online sobre",
            "estude na internet sobre","aprenda na internet sobre","investigue na internet sobre","busque na internet sobre","pesquise sobre","pesquisar sobre","deep research"};
        for(String prefix:prefixes) {
            String n=normalize(prefix); int i=value.indexOf(n);
            if(i>=0) return trim(value.substring(i+n.length()),240);
        }
        return trim(value,240);
    }

    private static String extractRegistryQuery(String value) {
        String[] prefixes={"buscar registro","procure no mod","buscar item do mod","buscar bloco do mod"};
        for(String prefix:prefixes) { int i=value.indexOf(prefix); if(i>=0) return value.substring(i+prefix.length()).trim(); }
        return value;
    }

    private static String trim(String value,int limit) {
        String result=value==null?"":value.trim();
        return result.length()>limit?result.substring(0,limit):result;
    }
}
