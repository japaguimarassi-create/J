package br.japa.wormhole.network;
import br.japa.wormhole.WormholePortals;
import net.minecraft.resources.ResourceLocation;
import net.minecraftforge.network.NetworkDirection;
import net.minecraftforge.network.NetworkRegistry;
import net.minecraftforge.network.simple.SimpleChannel;
import java.util.Optional;
public final class PortalControlNetwork {
    private static final String PROTOCOL = "1";
    public static final SimpleChannel CHANNEL = NetworkRegistry.newSimpleChannel(
        new ResourceLocation(WormholePortals.MOD_ID, "control"),
        () -> PROTOCOL, PROTOCOL::equals, PROTOCOL::equals
    );
    private static boolean registered;
    private PortalControlNetwork() {}
    public static synchronized void register() {
        if (registered) return;
        CHANNEL.registerMessage(0, PortalControlPacket.class, PortalControlPacket::encode, PortalControlPacket::decode, PortalControlPacket::handle);
        CHANNEL.registerMessage(1, RemoteChunkPacket.class, RemoteChunkPacket::encode, RemoteChunkPacket::decode, RemoteChunkPacket::handle, Optional.of(NetworkDirection.PLAY_TO_CLIENT));
        registered = true;
    }
}