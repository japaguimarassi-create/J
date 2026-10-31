package io.github.japaguimarassi.voxmobs.client;

import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.eventbus.api.IEventBus;

public final class ClientBootstrap {
    private ClientBootstrap() {
    }

    public static void register(IEventBus modEventBus) {
        modEventBus.addListener(ClientVoiceController::registerKeys);
        MinecraftForge.EVENT_BUS.register(ClientVoiceController.class);
        MinecraftForge.EVENT_BUS.register(ClientChatInput.class);
    }
}
