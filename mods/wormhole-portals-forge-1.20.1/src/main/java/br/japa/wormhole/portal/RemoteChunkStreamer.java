package br.japa.wormhole.portal;
import br.japa.wormhole.network.PortalControlNetwork;
import br.japa.wormhole.network.RemoteChunkPacket;
import br.japa.wormhole.network.RemoteEntitiesPacket;
import io.netty.buffer.ByteBuf;
import io.netty.buffer.ByteBufUtil;
import io.netty.buffer.Unpooled;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.network.protocol.game.ClientboundLevelChunkWithLightPacket;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.minecraft.world.level.chunk.LevelChunk;
import net.minecraftforge.network.PacketDistributor;
import net.minecraftforge.registries.ForgeRegistries;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
public final class RemoteChunkStreamer {
    private static final Map<UUID, Map<String, Long>> LAST_SENT = new HashMap<>();
    private static final Map<UUID, Map<String, Long>> LAST_ENTITY_SENT = new HashMap<>();
    private static final int VIEW_RADIUS = 1;
    private static final long RESEND_INTERVAL = 40L;
    private static final long ENTITY_SYNC_INTERVAL = 5L;
    private static final int MAX_REMOTE_ENTITIES = 64;
    private RemoteChunkStreamer() {}
    public static void sync(ServerLevel source, PortalEndpointEntity endpoint, ServerPlayer player) {
        ServerLevel destination = source.getServer().getLevel(net.minecraft.resources.ResourceKey.create(net.minecraft.core.registries.Registries.DIMENSION, endpoint.destinationId()));
        if (destination == null) return;
        Vec3 remotePoint = endpoint.targetPosition().add(player.position().subtract(endpoint.position()));
        int centerX = net.minecraft.core.BlockPos.containing(remotePoint).getX() >> 4;
        int centerZ = net.minecraft.core.BlockPos.containing(remotePoint).getZ() >> 4;
        long now = source.getGameTime();
        Map<String, Long> playerCache = LAST_SENT.computeIfAbsent(player.getUUID(), ignored -> new HashMap<>());
        ResourceLocation dimensionId = destination.dimension().location();
        ResourceLocation typeId = destination.dimensionTypeId().location();
        for (int dx = -VIEW_RADIUS; dx <= VIEW_RADIUS; dx++) {
            for (int dz = -VIEW_RADIUS; dz <= VIEW_RADIUS; dz++) {
                int chunkX = centerX + dx, chunkZ = centerZ + dz;
                String key = dimensionId + ":" + chunkX + ":" + chunkZ;
                Long last = playerCache.get(key);
                if (last != null && now - last < RESEND_INTERVAL) continue;
                LevelChunk chunk = destination.getChunkSource().getChunkNow(chunkX, chunkZ);
                if (chunk == null) continue;
                ByteBuf raw = Unpooled.buffer();
                try {
                    ClientboundLevelChunkWithLightPacket packet = new ClientboundLevelChunkWithLightPacket(chunk, destination.getLightEngine(), null, null);
                    packet.write(new FriendlyByteBuf(raw));
                    byte[] bytes = ByteBufUtil.getBytes(raw);
                    PortalControlNetwork.CHANNEL.send(PacketDistributor.PLAYER.with(() -> player), new RemoteChunkPacket(dimensionId, typeId, chunkX, chunkZ, bytes));
                    playerCache.put(key, now);
                } catch (RuntimeException ignored) {
                } finally {
                    raw.release();
                }
            }
        }
        syncEntities(destination, remotePoint, player, now, dimensionId);
        if (playerCache.size() > 2048) playerCache.entrySet().removeIf(entry -> now - entry.getValue() > 1200L);
    }
    private static void syncEntities(ServerLevel destination, Vec3 center, ServerPlayer player, long now, ResourceLocation dimension) {
        Map<String, Long> cache = LAST_ENTITY_SENT.computeIfAbsent(player.getUUID(), ignored -> new HashMap<>());
        String dimensionKey = dimension.toString();
        Long last = cache.get(dimensionKey);
        if (last != null && now - last < ENTITY_SYNC_INTERVAL) return;
        AABB area = AABB.ofSize(center, 48.0, 64.0, 48.0);
        List<Entity> nearby = destination.getEntitiesOfClass(Entity.class, area, entity ->
            !(entity instanceof Player) && !(entity instanceof PortalEndpointEntity) && !(entity instanceof PortalOrbEntity) && !entity.isRemoved());
        nearby.sort(Comparator.comparingDouble(entity -> entity.distanceToSqr(center)));
        List<RemoteEntitiesPacket.EntitySnapshot> snapshots = new ArrayList<>();
        for (Entity entity : nearby) {
            if (snapshots.size() >= MAX_REMOTE_ENTITIES) break;
            ResourceLocation typeId = ForgeRegistries.ENTITY_TYPES.getKey(entity.getType());
            if (typeId == null) continue;
            try {
                CompoundTag data = entity.saveWithoutId(new CompoundTag());
                snapshots.add(new RemoteEntitiesPacket.EntitySnapshot(entity.getId(), typeId, data));
            } catch (RuntimeException ignored) {
            }
        }
        PortalControlNetwork.CHANNEL.send(PacketDistributor.PLAYER.with(() -> player), new RemoteEntitiesPacket(dimension, snapshots));
        cache.put(dimensionKey, now);
        if (cache.size() > 32) cache.entrySet().removeIf(entry -> now - entry.getValue() > 1200L);
    }
    public static void forget(UUID player) { LAST_SENT.remove(player); LAST_ENTITY_SENT.remove(player); }
}