package br.japa.wormhole.portal;
import net.minecraft.core.BlockPos;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
public final class BubblePortalFactory {
    private BubblePortalFactory() {}
    public static String createPair(ServerLevel aWorld, Vec3 a, ServerLevel bWorld, Vec3 b, double radius, double range, boolean border) { return createPair(aWorld, a, bWorld, b, radius, range, border, UUID.randomUUID().toString()); }
    public static String createPair(ServerLevel aWorld, Vec3 a, ServerLevel bWorld, Vec3 b, double radius, double range, boolean border, String id) {
        validate(radius, range);
        PortalEndpointEntity first = new PortalEndpointEntity(br.japa.wormhole.WormholePortals.PORTAL_ENTITY.get(), aWorld); first.setPos(a); first.configure(id, 0, bWorld.dimension().location(), b, radius, range, border);
        PortalEndpointEntity second = new PortalEndpointEntity(br.japa.wormhole.WormholePortals.PORTAL_ENTITY.get(), bWorld); second.setPos(b); second.configure(id, 1, aWorld.dimension().location(), a, radius, range, border);
        if (!aWorld.addFreshEntity(first)) throw new IllegalStateException("Could not spawn first portal endpoint");
        if (!bWorld.addFreshEntity(second)) { first.discard(); throw new IllegalStateException("Could not spawn second portal endpoint"); }
        return id;
    }
    public static List<PortalEndpointEntity> allPortals(MinecraftServer server, String id) {
        List<PortalEndpointEntity> result = new ArrayList<>();
        for (ServerLevel level : server.getAllLevels()) for (Entity entity : level.getAllEntities()) if (entity instanceof PortalEndpointEntity portal && portal.linkId().equals(id)) result.add(portal);
        return result;
    }
    public static void removeLink(MinecraftServer server, String id) {
        PortalCarvingData.get(server).restoreLink(server, id);
        for (PortalEndpointEntity portal : allPortals(server, id)) portal.discard();
    }
    public static List<PortalEndpointEntity> findPortals(ServerLevel level, Vec3 point, double radius) { return level.getEntitiesOfClass(PortalEndpointEntity.class, new AABB(point, point).inflate(radius)); }
    public static PortalEndpointEntity findAnyTag(MinecraftServer server, String id) { List<PortalEndpointEntity> all = allPortals(server, id); return all.isEmpty() ? null : all.get(0); }
    public static void resize(MinecraftServer server, String id, double radius) { if (radius < 1 || radius > 8) throw new IllegalArgumentException("Radius must be 1–8 blocks"); for (PortalEndpointEntity p : allPortals(server, id)) p.setRadius(radius); }
    public static void setRange(MinecraftServer server, String id, double range) { if (range < 2 || range > 128) throw new IllegalArgumentException("Range must be 2–128 blocks"); for (PortalEndpointEntity p : allPortals(server, id)) p.setRange(range); }
    public static void setEnabled(MinecraftServer server, String id, boolean value) { for (PortalEndpointEntity p : allPortals(server, id)) { p.setEnabled(value); p.setOpen(false); } }
    public static void setBorder(MinecraftServer server, String id, boolean value) { for (PortalEndpointEntity p : allPortals(server, id)) p.setBorder(value); }
    public static void retarget(MinecraftServer server, String id, ServerLevel destination, Vec3 target) {
        List<PortalEndpointEntity> all = allPortals(server, id); if (all.size() != 2) throw new IllegalArgumentException("Portal pair is incomplete");
        PortalEndpointEntity source = all.get(0); ServerLevel sourceWorld = (ServerLevel) source.level(); Vec3 sourcePoint = source.position(); double radius = source.radius(), range = source.activationRange(); boolean border = source.hasBorder();
        PortalCarvingData.get(server).restoreLink(server, id);
        removeLink(server, id); createPair(sourceWorld, sourcePoint, destination, target, radius, range, border, id);
    }
    public static Vec3 defaultDestination(ServerLevel from, ServerLevel to, Vec3 source) {
        double x = source.x, z = source.z;
        if (from.dimension().equals(Level.OVERWORLD) && to.dimension().equals(Level.NETHER)) { x /= 8.0; z /= 8.0; }
        else if (from.dimension().equals(Level.NETHER) && to.dimension().equals(Level.OVERWORLD)) { x *= 8.0; z *= 8.0; }
        else if (!from.dimension().equals(to.dimension())) { BlockPos spawn = to.getSharedSpawnPos(); x = spawn.getX() + 0.5; z = spawn.getZ() + 0.5; }
        int bx = (int)Math.floor(x), bz = (int)Math.floor(z); int y = to.getHeight(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, bx, bz);
        y = Math.max(to.getMinBuildHeight() + 2, Math.min(to.getMaxBuildHeight() - 3, y + 1)); return new Vec3(bx + 0.5, y, bz + 0.5);
    }
    private static void validate(double radius, double range) { if (radius < 1 || radius > 8) throw new IllegalArgumentException("Radius must be 1–8 blocks"); if (range < radius + 1 || range > 128) throw new IllegalArgumentException("Activation range is out of bounds"); }
}