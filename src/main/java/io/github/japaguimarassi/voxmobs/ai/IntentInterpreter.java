package io.github.japaguimarassi.voxmobs.ai;

import java.text.Normalizer;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class IntentInterpreter {
    private static final Pattern DIACRITICS = Pattern.compile("\\p{M}+");
    private static final Pattern ENTITY_ID = Pattern.compile("(?<![a-z0-9_.-])([a-z0-9_.-]+:[a-z0-9_./-]+)(?![a-z0-9_.-])", Pattern.CASE_INSENSITIVE);

    private IntentInterpreter() {
    }

    public static ActionRequest parseCommand(String message) {
        String text = normalize(message);
        if (text.isBlank()) {
            return new ActionRequest(MobAction.NONE, "");
        }
        if (contains(text, "pegue o item", "pega o item", "pegue um item", "pega um item", "pegue esse item", "apanhe o item", "apanhe isso", "recolha o item", "pegue isso", "pegue esse objeto", "pegue o objeto", "recolha esse objeto")) {
            return new ActionRequest(MobAction.PICKUP_ITEM, "");
        }
        if (contains(text, "solte o item", "solta o item", "larga o item", "largue o item", "drop o item", "dropa o item", "deixe o item no chao", "jogue o item no chao", "jogue isso fora", "largue o que esta segurando")) {
            return new ActionRequest(MobAction.DROP_ITEM, "");
        }
        if (contains(text, "spawn", "spawne", "invoque", "convoque", "gere um mob", "crie um mob", "traga um mob")) {
            Matcher matcher = ENTITY_ID.matcher(message == null ? "" : message);
            if (matcher.find()) {
                return new ActionRequest(MobAction.SPAWN_MOB, matcher.group(1).toLowerCase(Locale.ROOT));
            }
            return new ActionRequest(MobAction.SPAWN_MOB, "");
        }
        return new ActionRequest(interpret(message), "");
    }

    public static MobAction interpret(String message) {
        String text = normalize(message);
        if (text.isBlank()) {
            return MobAction.NONE;
        }
        if (contains(text, "pare", "pare ai", "pare aqui", "fica aqui", "fica parado", "nao se mexa", "me espera", "espera aqui")) {
            return MobAction.STOP;
        }
        if (contains(text, "me siga", "me segue", "siga me", "siga-me", "vem comigo", "venha comigo", "me acompanha", "acompanhe me", "acompanha", "segue me")) {
            return MobAction.FOLLOW;
        }
        if (contains(text, "chega perto", "venha aqui", "vem aqui", "se aproxime", "aproxima", "chegue mais perto")) {
            return MobAction.APPROACH;
        }
        if (contains(text, "foge", "fuja", "vai embora", "se afasta", "afaste", "fica longe", "saia daqui")) {
            return MobAction.FLEE;
        }
        if (contains(text, "olha para mim", "olhe para mim", "olha pra mim", "olhe pra mim", "me olha", "olhe aqui")) {
            return MobAction.LOOK;
        }
        if (contains(text, "senta", "sente", "deita", "deite")) {
            return MobAction.SIT;
        }
        if (contains(text, "pula", "salta", "de um pulo", "da um pulo")) {
            return MobAction.JUMP;
        }
        if (contains(text, "me protege", "me proteja", "protege me", "defenda me", "me defenda", "proteja me", "me acompanhe e me proteja")) {
            return MobAction.PROTECT;
        }
        return MobAction.NONE;
    }

    public static String normalize(String message) {
        if (message == null) {
            return "";
        }
        String decomposed = Normalizer.normalize(message, Normalizer.Form.NFD).toLowerCase(Locale.ROOT);
        return DIACRITICS.matcher(decomposed).replaceAll("").replaceAll("[^a-z0-9\\s'-]", " ").replaceAll("\\s+", " ").trim();
    }

    private static boolean contains(String text, String... phrases) {
        String padded = " " + text + " ";
        for (String phrase : phrases) {
            String normalized = normalize(phrase);
            if (padded.contains(" " + normalized + " ")) {
                return true;
            }
        }
        return false;
    }
}
