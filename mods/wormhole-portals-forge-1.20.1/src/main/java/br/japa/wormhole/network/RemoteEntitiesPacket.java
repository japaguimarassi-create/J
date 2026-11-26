package br.japa.wormhole.network;
import br.japa.wormhole.client.RemoteDimensionManager;
import io.netty.handler.codec.DecoderException;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.resources.ResourceLocation;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.fml.DistExecutor;
import net.minecraftforge.network.NetworkDirection;
import net.minecraftforge.network.NetworkEvent;
import java.util.ArrayList;
import java.util.List;
import java.util.function.Supplier;
public final class RemoteEntitiesPacket {
    private static final int MAX_ENTITIES = 64;
    private static final int MAX_NBT_BYTES = 262144;
    private final ResourceLocation dimension;
    private final List<EntitySnapshot> entities;
    public RemoteEntitiesPacket(ResourceLocation dimension, List<EntitySnapshot> entities) {
        this.dimension = dimension;
        this.entities = List.copyOf(entities.subList(0, Math.min(entities.size(), MAX_ENTITIES)));
    }
    public static void encode(RemoteEntitiesPacket packet, FriendlyByteBuf buffer) {
        buffer.writeResourceLocation(packet.dimension);
        buffer.writeVarInt(packet.entities.size());
        for (EntitySnapshot entity : packet.entities) {
            buffer.writeVarInt(entity.id());
            buffer.writeResourceLocation(entity.type());
            buffer.writeNbt(entity.data());
            buffer.writeVarInt(entity.vehicleId());
        }
    }
    public static RemoteEntitiesPacket decode(FriendlyByteBuf buffer) {
        ResourceLocation dimension = buffer.readResourceLocation();
        int count = buffer.readVarInt();
        if (count < 0 || count > MAX_ENTITIES) throw new DecoderException("Invalid remote entity count");
        List<EntitySnapshot> entities = new ArrayList<>(count);
        for (int i = 0; i < count; i++) {
            int id = buffer.readVarInt();
            ResourceLocation type = buffer.readResourceLocation();
            CompoundTag data = buffer.readNbt();
            if (data == null) throw new DecoderException("Missing remote entity data");
            if (data.toString().length() > MAX_NBT_BYTES) throw new DecoderException("Remote entity data exceeds limit");
            int vehicleId = buffer.readVarInt();
            entities.add(new EntitySnapshot(id, type, data, vehicleId));
        }
        return new RemoteEntitiesPacket(dimension, entities);
    }
    public static void handle(RemoteEntitiesPacket packet, Supplier<NetworkEvent.Context> contextSupplier) {
        NetworkEvent.Context context = contextSupplier.get();
        if (context.getDirection() != NetworkDirection.PLAY_TO_CLIENT) { context.setPacketHandled(true); return; }
        context.enqueueWork(() -> DistExecutor.unsafeRunWhenOn(Dist.CLIENT, () -> () ->
            RemoteDimensionManager.updateEntities(packet.dimension, packet.entities)));
        context.setPacketHandled(true);
    }
    public record EntitySnapshot(int id, ResourceLocation type, CompoundTag data, int vehicleId) {
        public EntitySnapshot {
            data = data.copy();
        }
    }
}