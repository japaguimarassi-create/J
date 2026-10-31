package io.github.japaguimarassi.voxmobs.network;

import io.github.japaguimarassi.voxmobs.ai.ConversationService;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.server.level.ServerPlayer;
import net.minecraftforge.network.NetworkEvent;

import java.util.function.Supplier;

public record MobMessagePacket(int entityId, String message) {
    public MobMessagePacket {
        message = message == null ? "" : message.trim();
        if (message.length() > 240) {
            message = message.substring(0, 240);
        }
    }

    public static MobMessagePacket decode(FriendlyByteBuf buffer) {
        return new MobMessagePacket(buffer.readVarInt(), buffer.readUtf(240));
    }

    public void encode(FriendlyByteBuf buffer) {
        buffer.writeVarInt(entityId);
        buffer.writeUtf(message, 240);
    }

    public void handle(Supplier<NetworkEvent.Context> supplier) {
        NetworkEvent.Context context = supplier.get();
        context.enqueueWork(() -> {
            ServerPlayer player = context.getSender();
            if (player != null && !message.isBlank()) {
                ConversationService.handle(player, entityId, message);
            }
        });
        context.setPacketHandled(true);
    }
}
