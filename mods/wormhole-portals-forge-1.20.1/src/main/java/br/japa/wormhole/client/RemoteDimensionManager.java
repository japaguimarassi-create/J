package br.japa.wormhole.client;
import com.mojang.blaze3d.pipeline.TextureTarget;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.logging.LogUtils;
import io.netty.buffer.Unpooled;
import net.minecraft.client.Camera;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.renderer.LevelRenderer;
import net.minecraft.core.Holder;
import net.minecraft.core.SectionPos;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.network.protocol.game.ClientboundLevelChunkWithLightPacket;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.LightLayer;
import net.minecraft.world.level.dimension.DimensionType;
import net.minecraft.world.level.chunk.DataLayer;
import net.minecraft.world.level.lighting.LevelLightEngine;
import net.minecraft.world.phys.Vec3;
import br.japa.wormhole.portal.PortalEndpointEntity;
import br.japa.wormhole.network.RemoteEntitiesPacket.EntitySnapshot;
import net.minecraft.world.entity.Entity;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.fml.ModList;
import org.slf4j.Logger;
import java.util.BitSet;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
public final class RemoteDimensionManager {
    private static final Logger LOGGER = LogUtils.getLogger();
    private static final int TARGET_SIZE = 384;
    private static final int MAX_TARGETS = 4;
    private static RemoteWorld remote;
    private static long lastPacketTime;
    private static int packetsReceived;
    private static boolean renderingRemote;
    private static boolean rendererWarningSent;
    private static final Map<Integer, TextureTarget> TARGETS = new HashMap<>();
    private static final Map<Integer, Entity> REMOTE_ENTITIES = new HashMap<>();
    private static final PortalCamera PORTAL_CAMERA = new PortalCamera();
    private RemoteDimensionManager() {}

    public static void receive(ResourceLocation dimensionId, ResourceLocation dimensionTypeId, int chunkX, int chunkZ, byte[] payload) {
        Minecraft minecraft = Minecraft.getInstance();
        if (minecraft.level == null || minecraft.getConnection() == null) return;
        try {
            ensureWorld(minecraft, dimensionId, dimensionTypeId);
            io.netty.buffer.ByteBuf raw = Unpooled.wrappedBuffer(payload);
            ClientboundLevelChunkWithLightPacket packet;
            try {
                FriendlyByteBuf input = new FriendlyByteBuf(raw);
                packet = new ClientboundLevelChunkWithLightPacket(input);
            } finally {
                raw.release();
            }
            var chunkData = packet.getChunkData();
            remote.level.getChunkSource().replaceWithPacketData(packet.getX(), packet.getZ(), chunkData.getReadBuffer(),
                chunkData.getHeightmaps(), chunkData.getBlockEntitiesTagsConsumer(packet.getX(), packet.getZ()));
            applyLight(remote.level, packet);
            remote.renderer.setBlocksDirty(packet.getX() * 16, remote.level.getMinBuildHeight(), packet.getZ() * 16,
                packet.getX() * 16 + 15, remote.level.getMaxBuildHeight(), packet.getZ() * 16 + 15);
            remote.renderer.needsUpdate();
            remote.level.getChunkSource().updateViewCenter(packet.getX(), packet.getZ());
            lastPacketTime = System.currentTimeMillis();
            packetsReceived++;
        } catch (RuntimeException exception) {
            LOGGER.warn("Failed to apply remote dimension chunk {} {}, {}", dimensionId, chunkX, chunkZ, exception);
        }
    }

    private static void ensureWorld(Minecraft minecraft, ResourceLocation dimensionId, ResourceLocation typeId) {
        if (remote != null && remote.dimension.equals(dimensionId) && remote.dimensionType.equals(typeId)) return;
        closeRemoteWorld();
        ResourceKey<Level> dimensionKey = ResourceKey.create(Registries.DIMENSION, dimensionId);
        ResourceKey<DimensionType> typeKey = ResourceKey.create(Registries.DIMENSION_TYPE, typeId);
        Holder<DimensionType> type = minecraft.level.registryAccess().registryOrThrow(Registries.DIMENSION_TYPE).getHolderOrThrow(typeKey);
        LevelRenderer renderer = new LevelRenderer(minecraft, minecraft.getEntityRenderDispatcher(),
            minecraft.getBlockEntityRenderDispatcher(), minecraft.renderBuffers());
        ClientLevel.ClientLevelData data = new ClientLevel.ClientLevelData(minecraft.level.getDifficulty(), false, false);
        ClientLevel level = new ClientLevel(minecraft.getConnection(), data, dimensionKey, type, 4, 4,
            minecraft::getProfiler, renderer, false, 0L);
        renderer.setLevel(level);
        renderer.allChanged();
        level.getChunkSource().updateViewRadius(4);
        remote = new RemoteWorld(dimensionId, typeId, level, renderer);
        packetsReceived = 0;
    }

    public static void renderView(PortalEndpointEntity endpoint, float partialTick) {
        Minecraft minecraft = Minecraft.getInstance();
        if (isRendererUnsupported()) {
            if (!rendererWarningSent) {
                LOGGER.warn("Remote portal view disabled because Embeddium/Oculus is loaded; the native shell remains available.");
                rendererWarningSent = true;
            }
            return;
        }
        if (remote == null || minecraft.player == null || minecraft.level == null || !endpoint.isOpen()) return;
        if (packetsReceived == 0 || System.currentTimeMillis() - lastPacketTime > 6000L) return;
        if (!remote.dimension.equals(endpoint.destinationId())) return;
        TextureTarget target = targetFor(endpoint.getId());
        Vec3 playerEye = minecraft.player.getEyePosition(partialTick);
        Vec3 mappedEye = endpoint.targetPosition().add(playerEye.subtract(endpoint.position()));
        PORTAL_CAMERA.setupRemote(remote.level, minecraft.player, mappedEye, minecraft.player.getYRot(), minecraft.player.getXRot(), partialTick);
        target.setClearColor(0.005F, 0.008F, 0.025F, 1.0F);
        target.bindWrite(true);
        target.clear(false);
        renderingRemote = true;
        try {
            PoseStack stack = new PoseStack();
            float fov = minecraft.options.fov().get().floatValue();
            remote.renderer.renderLevel(stack, partialTick, System.nanoTime(), false, PORTAL_CAMERA,
                minecraft.gameRenderer, minecraft.gameRenderer.lightTexture(), minecraft.gameRenderer.getProjectionMatrix(fov));
        } catch (RuntimeException exception) {
            LOGGER.warn("Remote view rendering failed for portal {}", endpoint.linkId(), exception);
        } finally {
            renderingRemote = false;
            target.unbindWrite();
            minecraft.getMainRenderTarget().bindWrite(true);
        }
    }

    private static TextureTarget targetFor(int entityId) {
        TextureTarget existing = TARGETS.get(entityId);
        if (existing != null) return existing;
        if (TARGETS.size() >= MAX_TARGETS) {
            Integer first = TARGETS.keySet().iterator().next();
            TextureTarget removed = TARGETS.remove(first);
            if (removed != null) removed.destroyBuffers();
        }
        TextureTarget target = new TextureTarget(TARGET_SIZE, TARGET_SIZE, true, false);
        target.setFilterMode(9729);
        TARGETS.put(entityId, target);
        return target;
    }

    public static int textureId(int entityId) {
        TextureTarget target = TARGETS.get(entityId);
        return target == null ? -1 : target.getColorTextureId();
    }

    public static boolean hasRemoteView(PortalEndpointEntity endpoint) {
        return !isRendererUnsupported() && packetsReceived > 0
            && System.currentTimeMillis() - lastPacketTime <= 6000L
            && remote != null && remote.dimension.equals(endpoint.destinationId())
            && TARGETS.containsKey(endpoint.getId());
    }

    private static boolean isRendererUnsupported() {
        return ModList.get().isLoaded("embeddium") || ModList.get().isLoaded("oculus");
    }

    public static void pruneTargets(java.util.Set<Integer> activeIds) {
        var iterator = TARGETS.entrySet().iterator();
        while (iterator.hasNext()) {
            var entry = iterator.next();
            if (!activeIds.contains(entry.getKey())) {
                entry.getValue().destroyBuffers();
                iterator.remove();
            }
        }
    }

    public static void updateEntities(ResourceLocation dimensionId, List<EntitySnapshot> snapshots) {
        if (remote == null || !remote.dimension.equals(dimensionId)) return;
        java.util.Set<Integer> present = new java.util.HashSet<>();
        for (EntitySnapshot snapshot : snapshots) {
            present.add(snapshot.id());
            var type = ForgeRegistries.ENTITY_TYPES.getValue(snapshot.type());
            if (type == null || snapshot.type().equals(new ResourceLocation("minecraft", "player"))) continue;
            Entity entity = REMOTE_ENTITIES.get(snapshot.id());
            if (entity != null && entity.getType() != type) {
                remote.level.removeEntity(snapshot.id(), Entity.RemovalReason.DISCARDED);
                REMOTE_ENTITIES.remove(snapshot.id());
                entity = null;
            }
            if (entity == null) {
                entity = type.create(remote.level);
                if (entity == null) continue;
                try {
                    entity.load(snapshot.data());
                    remote.level.putNonPlayerEntity(snapshot.id(), entity);
                    REMOTE_ENTITIES.put(snapshot.id(), entity);
                } catch (RuntimeException exception) {
                    LOGGER.warn("Could not create remote entity type {}", snapshot.type(), exception);
                    entity.discard();
                }
            } else {
                try {
                    entity.load(snapshot.data());
                } catch (RuntimeException exception) {
                    LOGGER.warn("Could not update remote entity {}", snapshot.id(), exception);
                }
            }
        }
        for (EntitySnapshot snapshot : snapshots) {
            Entity passenger = REMOTE_ENTITIES.get(snapshot.id());
            Entity vehicle = REMOTE_ENTITIES.get(snapshot.vehicleId());
            if (snapshot.vehicleId() >= 0 && passenger != null && vehicle != null && passenger.getVehicle() != vehicle) {
                passenger.startRiding(vehicle, true);
            }
        }
        var iterator = REMOTE_ENTITIES.entrySet().iterator();
        while (iterator.hasNext()) {
            var entry = iterator.next();
            if (!present.contains(entry.getKey())) {
                remote.level.removeEntity(entry.getKey(), Entity.RemovalReason.DISCARDED);
                iterator.remove();
            }
        }
    }

    private static void applyLight(ClientLevel level, ClientboundLevelChunkWithLightPacket packet) {
        var data = packet.getLightData();
        LevelLightEngine light = level.getLightEngine();
        applyLayer(light, LightLayer.SKY, packet.getX(), packet.getZ(), light.getMinLightSection(), data.getSkyYMask(), data.getSkyUpdates());
        applyLayer(light, LightLayer.BLOCK, packet.getX(), packet.getZ(), light.getMinLightSection(), data.getBlockYMask(), data.getBlockUpdates());
        light.runLightUpdates();
    }

    private static void applyLayer(LevelLightEngine light, LightLayer layer, int chunkX, int chunkZ, int minSection, BitSet mask, List<byte[]> arrays) {
        int dataIndex = 0;
        for (int bit = mask.nextSetBit(0); bit >= 0; bit = mask.nextSetBit(bit + 1)) {
            if (dataIndex >= arrays.size()) break;
            SectionPos pos = SectionPos.of(chunkX, minSection + bit, chunkZ);
            light.queueSectionData(layer, pos, new DataLayer(arrays.get(dataIndex++).clone()));
        }
    }

    public static void tickRemoteEntities() {
        if (remote == null) return;
        for (Entity entity : List.copyOf(REMOTE_ENTITIES.values())) {
            if (!entity.isRemoved()) {
                try { entity.tick(); } catch (RuntimeException exception) {
                    LOGGER.debug("Remote entity tick failed for {}", entity.getId(), exception);
                }
            }
        }
    }

    public static boolean isRenderingRemote() { return renderingRemote; }

    public static ClientLevel level() { return remote == null ? null : remote.level; }
    public static LevelRenderer renderer() { return remote == null ? null : remote.renderer; }
    public static ResourceLocation dimension() { return remote == null ? null : remote.dimension; }
    public static int packetsReceived() { return packetsReceived; }
    public static long lastPacketTime() { return lastPacketTime; }

    public static void close() {
        closeRemoteWorld();
    }

    private static void closeRemoteWorld() {
        for (TextureTarget target : TARGETS.values()) {
            try { target.destroyBuffers(); } catch (RuntimeException ignored) { }
        }
        TARGETS.clear();
        REMOTE_ENTITIES.clear();
        if (remote != null) {
            try { remote.renderer.close(); } catch (Exception ignored) { }
            try { remote.level.close(); } catch (Exception ignored) { }
            remote = null;
        }
        packetsReceived = 0;
        lastPacketTime = 0L;
        rendererWarningSent = false;
    }

    private static final class PortalCamera extends Camera {
        private void setupRemote(ClientLevel level, Entity focus, Vec3 position, float yaw, float pitch, float partialTick) {
            setup(level, focus, false, false, partialTick);
            setPosition(position.x, position.y, position.z);
            setRotation(yaw, pitch);
        }
    }

    private record RemoteWorld(ResourceLocation dimension, ResourceLocation dimensionType, ClientLevel level, LevelRenderer renderer) {}
}