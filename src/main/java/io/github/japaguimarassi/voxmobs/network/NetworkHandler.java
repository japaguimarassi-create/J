package io.github.japaguimarassi.voxmobs.network;

import io.github.japaguimarassi.voxmobs.VoxMobs;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraftforge.network.NetworkRegistry;
import net.minecraftforge.network.NetworkDirection;
import net.minecraftforge.network.PacketDistributor;
import net.minecraftforge.network.simple.SimpleChannel;

public final class NetworkHandler {
    private static final String VERSION = "2";
    public static final SimpleChannel CHANNEL = NetworkRegistry.newSimpleChannel(
            new ResourceLocation(VoxMobs.MOD_ID, "main"),
            () -> VERSION,
            VERSION::equals,
            VERSION::equals
    );
    private static int nextId;
    private static boolean registered;

    private NetworkHandler() {
    }

    public static synchronized void register() {
        if (registered) {
            return;
        }
        CHANNEL.messageBuilder(MobMessagePacket.class, nextId++, NetworkDirection.PLAY_TO_SERVER)
                .encoder(MobMessagePacket::encode)
                .decoder(MobMessagePacket::decode)
                .consumerMainThread(MobMessagePacket::handle)
                .add();
        CHANNEL.messageBuilder(MobReplyPacket.class, nextId++, NetworkDirection.PLAY_TO_CLIENT)
                .encoder(MobReplyPacket::encode)
                .decoder(MobReplyPacket::decode)
                .consumerMainThread(MobReplyPacket::handle)
                .add();
        registered = true;
    }

    public static void sendToServer(MobMessagePacket packet) {
        CHANNEL.sendToServer(packet);
    }

    public static void sendReply(ServerPlayer player, MobReplyPacket packet) {
        CHANNEL.send(PacketDistributor.PLAYER.with(() -> player), packet);
    }
}
