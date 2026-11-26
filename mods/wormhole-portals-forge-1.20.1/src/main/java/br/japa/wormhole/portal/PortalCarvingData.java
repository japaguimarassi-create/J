package br.japa.wormhole.portal;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.Registries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.NbtUtils;
import net.minecraft.nbt.Tag;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.saveddata.SavedData;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Set;
public final class PortalCarvingData extends SavedData {
    private static final String DATA_NAME = "frameless_style_portal_carves";
    private final List<CompoundTag> entries = new ArrayList<>();
    private final Set<String> recorded = new HashSet<>();
    public static PortalCarvingData get(MinecraftServer server) {
        return server.overworld().getDataStorage().computeIfAbsent(PortalCarvingData::load, PortalCarvingData::new, DATA_NAME);
    }
    private static PortalCarvingData load(CompoundTag root) {
        PortalCarvingData data = new PortalCarvingData();
        ListTag list = root.getList("Entries", Tag.TAG_COMPOUND);
        for (int i = 0; i < list.size(); i++) {
            CompoundTag entry = list.getCompound(i);
            data.entries.add(entry.copy());
            data.recorded.add(entry.getString("Dimension") + "|" + entry.getLong("Position"));
        }
        return data;
    }
    @Override public CompoundTag save(CompoundTag root) {
        ListTag list = new ListTag();
        for (CompoundTag entry : entries) list.add(entry.copy());
        root.put("Entries", list);
        return root;
    }
    public void carveSurface(ServerLevel level, String linkId, Vec3Center center, Direction normal, String mode, double radius) {
        int r = Math.max(1, Math.min(8, (int)Math.ceil(radius)));
        BlockPos origin = BlockPos.containing(center.x(), center.y(), center.z());
        boolean softOnly = mode.equals("bubble");
        if (softOnly) {
            for (int x = -r; x <= r; x++) for (int y = -r; y <= r; y++) for (int z = -r; z <= r; z++) {
                if (x*x + y*y + z*z > radius*radius) continue;
                carveOne(level, linkId, origin.offset(x, y, z), true);
            }
            return;
        }
        int ux;
        int uy;
        int uz;
        int vx;
        int vy;
        int vz;
        if (normal.getAxis() == Direction.Axis.X) {
            ux = 0; uy = 1; uz = 0;
            vx = 0; vy = 0; vz = 1;
        } else if (normal.getAxis() == Direction.Axis.Y) {
            ux = 1; uy = 0; uz = 0;
            vx = 0; vy = 0; vz = 1;
        } else {
            ux = 1; uy = 0; uz = 0;
            vx = 0; vy = 1; vz = 0;
        }
        for (int u = -r; u <= r; u++) for (int v = -r; v <= r; v++) {
            if (u*u + v*v > radius*radius) continue;
            for (int depth = -1; depth <= 1; depth++) {
                BlockPos pos = origin.offset(ux*u + vx*v + normal.getStepX()*depth, uy*u + vy*v + normal.getStepY()*depth, uz*u + vz*v + normal.getStepZ()*depth);
                carveOne(level, linkId, pos, false);
            }
        }
    }
    private void carveOne(ServerLevel level, String linkId, BlockPos pos, boolean softOnly) {
        if (!level.hasChunkAt(pos)) return;
        BlockState state = level.getBlockState(pos);
        if (state.isAir() || state.hasBlockEntity() || state.is(Blocks.BEDROCK) || state.is(Blocks.BARRIER)) return;
        float hardness = state.getDestroySpeed(level, pos);
        if (hardness < 0 || (softOnly && hardness > 1.5F)) return;
        String key = level.dimension().location() + "|" + pos.asLong();
        if (!recorded.add(key)) return;
        CompoundTag entry = new CompoundTag();
        entry.putString("Link", linkId);
        entry.putString("Dimension", level.dimension().location().toString());
        entry.putLong("Position", pos.asLong());
        entry.put("State", NbtUtils.writeBlockState(state));
        entries.add(entry);
        level.setBlock(pos, Blocks.AIR.defaultBlockState(), 3);
        setDirty();
    }
    public void restoreLink(MinecraftServer server, String linkId) { restore(server, linkId); }
    public void restoreAll(MinecraftServer server) { restore(server, null); }
    private void restore(MinecraftServer server, String linkId) {
        Iterator<CompoundTag> iterator = entries.iterator();
        while (iterator.hasNext()) {
            CompoundTag entry = iterator.next();
            if (linkId != null && !entry.getString("Link").equals(linkId)) continue;
            ResourceLocation dimension = ResourceLocation.tryParse(entry.getString("Dimension"));
            ServerLevel level = dimension == null ? null : server.getLevel(ResourceKey.create(Registries.DIMENSION, dimension));
            if (level == null) continue;
            BlockPos pos = BlockPos.of(entry.getLong("Position"));
            if (!level.hasChunkAt(pos)) continue;
            if (level.getBlockState(pos).isAir()) {
                BlockState original = NbtUtils.readBlockState(level.registryAccess().lookupOrThrow(Registries.BLOCK), entry.getCompound("State"));
                level.setBlock(pos, original, 3);
            }
            recorded.remove(entry.getString("Dimension") + "|" + entry.getLong("Position"));
            iterator.remove();
            setDirty();
        }
    }
    public record Vec3Center(double x, double y, double z) {}
}