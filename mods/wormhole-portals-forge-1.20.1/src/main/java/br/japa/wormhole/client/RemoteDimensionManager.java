package br.japa.wormhole.client;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.logging.LogUtils;
import io.netty.buffer.Unpooled;
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
import net.minecraft.world.level.Level;
import net.minecraft.world.level.LightLayer;
import net.minecraft.world.level.dimension.DimensionType;
import net.minecraft.world.level.chunk.DataLayer;
import net.minecraft.world.level.lighting.LevelLightEngine;
import org.slf4j.Logger;
import java.util.BitSet;
import java.util.List;
public final class RemoteDimensionManager {
    private static final Logger LOGGER = LogUtils.getLogger();
    private static RemoteWorld remote;
    private static long lastPacketTime;
    private static int packetsReceived;
    private RemoteDimensionManager() {}
    public static void receive(ResourceLocation dimensionId, ResourceLocation dimensionTypeId, int chunkX, int chunkZ, byte[] payload) {
        Minecraft minecraft = Minecraft.getInstance();
        if (minecraft.level == null || minecraft.getConnection() == null) return;
        try {
            ensureWorld(minecraft, dimensionId, dimensionTypeId);
            FriendlyByteBuf input = new FriendlyByteBuf(Unpooled.wrappedBuffer(payload));
            ClientboundLevelChunkWithLightPacket packet = new ClientboundLevelChunkWithLightPacket(input);
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
        close();
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
    public static ClientLevel level() { return remote == null ? null : remote.level; }
    public static LevelRenderer renderer() { return remote == null ? null : remote.renderer; }
    public static ResourceLocation dimension() { return remote == null ? null : remote.dimension; }
    public static int packetsReceived() { return packetsReceived; }
    public static long lastPacketTime() { return lastPacketTime; }
    public static void close() {
        if (remote != null) {
            try { remote.renderer.close(); } catch (Exception ignored) { }
            try { remote.level.close(); } catch (Exception ignored) { }
            remote = null;
        }
        packetsReceived = 0;
        lastPacketTime = 0L;
    }
    private record RemoteWorld(ResourceLocation dimension, ResourceLocation dimensionType, ClientLevel level, LevelRenderer renderer) {}
}