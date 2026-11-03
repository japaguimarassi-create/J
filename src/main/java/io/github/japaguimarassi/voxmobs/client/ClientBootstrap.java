package io.github.japaguimarassi.voxmobs.client;

import io.github.japaguimarassi.voxmobs.client.renderer.TalkingVillagerRenderer;
import io.github.japaguimarassi.voxmobs.registry.ModEntities;
import net.minecraftforge.client.event.EntityRenderersEvent;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.eventbus.api.IEventBus;

public final class ClientBootstrap {
    private ClientBootstrap() {
    }

    public static void register(IEventBus modEventBus) {
        modEventBus.addListener(ClientVoiceController::registerKeys);
        modEventBus.addListener(ClientBootstrap::registerRenderers);
        MinecraftForge.EVENT_BUS.register(ClientVoiceController.class);
        MinecraftForge.EVENT_BUS.register(ClientChatInput.class);
    }

    private static void registerRenderers(EntityRenderersEvent.RegisterRenderers event) {
        event.registerEntityRenderer(ModEntities.TALKING_VILLAGER.get(), TalkingVillagerRenderer::new);
    }
}
