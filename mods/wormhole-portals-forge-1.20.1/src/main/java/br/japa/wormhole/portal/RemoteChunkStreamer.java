package br.japa.wormhole.portal;
import br.japa.wormhole.network.PortalControlNetwork;
import br.japa.wormhole.network.RemoteChunkPacket;
import io.netty.buffer.ByteBuf;
import io.netty.buffer.ByteBufUtil;
import io.netty.buffer.Unpooled;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.network.protocol.game.ClientboundLevelChunkWithLightPacket;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.chunk.LevelChunk;
import net.minecraftforge.network.PacketDistributor;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
public final class RemoteChunkStreamer {
    private static final Map<UUID, Map<String, Long>> LAST_SENT = new HashMap<>();
    private static final int VIEW_RADIUS = 1;
    private static final long RESEND_INTERVAL = 40L;
    private RemoteChunkStreamer() {}
    public static void sync(ServerLevel source, PortalEndpointEntity endpoint, ServerPlayer player) {
        ServerLevel destination = source.getServer().getLevel(net.minecraft.resources.ResourceKey.create(
            net.minecraft.core.registries.Registries.DIMENSION, endpoint.destinationId()));
        if (destination == null) return;
        net.minecraft.world.phys.Vec3 remotePoint = endpoint.targetPosition().add(player.position().subtract(endpoint.position()));
        int centerX = net.minecraft.core.BlockPos.containing(remotePoint).getX() >> 4;
        int centerZ = net.minecraft.core.BlockPos.containing(remotePoint).getZ() >> 4;
        long now = source.getGameTime();
        Map<String, Long> playerCache = LAST_SENT.computeIfAbsent(player.getUUID(), ignored -> new HashMap<>());
        ResourceLocation dimensionId = destination.dimension().location();
        ResourceLocation typeId = destination.dimensionTypeId().location();
        for (int dx = -VIEW_RADIUS; dx <= VIEW_RADIUS; dx++) {
            for (int dz = -VIEW_RADIUS; dz <= VIEW_RADIUS; dz++) {
                int chunkX = centerX + dx;
                int chunkZ = centerZ + dz;
                String key = dimensionId + ":" + chunkX + ":" + chunkZ;
                Long last = playerCache.get(key);
                if (last != null && now - last < RESEND_INTERVAL) continue;
                LevelChunk chunk = destination.getChunkSource().getChunkNow(chunkX, chunkZ);
                if (chunk == null) continue;
                try {
                    ClientboundLevelChunkWithLightPacket packet = new ClientboundLevelChunkWithLightPacket(chunk, destination.getLightEngine(), null, null);
                    ByteBuf raw = Unpooled.buffer();
                    FriendlyByteBuf output = new FriendlyByteBuf(raw);
                    packet.write(output);
                    byte[] bytes = ByteBufUtil.getBytes(raw);
                    raw.release();
                    PortalControlNetwork.CHANNEL.send(PacketDistributor.PLAYER.with(player),
                        new RemoteChunkPacket(dimensionId, typeId, chunkX, chunkZ, bytes));
                    playerCache.put(key, now);
                } catch (RuntimeException ignored) {
                }
            }
        }
        if (playerCache.size() > 2048) playerCache.entrySet().removeIf(entry -> now - entry.getValue() > 1200L);
    }
    public static void forget(UUID player) { LAST_SENT.remove(player); }
}