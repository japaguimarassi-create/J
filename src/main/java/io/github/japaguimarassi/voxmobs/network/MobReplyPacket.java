package io.github.japaguimarassi.voxmobs.network;

import io.github.japaguimarassi.voxmobs.client.ClientVoiceOutput;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.fml.DistExecutor;
import net.minecraftforge.network.NetworkEvent;

import java.util.UUID;
import java.util.function.Supplier;

public record MobReplyPacket(String reply, String entityType, UUID entityId, String mobName, String emotion) {
    public MobReplyPacket {
        reply = reply == null ? "" : reply.substring(0, Math.min(300, reply.length()));
        entityType = entityType == null ? "minecraft:pig" : entityType.substring(0, Math.min(128, entityType.length()));
        entityId = entityId == null ? new UUID(0L, 0L) : entityId;
        mobName = mobName == null ? "Mob" : mobName.substring(0, Math.min(64, mobName.length()));
        emotion = emotion == null ? "neutral" : emotion.substring(0, Math.min(24, emotion.length()));
    }

    public static MobReplyPacket decode(FriendlyByteBuf buffer) {
        String reply = buffer.readUtf(300);
        String entityType = buffer.readUtf(128);
        UUID entityId = new UUID(buffer.readLong(), buffer.readLong());
        String mobName = buffer.readUtf(64);
        String emotion = buffer.readUtf(24);
        return new MobReplyPacket(reply, entityType, entityId, mobName, emotion);
    }

    public void encode(FriendlyByteBuf buffer) {
        buffer.writeUtf(reply, 300);
        buffer.writeUtf(entityType, 128);
        buffer.writeLong(entityId.getMostSignificantBits());
        buffer.writeLong(entityId.getLeastSignificantBits());
        buffer.writeUtf(mobName, 64);
        buffer.writeUtf(emotion, 24);
    }

    public void handle(Supplier<NetworkEvent.Context> supplier) {
        NetworkEvent.Context context = supplier.get();
        context.enqueueWork(() -> DistExecutor.unsafeRunWhenOn(Dist.CLIENT, () ->
                () -> ClientVoiceOutput.speak(reply, entityType, entityId, mobName, emotion)));
        context.setPacketHandled(true);
    }
}
