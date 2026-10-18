package com.enturma.voice;

import com.enturma.mod.VoiceBridge;
import de.maxhenkel.voicechat.api.VoicechatApi;
import de.maxhenkel.voicechat.api.VoicechatPlugin;
import de.maxhenkel.voicechat.api.events.EventRegistration;
import de.maxhenkel.voicechat.api.events.VoicechatServerStartedEvent;
import de.maxhenkel.voicechat.api.ForgeVoicechatPlugin;

@ForgeVoicechatPlugin
public final class EnturmaVoicePlugin implements VoicechatPlugin {
    @Override
    public String getPluginId() {
        return "enturma";
    }

    @Override
    public void initialize(VoicechatApi api) {
    }

    @Override
    public void registerEvents(EventRegistration registration) {
        registration.registerEvent(VoicechatServerStartedEvent.class, this::onServerStarted);
    }

    private void onServerStarted(VoicechatServerStartedEvent event) {
        VoicechatApi api = event.getVoicechat();
        VoicePlayback.initialize(api);
        VoiceBridge.registerVoiceApi(api);
    }
}
