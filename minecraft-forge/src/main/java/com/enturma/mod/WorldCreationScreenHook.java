package com.enturma.mod;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.screens.worldselection.CreateWorldScreen;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.ScreenEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

@Mod.EventBusSubscriber(modid = EnturmaMod.MOD_ID, value = Dist.CLIENT, bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class WorldCreationScreenHook {
    private WorldCreationScreenHook() {}

    @SubscribeEvent
    public static void onScreenInit(ScreenEvent.Init.Post event) {
        if (!(event.getScreen() instanceof CreateWorldScreen screen)) return;
        int width = Math.min(120, screen.width - 8);
        int x = Math.max(4, screen.width - width - 4);
        int y = 24;
        event.addListener(Button.builder(net.minecraft.network.chat.Component.literal("Mobs: Enturma"), button ->
            Minecraft.getInstance().setScreen(new MobSelectionScreen(screen))
        ).bounds(x, y, width, 20).build());
    }
}
