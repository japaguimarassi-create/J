package com.enturma.mod;

import net.minecraft.world.entity.Mob;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.lang.reflect.Method;
import java.net.HttpURLConnection;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicReference;

public final class VoiceBridge {
    private static final AtomicReference<Object> VOICE_API = new AtomicReference<>();
    private static final ExecutorService AUDIO_REQUESTS = Executors.newSingleThreadExecutor(runnable -> {
        Thread thread = new Thread(runnable, "Enturma-AI-voice");
        thread.setDaemon(true);
        return thread;
    });

    private VoiceBridge() {}

    public static void registerVoiceApi(Object api) {
        VOICE_API.set(api);
    }

    public static void speak(Mob mob, String text) {
        Object api = VOICE_API.get();
        if (api == null || !EnturmaConfig.VOICE_ENABLED.get() || !EnturmaConfig.ENABLED.get() || text == null || text.isBlank()) return;
        String entityId = net.minecraft.core.registries.BuiltInRegistries.ENTITY_TYPE.getKey(mob.getType()).toString();
        String profile = entityId.equals("minecraft:villager") || entityId.equals("minecraft:wandering_trader") ? "villager"
            : entityId.equals("minecraft:iron_golem") ? "iron_golem"
            : entityId.contains("zombie") || entityId.contains("drowned") || entityId.contains("husk") ? "zombie"
            : entityId.contains("skeleton") ? "skeleton"
            : entityId.equals("minecraft:creeper") ? "creeper"
            : entityId.equals("minecraft:cat") ? "cat"
            : entityId.equals("minecraft:pig") ? "pig" : "generic";
        AUDIO_REQUESTS.submit(() -> {
            try {
                String base = EnturmaConfig.AI_ENDPOINT.get().replaceAll("/+$", "");
                HttpURLConnection connection = (HttpURLConnection) URI.create(base + "/api/minecraft/voice").toURL().openConnection();
                connection.setRequestMethod("POST");
                connection.setConnectTimeout(2000);
                connection.setReadTimeout(30000);
                connection.setDoOutput(true);
                connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
                com.google.gson.JsonObject body = new com.google.gson.JsonObject();
                body.addProperty("text", text.length() > 450 ? text.substring(0, 450) : text);
                body.addProperty("profile", profile);
                byte[] payload = new com.google.gson.Gson().toJson(body).getBytes(StandardCharsets.UTF_8);
                try (OutputStream output = connection.getOutputStream()) { output.write(payload); }
                int status = connection.getResponseCode();
                if (status < 200 || status >= 300) { connection.disconnect(); return; }
                byte[] audio;
                try (InputStream input = connection.getInputStream(); ByteArrayOutputStream buffer = new ByteArrayOutputStream()) {
                    input.transferTo(buffer);
                    audio = buffer.toByteArray();
                } finally {
                    connection.disconnect();
                }
                if (audio.length < 2 || audio.length > 2880000) return;
                mob.level().getServer().execute(() -> {
                    if (!mob.isAlive() || VOICE_API.get() == null) return;
                    try {
                        Class<?> playback = Class.forName("com.enturma.voice.VoicePlayback");
                        Method method = playback.getMethod("play", Mob.class, byte[].class);
                        method.invoke(null, mob, audio);
                    } catch (ReflectiveOperationException ignored) {
                    }
                });
            } catch (Exception ignored) {
            }
        });
    }
}
