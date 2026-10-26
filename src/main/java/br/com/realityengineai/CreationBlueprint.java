package br.com.realityengineai;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class CreationBlueprint {
    public final String fullPrompt;
    public final String kind;
    public final String archetype;
    public final String objectName;
    public final String purpose;
    public final String material;
    public final String effects;
    private final List<String> effectList;

    private static final String[] EFFECTS = {
        "cura", "cura", "heal", "heal",
        "velocidade", "speed", "strength", "forca",
        "resistance", "resistencia", "protecao", "escudo",
        "regeneration", "regeneracao", "regenera", "regenerar",
        "jump", "pulo", "saltar", "salto",
        "fire_resistance", "resistencia ao fogo", "protecao contra fogo",
        "night_vision", "visao noturna", "enxergar no escuro",
        "water_breathing", "respirar debaixo d'agua", "respiracao aquatica",
        "invisibility", "invisibilidade", "ficar invisivel",
        "mining_speed", "mineracao rapida", "minerar mais rapido", "velocidade de mineracao",
        "fire_attack", "fogo", "chamas", "incendiar", "queimar", "queima",
        "freeze_attack", "gelo", "congelar", "congela", "congelamento",
        "poison_attack", "veneno", "envenenar", "envenena",
        "knockback", "repulsao", "empurrar", "arremessar",
        "lightning_attack", "raio", "relampago", "eletricidade",
        "teleport", "teleportar", "teletransporte", "teleporte",
        "explosion", "explodir", "explosao",
        "flight", "voar", "voo",
        "corruption", "corromper", "corrompe", "infectar", "contaminar",
        "projectile", "disparar projeteis", "lancar projeteis", "atira"
    };

    private CreationBlueprint(String prompt, CreationPlan plan, String name, String purpose, String material, List<String> inferredEffects) {
        fullPrompt = prompt == null ? "" : prompt.trim();
        kind = plan == null ? CreationPlan.AMBIGUOUS : plan.kind;
        archetype = plan == null ? "unknown" : plan.archetype;
        objectName = name;
        this.purpose = purpose;
        this.material = material;
        effectList = Collections.unmodifiableList(new ArrayList<String>(inferredEffects));
        effects = join(inferredEffects);
    }

    public static CreationBlueprint parse(String prompt) {
        return parse(prompt, CreationPlan.resolve(prompt));
    }

    public static CreationBlueprint parse(String prompt, CreationPlan plan) {
        String full = prompt == null ? "" : prompt.trim();
        String normalized = CreationPlan.normalize(full);
        String request = normalized.replaceFirst("^crie\\s+", "");
        request = request.replaceAll("\\b(por favor|por gentileza|no minecraft|dentro do jogo|no meu mundo|agora|imediatamente|para mim)\\b", " ");
        request = request.replaceAll("[,;:!?.]+$", "").replaceAll("\\s+", " ").trim();
        String rawRequest = full.replaceFirst("(?i)^crie\\s+", "");
        rawRequest = rawRequest.replaceAll("(?i)\\b(por favor|por gentileza|no minecraft|dentro do jogo|no meu mundo|agora|imediatamente|para mim)\\b", " ");
        rawRequest = rawRequest.replaceAll("[,;:!?.]+$", "").replaceAll("\\s+", " ").trim();

        int boundary = findPurposeBoundary(request);
        String namePart = boundary >= 0 ? rawRequest.substring(0, Math.min(boundary, rawRequest.length())).trim() : rawRequest;
        String purpose = boundary >= 0 ? cleanPurpose(request.substring(boundary).trim()) : "";
        namePart = namePart.replaceFirst("^(um|uma|o|a|os|as|novo|nova|novos|novas)\\s+", "");
        namePart = namePart.replaceFirst("^(item chamado|objeto chamado|artefato chamado|bloco chamado|entidade chamada|criatura chamada)\\s+", "");
        namePart = namePart.replaceAll("\\s+", " ").replaceAll("^[,;:. -]+|[,;:. -]+$", "").trim();
        if (namePart.isEmpty()) namePart = defaultName(plan);
        String name = titleCase(namePart);
        if (name.length() > 56) name = name.substring(0, 53).trim() + "...";

        String material = inferMaterial(request);
        List<String> effects = inferEffects(normalized);
        if (purpose.isEmpty() && !effects.isEmpty()) purpose = describeEffects(effects);
        if (purpose.length() > 240) purpose = purpose.substring(0, 240);
        return new CreationBlueprint(full, plan, name, purpose, material, effects);
    }

    public boolean hasEffect(String effect) {
        return effect != null && effectList.contains(effect);
    }

    public List<String> getEffects() {
        return effectList;
    }

    public String getEffectSummary() {
        return describeEffects(effectList);
    }

    public static String join(List<String> values) {
        StringBuilder result = new StringBuilder();
        if (values == null) return "";
        for (String value : values) {
            if (value == null || value.isEmpty()) continue;
            if (result.length() > 0) result.append(',');
            result.append(value);
        }
        return result.toString();
    }

    private static int findPurposeBoundary(String text) {
        String[] markers = {
            " com a capacidade de ", " com capacidade de ", " com habilidade de ", " com poder de ",
            " com efeito de ", " feita para ", " feito para ", " usada para ", " usado para ",
            " capaz de ", " que pode ", " que consegue ", " que causa ", " que dispara ",
            " que cura ", " e que ", " que ", " para ", " e cura ", " e regenera ",
            " e protege ", " e aumenta ", " e reduz ", " e concede ", " e aplica ",
            " e dispara ", " e congela ", " e queima ", " e envenena ", " e teleporta ",
            " e explode ", " e invoca ", " e cria ", " e restaura "
        };
        int found = -1;
        for (String marker : markers) {
            int index = text.indexOf(marker);
            if (index >= 0 && (found < 0 || index < found)) found = index;
        }
        return found;
    }

    private static String cleanPurpose(String text) {
        String result = text;
        String[] prefixes = {
            "com a capacidade de ", "com capacidade de ", "com habilidade de ", "com poder de ",
            "com efeito de ", "feita para ", "feito para ", "usada para ", "usado para ",
            "capaz de ", "que pode ", "que consegue ", "que causa ", "que dispara ", "que ",
            "para ", "e que ", "e cura ", "e regenera ", "e protege ", "e aumenta ",
            "e reduz ", "e concede ", "e aplica ", "e dispara ", "e congela ", "e queima ",
            "e envenena ", "e teleporta ", "e explode ", "e invoca ", "e cria ", "e restaura "
        };
        for (String prefix : prefixes) {
            if (result.startsWith(prefix)) {
                result = result.substring(prefix.length());
                break;
            }
        }
        return result.replaceAll("[,;:.!]+$", "").replaceAll("\\s+", " ").trim();
    }

    private static List<String> inferEffects(String text) {
        Set<String> result = new LinkedHashSet<String>();
        addIf(result, text, "heal", "cura", "curar", "curando", "recupera vida", "recuperar vida", "regenera vida",
            "regenerar vida", "restaura vida", "restaurar vida", "healing", "heal", "vida");
        addIf(result, text, "speed", "velocidade", "rapido", "rapida", "acelera", "acelerar");
        addIf(result, text, "strength", "forca", "dano aumentado", "aumenta o dano");
        addIf(result, text, "resistance", "resistencia", "protecao", "proteger", "protege", "escudo", "defesa");
        addIf(result, text, "regeneration", "regeneracao", "regenera", "regenerar");
        addIf(result, text, "jump", "pulo", "saltar", "salto");
        addIf(result, text, "fire_resistance", "resistencia ao fogo", "protecao contra fogo");
        addIf(result, text, "night_vision", "visao noturna", "enxergar no escuro");
        addIf(result, text, "water_breathing", "respirar debaixo d agua", "respiracao aquatica", "respirar na agua");
        addIf(result, text, "invisibility", "invisibilidade", "ficar invisivel", "invisivel");
        addIf(result, text, "mining_speed", "mineracao rapida", "minerar mais rapido", "velocidade de mineracao");
        addIf(result, text, "fire_attack", "fogo", "chamas", "incendiar", "queimar", "queima", "flamejante", "incendiario");
        addIf(result, text, "freeze_attack", "gelo", "congelar", "congela", "congelamento", "gelido");
        addIf(result, text, "poison_attack", "veneno", "envenenar", "envenena", "venenoso");
        addIf(result, text, "knockback", "repulsao", "empurrar", "arremessar", "afastar inimigos");
        addIf(result, text, "lightning_attack", "raio", "relampago", "eletricidade", "eletrico", "eletrica");
        addIf(result, text, "teleport", "teleportar", "teletransporte", "teleporte");
        addIf(result, text, "explosion", "explodir", "explosao", "explosivo");
        addIf(result, text, "flight", "voar", "voo", "voador", "voadora");
        addIf(result, text, "corruption", "corromper", "corrompe", "infectar", "contaminar", "corrupcao");
        addIf(result, text, "projectile", "disparar projeteis", "lancar projeteis", "atira", "atirar", "projeteis");
        if (hasTerm(text, "nao cura") || hasTerm(text, "nao curar") || hasTerm(text, "sem cura")) result.remove("heal");
        if (hasTerm(text, "nao queima") || hasTerm(text, "sem fogo")) result.remove("fire_attack");
        return new ArrayList<String>(result);
    }

    private static void addIf(Set<String> target, String text, String effect, String... terms) {
        for (String term : terms) {
            if (hasTerm(text, term)) {
                target.add(effect);
                return;
            }
        }
    }

    private static boolean hasTerm(String text, String term) {
        String normalized = CreationPlan.normalize(term);
        if (normalized.isEmpty()) return false;
        Pattern pattern = Pattern.compile("(^|[^a-z0-9])" + Pattern.quote(normalized) + "([^a-z0-9]|$)");
        Matcher matcher = pattern.matcher(text);
        return matcher.find();
    }

    private static String inferMaterial(String text) {
        String[][] materials = {
            {"obsidian", "obsidiana"}, {"diamond", "diamante"}, {"emerald", "esmeralda"},
            {"netherite", "netherita", "netherite"}, {"gold", "ouro", "dourado"},
            {"iron", "ferro", "aco", "aço"}, {"stone", "pedra"}, {"wood", "madeira", "madeiro"},
            {"crystal", "cristal", "cristalino"}, {"ice", "gelo", "neve"},
            {"fire", "fogo", "lava"}, {"redstone", "redstone"}, {"metal", "metal", "metalico"}
        };
        for (String[] group : materials) {
            for (int i = 1; i < group.length; i++) {
                if (hasTerm(text, group[i])) return group[0];
            }
        }
        return "base";
    }

    private static String describeEffects(List<String> values) {
        List<String> labels = new ArrayList<String>();
        for (String value : values) {
            if ("heal".equals(value)) labels.add("restaura vida");
            else if ("speed".equals(value)) labels.add("aumenta a velocidade");
            else if ("strength".equals(value)) labels.add("aumenta a força");
            else if ("resistance".equals(value)) labels.add("concede proteção");
            else if ("regeneration".equals(value)) labels.add("regenera vida");
            else if ("jump".equals(value)) labels.add("aumenta o salto");
            else if ("fire_resistance".equals(value)) labels.add("resiste ao fogo");
            else if ("night_vision".equals(value)) labels.add("concede visão noturna");
            else if ("water_breathing".equals(value)) labels.add("permite respirar na água");
            else if ("invisibility".equals(value)) labels.add("concede invisibilidade");
            else if ("mining_speed".equals(value)) labels.add("acelera a mineração");
            else if ("fire_attack".equals(value)) labels.add("aplica fogo ao alvo");
            else if ("freeze_attack".equals(value)) labels.add("congela ou desacelera o alvo");
            else if ("poison_attack".equals(value)) labels.add("envenena o alvo");
            else if ("knockback".equals(value)) labels.add("empurra o alvo");
            else if ("lightning_attack".equals(value)) labels.add("usa eletricidade");
            else if ("teleport".equals(value)) labels.add("teletransporta");
            else if ("explosion".equals(value)) labels.add("explode");
            else if ("flight".equals(value)) labels.add("permite voar");
            else if ("corruption".equals(value)) labels.add("corrompe ou infecta");
            else if ("projectile".equals(value)) labels.add("dispara projéteis");
        }
        return join(labels);
    }

    private static String defaultName(CreationPlan plan) {
        if (plan == null) return "Objeto personalizado";
        if (CreationPlan.ITEM.equals(plan.kind)) {
            if ("sword".equals(plan.archetype)) return "Espada personalizada";
            if ("tool".equals(plan.archetype)) return "Ferramenta personalizada";
            if ("food".equals(plan.archetype)) return "Alimento personalizado";
            if ("staff".equals(plan.archetype)) return "Cajado personalizado";
            if ("amulet".equals(plan.archetype)) return "Amuleto personalizado";
            if ("dagger".equals(plan.archetype)) return "Adaga personalizada";
            return "Artefato personalizado";
        }
        if (CreationPlan.BLOCK.equals(plan.kind)) return "Bloco personalizado";
        if (CreationPlan.ENTITY.equals(plan.kind)) return "Criatura personalizada";
        if (CreationPlan.STRUCTURE.equals(plan.kind)) return "Construção personalizada";
        if (CreationPlan.TERRAIN.equals(plan.kind)) return "Terreno personalizado";
        if (CreationPlan.MAP.equals(plan.kind)) return "Mapa personalizado";
        if (CreationPlan.DIMENSION.equals(plan.kind)) return "Dimensão personalizada";
        return "Objeto personalizado";
    }

    private static String titleCase(String value) {
        if (value == null || value.isEmpty()) return "";
        String first = value.substring(0, 1).toUpperCase(java.util.Locale.ROOT);
        return first + value.substring(1);
    }
}
