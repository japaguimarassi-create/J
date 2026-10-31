package io.github.japaguimarassi.voxmobs.client;

import io.github.japaguimarassi.voxmobs.network.MobMessagePacket;
import io.github.japaguimarassi.voxmobs.network.NetworkHandler;
import net.minecraft.client.Minecraft;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.phys.EntityHitResult;
import net.minecraftforge.client.event.ClientChatEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;

public final class ClientChatInput {
    private static final String PREFIX = "!mob ";

    private ClientChatInput() {
    }

    @SubscribeEvent
    public static void onClientChat(ClientChatEvent event) {
        String message = event.getMessage();
        if (message == null || !message.startsWith(PREFIX)) {
            return;
        }
        event.setCanceled(true);
        String body = message.substring(PREFIX.length()).trim();
        Minecraft minecraft = Minecraft.getInstance();
        if (body.isBlank() || minecraft.player == null) {
            return;
        }
        if (!(minecraft.hitResult instanceof EntityHitResult hit) || !(hit.getEntity() instanceof Mob mob)) {
            minecraft.player.displayClientMessage(Component.literal("VoxMobs: mire para um mob e use !mob sua mensagem."), true);
            return;
        }
        NetworkHandler.sendToServer(new MobMessagePacket(mob.getId(), body));
    }
}
