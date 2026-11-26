package br.japa.wormhole.network;
import br.japa.wormhole.WormholePortals;
import br.japa.wormhole.item.PortalGunItem;
import br.japa.wormhole.portal.BubblePortalFactory;
import br.japa.wormhole.portal.PortalEndpointEntity;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.network.NetworkEvent;
import java.util.function.Supplier;
public final class PortalControlPacket {
    private final int entityId; private final int action; private final float value;
    public PortalControlPacket(int entityId, int action, float value) { this.entityId = entityId; this.action = action; this.value = value; }
    public static void encode(PortalControlPacket message, FriendlyByteBuf buffer) { buffer.writeVarInt(message.entityId); buffer.writeVarInt(message.action); buffer.writeFloat(message.value); }
    public static PortalControlPacket decode(FriendlyByteBuf buffer) { return new PortalControlPacket(buffer.readVarInt(), buffer.readVarInt(), buffer.readFloat()); }
    public static void handle(PortalControlPacket message, Supplier<NetworkEvent.Context> contextSupplier) {
        NetworkEvent.Context context = contextSupplier.get();
        context.enqueueWork(() -> {
            ServerPlayer player = context.getSender(); if (player == null) return;
            if (message.action == 4) {
                ItemStack stack = player.getMainHandItem().is(WormholePortals.PORTAL_GUN.get()) ? player.getMainHandItem() : player.getOffhandItem();
                if (!stack.is(WormholePortals.PORTAL_GUN.get())) return;
                PortalGunItem.adjustRadius(stack, Math.max(-1.0, Math.min(1.0, message.value)));
                return;
            }
            net.minecraft.world.entity.Entity entity = player.level().getEntity(message.entityId);
            if (!(entity instanceof PortalEndpointEntity endpoint) || endpoint.distanceToSqr(player) > 16.0 * 16.0) return;
            String id = endpoint.linkId();
            switch (message.action) {
                case 0 -> BubblePortalFactory.resize(player.server, id, Math.max(1.0, Math.min(8.0, endpoint.radius() + message.value)));
                case 1 -> BubblePortalFactory.setRange(player.server, id, Math.max(2.0, Math.min(128.0, endpoint.activationRange() + message.value)));
                case 2 -> BubblePortalFactory.setEnabled(player.server, id, !endpoint.isEnabled());
                case 3 -> BubblePortalFactory.removeLink(player.server, id);
                default -> { }
            }
        });
        context.setPacketHandled(true);
    }
}