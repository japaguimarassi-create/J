package com.enturma.mod;

import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.Mob;
import net.minecraftforge.fml.ModList;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class AIClient {
    private static final Gson GSON = new Gson();
    private static final ExecutorService REQUESTS = Executors.newFixedThreadPool(3, runnable -> {
        Thread thread = new Thread(runnable, "Enturma-AI-HTTP");
        thread.setDaemon(true);
        return thread;
    });

    public record Turn(String role, String content) {}

    private AIClient() {}

    public static void request(Mob mob, ServerPlayer player, String message, List<Turn> history) {
        if (!(mob.level() instanceof ServerLevel serverLevel)) return;
        UUID mobId = mob.getUUID();
        UUID playerId = player.getUUID();
        String mobName = mob.getDisplayName().getString();
        String entityId = BuiltInRegistries.ENTITY_TYPE.getKey(mob.getType()).toString();
        JsonObject request = new JsonObject();
        request.addProperty("player_name", player.getGameProfile().getName());
        request.addProperty("player_message", message);
        request.addProperty("mob_name", mobName);
        request.addProperty("mob_id", entityId);
        request.addProperty("voice_profile", voiceProfile(entityId));
        request.addProperty("dimension", mob.level().dimension().location().toString());
        request.addProperty("game_context", gameContext(mob, player));
        request.addProperty("research", EnturmaConfig.WEB_RESEARCH.get());
        JsonArray mods = new JsonArray();
        ModList.get().getMods().stream().limit(100).forEach(info -> mods.add(info.getModId() + "@" + info.getVersion()));
        request.add("installed_mods", mods);
        JsonArray turns = new JsonArray();
        for (Turn turn : history) {
            JsonObject item = new JsonObject();
            item.addProperty("role", turn.role());
            item.addProperty("content", turn.content());
            turns.add(item);
        }
        request.add("history", turns);

        REQUESTS.submit(() -> {
            JsonObject result;
            try {
                    result = postJson(endpoint("/api/minecraft/dialogue"), request);
                if (result == null) throw new IllegalStateException("Resposta vazia do backend");
            } catch (Exception exception) {
                serverLevel.getServer().execute(() -> fallback(mobId, playerId, message));
                return;
            }
            serverLevel.getServer().execute(() -> {
                Mob currentMob = serverLevel.getEntity(mobId) instanceof Mob found ? found : null;
                ServerPlayer currentPlayer = serverLevel.getServer().getPlayerList().getPlayer(playerId);
                if (currentMob == null || currentPlayer == null) return;
                String dialogue = result.has("dialogue") ? result.get("dialogue").getAsString() : "...";
                String emotion = result.has("emotion") ? result.get("emotion").getAsString() : "neutral";
                JsonArray actions = result.has("actions") && result.get("actions").isJsonArray() ? result.getAsJsonArray("actions") : new JsonArray();
                actions = filterUnauthorizedDrops(actions, message);
                MobConversationHandler.acceptReply(currentMob, currentPlayer, dialogue, emotion, actions);
            });
        });
    }


    private static JsonArray filterUnauthorizedDrops(JsonArray actions, String message) {
        String normalized = message == null ? "" : message.toLowerCase(java.util.Locale.ROOT);
        List<String> requestPhrases = List.of(
            "me dá", "me da", "me de", "me dê", "me dar", "pode me dar", "poderia me dar",
            "me entrega", "me empresta", "me passa", "me presenteia", "me arranja", "dá pra mim",
            "dê pra mim", "give me", "can i have", "could i have", "drop a", "drop me", "solta um", "solta uma"
        );
        boolean requestedItem = requestPhrases.stream().anyMatch(normalized::contains);
        JsonArray safe = new JsonArray();
        for (JsonElement element : actions) {
            if (!element.isJsonObject()) continue;
            JsonObject action = element.getAsJsonObject();
            if (action.has("type") && "give_item".equals(action.get("type").getAsString()) && !requestedItem) continue;
            safe.add(action.deepCopy());
        }
        return safe;
    }

    private static JsonObject postJson(String endpoint, JsonObject payload) throws Exception {
        HttpURLConnection connection = (HttpURLConnection) URI.create(endpoint).toURL().openConnection();
        connection.setRequestMethod("POST");
        connection.setConnectTimeout(2000);
        connection.setReadTimeout(45000);
        connection.setDoOutput(true);
        connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
        byte[] body = GSON.toJson(payload).getBytes(StandardCharsets.UTF_8);
        connection.setFixedLengthStreamingMode(body.length);
        try (OutputStream output = connection.getOutputStream()) {
            output.write(body);
        }
        int status = connection.getResponseCode();
        InputStream stream = status >= 200 && status < 300 ? connection.getInputStream() : connection.getErrorStream();
        if (stream == null) throw new IllegalStateException("Backend HTTP " + status);
        byte[] response;
        try (InputStream input = stream; ByteArrayOutputStream buffer = new ByteArrayOutputStream()) {
            input.transferTo(buffer);
            response = buffer.toByteArray();
        } finally {
            connection.disconnect();
        }
        if (status < 200 || status >= 300) throw new IllegalStateException("Backend HTTP " + status);
        return GSON.fromJson(new String(response, StandardCharsets.UTF_8), JsonObject.class);
    }

    private static String endpoint(String path) {
        String base = EnturmaConfig.AI_ENDPOINT.get().trim();
        while (base.endsWith("/")) base = base.substring(0, base.length() - 1);
        return base + path;
    }

    private static String gameContext(Mob mob, ServerPlayer player) {
        String biome = mob.level().getBiome(mob.blockPosition()).unwrapKey()
            .map(key -> key.location().toString()).orElse("bioma-desconhecido");
        return "bioma=" + biome + "; distancia=" + String.format(java.util.Locale.ROOT, "%.1f", mob.distanceTo(player))
            + "; saude=" + String.format(java.util.Locale.ROOT, "%.1f", mob.getHealth()) + "/" + mob.getMaxHealth()
            + "; vida_do_jogador=" + String.format(java.util.Locale.ROOT, "%.1f", player.getHealth())
            + "; dia_mundial=" + (mob.level().getDayTime() % 24000L < 12000L)
            + "; modo=" + player.gameMode.getGameModeForPlayer().getName();
    }

    private static String voiceProfile(String entityId) {
        if (entityId.equals("minecraft:villager") || entityId.equals("minecraft:wandering_trader")) return "villager";
        if (entityId.equals("minecraft:iron_golem")) return "iron_golem";
        if (entityId.equals("minecraft:zombie") || entityId.equals("minecraft:drowned") || entityId.equals("minecraft:husk")) return "zombie";
        if (entityId.equals("minecraft:skeleton") || entityId.equals("minecraft:stray") || entityId.equals("minecraft:wither_skeleton")) return "skeleton";
        if (entityId.equals("minecraft:creeper")) return "creeper";
        if (entityId.equals("minecraft:cat")) return "cat";
        if (entityId.equals("minecraft:pig")) return "pig";
        if (entityId.equals("minecraft:wolf") || entityId.equals("minecraft:dog")) return "wolf";
        if (entityId.contains("parrot") || entityId.contains("chicken") || entityId.contains("allay")) return "bird";
        if (entityId.contains("cow") || entityId.contains("mooshroom")) return "cow";
        if (entityId.contains("sheep")) return "sheep";
        if (entityId.contains("enderman")) return "enderman";
        if (entityId.contains("illager") || entityId.contains("pillager") || entityId.contains("evoker") || entityId.contains("vindicator")) return "illager";
        if (entityId.contains("witch")) return "witch";
        if (entityId.contains("blaze")) return "blaze";
        if (entityId.contains("slime")) return "slime";
        if (entityId.contains("warden")) return "warden";
        if (entityId.contains("fox")) return "fox";
        if (entityId.contains("bee")) return "bee";
        if (entityId.contains("fish") || entityId.contains("axolotl") || entityId.contains("dolphin") || entityId.contains("guardian")) return "aquatic";
        return "generic";
    }

    private static void fallback(UUID mobId, UUID playerId, String message) {
        net.minecraft.server.MinecraftServer server = net.minecraftforge.server.ServerLifecycleHooks.getCurrentServer();
        if (server == null) return;
        ServerPlayer player = server.getPlayerList().getPlayer(playerId);
        if (player == null) return;
        Mob mob = player.serverLevel().getEntity(mobId) instanceof Mob found ? found : null;
        if (mob == null) return;
        String line;
        if (message.equals("__greeting__") || message.equalsIgnoreCase("oi") || message.equalsIgnoreCase("olá")) {
            line = mob.getType().toShortString().contains("villager")
                ? "Hm? Ah, olá! Está procurando alguma coisa pela vila? Hmm."
                : "*olha para você com curiosidade* O que foi?";
        } else {
            line = "*presta atenção* Entendi. Pode me explicar um pouco mais?";
        }
        MobConversationHandler.acceptReply(mob, player, line, "curious", new JsonArray());
        player.sendSystemMessage(Component.literal("[Enturma AI] O backend não respondeu; use /enturma status para verificar a configuração."));
    }
}
