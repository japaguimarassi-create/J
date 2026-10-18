package com.enturma.voice;

import de.maxhenkel.voicechat.api.VoicechatApi;
import de.maxhenkel.voicechat.api.VoicechatServerApi;
import de.maxhenkel.voicechat.api.audiochannel.AudioPlayer;
import de.maxhenkel.voicechat.api.audiochannel.LocationalAudioChannel;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Mob;

import java.util.UUID;
import java.util.concurrent.atomic.AtomicReference;

public final class VoicePlayback {
    private static final String CATEGORY = "enturma_voice";
    private static final AtomicReference<VoicechatServerApi> SERVER_API = new AtomicReference<>();

    private VoicePlayback() {}

    public static void initialize(VoicechatApi api) {
        if (!(api instanceof VoicechatServerApi serverApi)) return;
        SERVER_API.set(serverApi);
        serverApi.registerVolumeCategory(serverApi.volumeCategoryBuilder()
            .setId(CATEGORY)
            .setName("Enturma AI")
            .setDescription("Vozes sintetizadas das criaturas do Enturma AI")
            .build());
    }

    public static void play(Mob mob, byte[] pcm) {
        VoicechatServerApi api = SERVER_API.get();
        if (api == null || !(mob.level() instanceof ServerLevel level) || !mob.isAlive()) return;
        int length = pcm.length - (pcm.length % 2);
        short[] samples = new short[length / 2];
        for (int i = 0; i < samples.length; i++) {
            int low = pcm[i * 2] & 0xff;
            int high = pcm[i * 2 + 1];
            samples[i] = (short) ((high << 8) | low);
        }
        LocationalAudioChannel channel = api.createLocationalAudioChannel(UUID.randomUUID(), api.fromServerLevel(level), api.createPosition(mob.getX(), mob.getY() + mob.getBbHeight() * 0.7D, mob.getZ()));
        if (channel == null) return;
        channel.setCategory(CATEGORY);
        channel.setDistance(18.0F);
        AudioPlayer player = api.createAudioPlayer(channel, api.createEncoder(), samples);
        player.startPlaying();
    }
}
