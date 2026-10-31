package io.github.japaguimarassi.voxmobs.client;

import io.github.japaguimarassi.voxmobs.config.VoxMobsConfig;
import io.github.japaguimarassi.voxmobs.speech.FormantTtsEngine;
import io.github.japaguimarassi.voxmobs.speech.VoicePlayback;
import io.github.japaguimarassi.voxmobs.speech.VoiceProfile;
import net.minecraft.client.Minecraft;
import net.minecraft.network.chat.Component;

import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class ClientVoiceOutput {
    private static final ExecutorService AUDIO_QUEUE = Executors.newSingleThreadExecutor(runnable -> {
        Thread thread = new Thread(runnable, "VoxMobs-TTS");
        thread.setDaemon(true);
        return thread;
    });

    private ClientVoiceOutput() {
    }

    public static void speak(String text, String entityType, UUID entityId, String mobName, String emotion) {
        if (!VoxMobsConfig.CLIENT_VALUES.voiceEnabled.get() || text == null || text.isBlank()) {
            return;
        }
        String safeText = text.substring(0, Math.min(300, text.length()));
        double volume = VoxMobsConfig.CLIENT_VALUES.voiceVolume.get();
        String genderMode = VoxMobsConfig.CLIENT_VALUES.voiceGenderMode.get();
        VoiceProfile profile = VoiceProfile.forMob(entityType, mobName, entityId, genderMode).withEmotion(emotion);
        if (VoxMobsConfig.CLIENT_VALUES.showVoiceIdentity.get()) {
            Minecraft minecraft = Minecraft.getInstance();
            if (minecraft.player != null) {
                minecraft.player.displayClientMessage(Component.literal("Voz de " + mobName + ": "
                        + profile.voiceName() + " (" + profile.gender() + ")"), true);
            }
        }
        AUDIO_QUEUE.submit(() -> {
            byte[] audio = FormantTtsEngine.synthesize(safeText, profile);
            VoicePlayback.play(audio, volume);
        });
    }
}
