package br.japa.wormhole.network;

import br.japa.wormhole.WormholePortals;
import net.minecraft.resources.ResourceLocation;
import net.minecraftforge.network.NetworkRegistry;
import net.minecraftforge.network.simple.SimpleChannel;

public final class PortalControlNetwork {
    private static final String PROTOCOL = "1";
    public static final SimpleChannel CHANNEL = NetworkRegistry.newSimpleChannel(
        new ResourceLocation(WormholePortals.MOD_ID, "control"),
        () -> PROTOCOL,
        PROTOCOL::equals,
        PROTOCOL::equals
    );
    private static boolean registered;

    private PortalControlNetwork() {}

    public static synchronized void register() {
        if (registered) return;
        CHANNEL.registerMessage(0, PortalControlPacket.class,
            PortalControlPacket::encode,
            PortalControlPacket::decode,
            PortalControlPacket::handle
        );
        registered = true;
    }
}