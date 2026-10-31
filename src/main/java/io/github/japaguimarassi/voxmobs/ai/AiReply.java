package io.github.japaguimarassi.voxmobs.ai;

import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

public record AiReply(String reply, MobAction action, String emotion, String argument) {
    public AiReply(String reply, MobAction action, String emotion) {
        this(reply, action, emotion, "");
    }

    public AiReply {
        reply = sanitize(reply);
        action = action == null ? MobAction.NONE : action;
        emotion = sanitize(emotion);
        argument = sanitize(argument);
        if (emotion.length() > 24) {
            emotion = emotion.substring(0, 24);
        }
        if (argument.length() > 128) {
            argument = argument.substring(0, 128);
        }
    }

    public static AiReply parse(String raw) {
        if (raw == null || raw.isBlank()) {
            return new AiReply("Não entendi. Pode repetir?", MobAction.NONE, "confuso");
        }
        String cleaned = raw.trim();
        if (cleaned.startsWith("```")) {
            cleaned = cleaned.replaceFirst("^```(?:json)?\\s*", "").replaceFirst("\\s*```$", "").trim();
        }
        try {
            JsonElement parsed = JsonParser.parseString(cleaned);
            if (parsed.isJsonObject()) {
                JsonObject object = parsed.getAsJsonObject();
                String text = stringValue(object, "reply", "Não entendi. Pode repetir?");
                String action = stringValue(object, "action", "NONE");
                String emotion = stringValue(object, "emotion", "neutral");
                String argument = stringValue(object, "argument", "");
                return new AiReply(text, MobAction.safeParse(action), emotion, argument);
            }
        } catch (RuntimeException ignored) {
        }
        return new AiReply(cleaned, MobAction.NONE, "neutral");
    }

    private static String stringValue(JsonObject object, String key, String fallback) {
        JsonElement value = object.get(key);
        return value != null && value.isJsonPrimitive() ? value.getAsString() : fallback;
    }

    private static String sanitize(String value) {
        if (value == null) {
            return "";
        }
        return value.replaceAll("[\\p{Cntrl}&&[^\\n\\t]]", "").trim();
    }
}
