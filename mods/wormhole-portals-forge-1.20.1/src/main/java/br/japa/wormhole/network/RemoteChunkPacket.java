package br.japa.wormhole.network;
import br.japa.wormhole.client.RemoteDimensionManager;
import io.netty.handler.codec.DecoderException;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.resources.ResourceLocation;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.fml.DistExecutor;
import net.minecraftforge.network.NetworkDirection;
import net.minecraftforge.network.NetworkEvent;
import java.util.function.Supplier;
public final class RemoteChunkPacket {
    private static final int MAX_PACKET_BYTES = 2_000_000;
    private final ResourceLocation dimension;
    private final ResourceLocation dimensionType;
    private final int chunkX;
    private final int chunkZ;
    private final byte[] payload;
    public RemoteChunkPacket(ResourceLocation dimension, ResourceLocation dimensionType, int chunkX, int chunkZ, byte[] payload) {
        this.dimension = dimension; this.dimensionType = dimensionType; this.chunkX = chunkX; this.chunkZ = chunkZ; this.payload = payload;
    }
    public static void encode(RemoteChunkPacket packet, FriendlyByteBuf buffer) {
        buffer.writeResourceLocation(packet.dimension);
        buffer.writeResourceLocation(packet.dimensionType);
        buffer.writeVarInt(packet.chunkX);
        buffer.writeVarInt(packet.chunkZ);
        buffer.writeVarInt(packet.payload.length);
        buffer.writeBytes(packet.payload);
    }
    public static RemoteChunkPacket decode(FriendlyByteBuf buffer) {
        ResourceLocation dimension = buffer.readResourceLocation();
        ResourceLocation type = buffer.readResourceLocation();
        int x = buffer.readVarInt();
        int z = buffer.readVarInt();
        int length = buffer.readVarInt();
        if (length < 0 || length > MAX_PACKET_BYTES || length > buffer.readableBytes()) throw new DecoderException("Invalid remote chunk payload length");
        byte[] payload = new byte[length];
        buffer.readBytes(payload);
        return new RemoteChunkPacket(dimension, type, x, z, payload);
    }
    public static void handle(RemoteChunkPacket packet, Supplier<NetworkEvent.Context> contextSupplier) {
        NetworkEvent.Context context = contextSupplier.get();
        if (context.getDirection() != NetworkDirection.PLAY_TO_CLIENT) { context.setPacketHandled(true); return; }
        context.enqueueWork(() -> DistExecutor.unsafeRunWhenOn(Dist.CLIENT, () -> () ->
            RemoteDimensionManager.receive(packet.dimension, packet.dimensionType, packet.chunkX, packet.chunkZ, packet.payload)));
        context.setPacketHandled(true);
    }
}