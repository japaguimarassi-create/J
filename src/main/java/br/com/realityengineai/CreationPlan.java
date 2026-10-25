package br.com.realityengineai;

import java.text.Normalizer;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class CreationPlan {
    public static final String ENTITY = "entity";
    public static final String BLOCK = "block";
    public static final String ITEM = "item";
    public static final String DIMENSION = "dimension";
    public static final String QUERY = "query";
    public static final String AMBIGUOUS = "ambiguous";

    public final String kind;
    public final String archetype;
    public final String behavior;
    public final String query;
    public final int radius;
    public final float confidence;

    private static final Pattern WORDS = Pattern.compile("[a-z0-9]+");
    private static final Pattern RADIUS = Pattern.compile("(?:raio\\s*(\\d+)|(\\d+)\\s*blocos)");
    private static final Pattern LEADING_COMMAND = Pattern.compile("^\\s*crie\\s+");

    private CreationPlan(String kind, String archetype, String behavior, String query, int radius, float confidence) {
        this.kind = kind;
        this.archetype = archetype;
        this.behavior = behavior;
        this.query = query == null ? "" : query.trim();
        this.radius = radius;
        this.confidence = confidence;
    }

    public static CreationPlan resolve(String input) {
        String raw = input == null ? "" : input.trim();
        String normalized = normalize(raw);
        normalized = LEADING_COMMAND.matcher(normalized).replaceFirst("").trim();
        if (normalized.isEmpty()) {
            return ambiguous("empty", "none", 0.0F);
        }

        if (containsAny(normalized, "pesquise na internet", "pesquisar na internet", "pesquise online",
                "pesquisar online", "estude na internet", "aprenda na internet", "investigue na internet",
                "busque na internet", "pesquise sobre")) {
            return plan(QUERY, "internet_research", "learn", extractResearchQuery(normalized), 0, 1.0F);
        }
        if (containsAny(normalized, "lista de mods", "mods instalados", "mods carregados", "quais mods",
                "catalogo de mods", "liste os mods")) {
            return plan(QUERY, "query_mods", "none", "", 0, 1.0F);
        }
        if (containsAny(normalized, "blocos registrados", "listar blocos", "catalogo de blocos", "liste os blocos",
                "itens registrados", "listar itens", "catalogo de itens")) {
            return plan(QUERY, "query_registry", "none", "", 0, 1.0F);
        }
        if (containsAny(normalized, "buscar registro", "procure no mod", "buscar item do mod", "buscar bloco do mod")) {
            return plan(QUERY, "query_registry_search", "none", extractRegistryQuery(normalized), 0, 1.0F);
        }
        if (containsAny(normalized, "entrar na dimensao", "ir para dimensao", "entrar dimensao",
                "teleportar para dimensao", "ir para a dimensao")) {
            return plan(QUERY, "enter_dimension", "none", normalized, 0, 1.0F);
        }
        if (containsAny(normalized, "ajuda", "o que sabe fazer", "comandos", "capacidades", "como funciona")) {
            return plan(QUERY, "help", "none", "", 0, 1.0F);
        }

        boolean entityMarker = hasWord(normalized, "entidade", "entidade", "mob", "criatura", "ser vivo", "veiculo", "automovel");
        boolean vehicle = hasWord(normalized, "carro", "carros", "veiculo", "veiculos", "automovel", "automoveis",
                "caminhao", "caminhoes", "moto", "motocicleta", "bicicleta", "onibus", "tanque");
        boolean corruptionAction = hasWord(normalized, "corrompe", "corromper", "corrompendo", "corrompida",
                "corrompido", "infecta", "infectar", "contamina", "contaminar", "corruptor", "corruption");
        boolean nearbyBlocks = hasWord(normalized, "bloco", "blocos", "construcoes", "construcao", "terreno");
        boolean entityAction = hasWord(normalized, "ataca", "atacar", "persegue", "perseguir", "voa", "voar",
                "dirigivel", "dirige", "dirigir", "montavel", "pilotavel", "dirigivel");

        boolean explicitEntity = entityMarker || hasWord(normalized, "entidade", "mob", "criatura", "dragao", "monstro", "boss");
        boolean explicitItem = hasWord(normalized, "item", "objeto", "artefato", "inventario")
                || containsAny(normalized, "como item", "em forma de item", "item chamado");
        boolean explicitBlock = containsAny(normalized, "como bloco", "em bloco", "bloco de", "bloco chamado",
                "bloco personalizado", "bloco que");
        boolean explicitDimension = hasWord(normalized, "dimensao", "planeta", "universo") || containsAny(normalized, "mundo novo");

        if (explicitEntity || (vehicle && !explicitItem && !explicitBlock)
                || (corruptionAction && nearbyBlocks && hasWord(normalized, "que", "entidade", "criatura", "mob", "monstro"))) {
            if (corruptionAction && nearbyBlocks) {
                return plan(ENTITY, "corruptor", "corrupt_nearby_blocks", "", parseRadius(normalized), 1.0F);
            }
            if (vehicle) {
                return plan(ENTITY, "car", "vehicle", "", 0, 1.0F);
            }
            if (hasWord(normalized, "dragao")) {
                return plan(ENTITY, "dragon", "basic_ai", "", 0, 1.0F);
            }
            if (hasWord(normalized, "hostil", "agressivo", "agressiva", "inimigo", "inimiga", "boss", "ataca", "atacar")) {
                return plan(ENTITY, "hostile_creature", "hostile_ai", "", 0, 0.98F);
            }
            return plan(ENTITY, "creature", entityAction ? "basic_ai" : "basic_ai", "", 0, 0.96F);
        }

        if (explicitDimension) {
            if (containsAny(normalized, "deserto", "areia", "duna")) {
                return plan(DIMENSION, "desert", "vanilla_terrain", "", 0, 0.99F);
            }
            if (containsAny(normalized, "neve", "gelo", "frio", "congelado")) {
                return plan(DIMENSION, "cold", "vanilla_terrain", "", 0, 0.99F);
            }
            if (containsAny(normalized, "floresta", "arvore", "selva")) {
                return plan(DIMENSION, "forest", "vanilla_terrain", "", 0, 0.99F);
            }
            if (containsAny(normalized, "espaco", "vazio", "galaxia", "estrela")) {
                return plan(DIMENSION, "space", "vanilla_terrain", "", 0, 0.99F);
            }
            if (containsAny(normalized, "infernal", "lava", "fogo", "vulcao")) {
                return plan(DIMENSION, "infernal", "vanilla_terrain", "", 0, 0.99F);
            }
            return plan(DIMENSION, "generic", "vanilla_terrain", "", 0, 0.95F);
        }

        if (explicitItem) {
            if (hasWord(normalized, "espada", "sabre", "katana", "lamina")) {
                return plan(ITEM, "sword", "melee", "", 0, 0.99F);
            }
            if (hasWord(normalized, "picareta", "machado", "ferramenta")) {
                return plan(ITEM, "tool", "tool", "", 0, 0.99F);
            }
            if (hasWord(normalized, "comida", "pao", "fruta", "alimento", "carne")) {
                return plan(ITEM, "food", "edible", "", 0, 0.99F);
            }
            return plan(ITEM, "artifact", "recognized_effects_only", "", 0, 0.90F);
        }

        if (explicitBlock) {
            if (containsAny(normalized, "computador", "computer")) {
                return ambiguous("computer_prototype_removed", "none", 0.2F);
            }
            if (containsAny(normalized, "cristal", "cristalino", "cristalina")) {
                return plan(BLOCK, "crystal", "emissive", "", 0, 0.99F);
            }
            return plan(BLOCK, "generic", "limited_interaction", "", 0, 0.90F);
        }

        if (vehicle || hasWord(normalized, "carro", "veiculo", "automovel", "caminhao", "moto")) {
            return plan(ENTITY, "car", "vehicle", "", 0, 0.95F);
        }
        if (explicitDimension) {
            return plan(DIMENSION, "generic", "vanilla_terrain", "", 0, 0.95F);
        }

        if (hasWord(normalized, "espada", "sabre", "katana", "lamina")) {
            return plan(ITEM, "sword", "melee", "", 0, 0.95F);
        }
        if (hasWord(normalized, "picareta", "machado", "ferramenta")) {
            return plan(ITEM, "tool", "tool", "", 0, 0.95F);
        }
        if (hasWord(normalized, "comida", "pao", "fruta", "alimento", "carne")) {
            return plan(ITEM, "food", "edible", "", 0, 0.95F);
        }
        if (containsAny(normalized, "dragao")) {
            return plan(ENTITY, "dragon", "basic_ai", "", 0, 0.90F);
        }

        if (corruptionAction && nearbyBlocks) {
            return ambiguous("missing_entity_or_block_type", "none", 0.25F);
        }
        return ambiguous("type_not_explicit", "none", 0.0F);
    }

    public boolean isCreation() {
        return ENTITY.equals(kind) || BLOCK.equals(kind) || ITEM.equals(kind) || DIMENSION.equals(kind);
    }

    private static CreationPlan plan(String kind, String archetype, String behavior, String query, int radius, float confidence) {
        return new CreationPlan(kind, archetype, behavior, query, radius, confidence);
    }

    private static CreationPlan ambiguous(String archetype, String behavior, float confidence) {
        return plan(AMBIGUOUS, archetype, behavior, "", 0, confidence);
    }

    public static String normalize(String value) {
        String normalized = Normalizer.normalize(value == null ? "" : value.toLowerCase(Locale.ROOT), Normalizer.Form.NFD);
        return normalized.replaceAll("\\p{M}", "").replace('ё', 'e');
    }

    private static boolean hasWord(String value, String... words) {
        Matcher matcher = WORDS.matcher(value);
        java.util.HashSet<String> found = new java.util.HashSet<String>();
        while (matcher.find()) {
            found.add(matcher.group());
        }
        for (String word : words) {
            if (word.indexOf(' ') >= 0) {
                if (value.contains(word)) {
                    return true;
                }
            } else if (found.contains(word)) {
                return true;
            }
        }
        return false;
    }

    private static boolean containsAny(String value, String... options) {
        for (String option : options) {
            if (value.contains(option)) {
                return true;
            }
        }
        return false;
    }

    private static int parseRadius(String value) {
        Matcher matcher = RADIUS.matcher(value);
        if (matcher.find()) {
            String digits = matcher.group(1) == null ? matcher.group(2) : matcher.group(1);
            try {
                return Math.max(1, Math.min(6, Integer.parseInt(digits)));
            } catch (NumberFormatException ignored) {
                return 3;
            }
        }
        return 3;
    }

    private static String extractResearchQuery(String value) {
        String query = value;
        String[] prefixes = {"pesquise na internet sobre", "pesquisar na internet sobre", "pesquise online sobre",
            "pesquisar online sobre", "estude na internet sobre", "aprenda na internet sobre",
            "investigue na internet sobre", "busque na internet sobre", "pesquise sobre"};
        for (String prefix : prefixes) {
            int index = query.indexOf(prefix);
            if (index >= 0) {
                query = query.substring(index + prefix.length()).trim();
                break;
            }
        }
        return query.length() > 240 ? query.substring(0, 240) : query;
    }

    private static String extractRegistryQuery(String value) {
        int index = value.indexOf("buscar registro");
        if (index >= 0) {
            return value.substring(index + "buscar registro".length()).trim();
        }
        index = value.indexOf("procure no mod");
        if (index >= 0) {
            return value.substring(index + "procure no mod".length()).trim();
        }
        return value;
    }
}
