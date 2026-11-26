package br.japa.wormhole.portal;

import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import qouteall.imm_ptl.core.api.PortalAPI;
import qouteall.imm_ptl.core.platform_specific.IPRegistry;
import qouteall.imm_ptl.core.portal.GeometryPortalShape;
import qouteall.imm_ptl.core.portal.Portal;
import qouteall.q_misc_util.my_util.DQuaternion;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

public final class BubblePortalFactory {
    private static final double PHI = (1.0 + Math.sqrt(5.0)) / 2.0;
    private static final Vec3[] VERTICES = createVertices();
    private static final int[][] FACES = {
        {0, 11, 5}, {0, 5, 1}, {0, 1, 7}, {0, 7, 10}, {0, 10, 11},
        {1, 5, 9}, {5, 11, 4}, {11, 10, 2}, {10, 7, 6}, {7, 1, 8},
        {3, 9, 4}, {3, 4, 2}, {3, 2, 6}, {3, 6, 8}, {3, 8, 9},
        {4, 9, 5}, {2, 4, 11}, {6, 2, 10}, {8, 6, 7}, {9, 8, 1}
    };

    private BubblePortalFactory() {}

    public static String createPair(ServerLevel firstWorld, Vec3 firstCenter, ServerLevel secondWorld,
                                    Vec3 secondCenter, double radius, double activationRange, boolean border) {
        return createPair(firstWorld, firstCenter, secondWorld, secondCenter, radius, activationRange, border, UUID.randomUUID().toString());
    }

    public static String createPair(ServerLevel firstWorld, Vec3 firstCenter, ServerLevel secondWorld,
                                    Vec3 secondCenter, double radius, double activationRange, boolean border, String linkId) {
        if (radius < 1.0 || radius > 8.0) throw new IllegalArgumentException("Radius must be between 1 and 8 blocks");
        if (activationRange < radius + 1.0 || activationRange > 128.0) throw new IllegalArgumentException("Activation range is out of bounds");

        for (int[] face : FACES) {
            Vec3 a = VERTICES[face[0]];
            Vec3 b = VERTICES[face[1]];
            Vec3 c = VERTICES[face[2]];
            Vec3 normal = b.subtract(a).cross(c.subtract(a)).normalize();
            Vec3 faceCenter = a.add(b).add(c).scale(1.0 / 3.0).normalize();
            if (normal.dot(faceCenter) < 0) {
                Vec3 swap = b;
                b = c;
                c = swap;
            }
            createFacePair(firstWorld, firstCenter, secondWorld, secondCenter, radius, activationRange, border, linkId, "a", a, b, c, faceCenter);
        }
        return linkId;
    }

    private static void createFacePair(ServerLevel fromWorld, Vec3 fromCenter, ServerLevel toWorld, Vec3 toCenter,
                                       double radius, double range, boolean border, String linkId, String side,
                                       Vec3 a, Vec3 b, Vec3 c, Vec3 faceCenter) {
        Vec3 center = fromCenter.add(faceCenter.scale(radius));
        Vec3 target = toCenter.add(faceCenter.scale(radius));
        Vec3 axisW = b.subtract(a).normalize();
        Vec3 normal = faceCenter.normalize();
        Vec3 axisH = normal.cross(axisW).normalize();
        if (axisW.cross(axisH).dot(normal) < 0) axisH = axisH.scale(-1);

        Vec3 pa = a.subtract(faceCenter).scale(radius);
        Vec3 pb = b.subtract(faceCenter).scale(radius);
        Vec3 pc = c.subtract(faceCenter).scale(radius);
        double width = Math.max(0.05, 2.0 * Math.max(Math.abs(pa.dot(axisW)), Math.max(Math.abs(pb.dot(axisW)), Math.abs(pc.dot(axisW)))) + 0.02);
        double height = Math.max(0.05, 2.0 * Math.max(Math.abs(pa.dot(axisH)), Math.max(Math.abs(pb.dot(axisH)), Math.abs(pc.dot(axisH)))) + 0.02);

        Portal portal = new Portal(IPRegistry.PORTAL.get(), fromWorld);
        PortalAPI.setPortalPositionOrientationAndSize(portal, center, DQuaternion.fromFacingVecs(axisW, axisH), width, height);
        PortalAPI.setPortalTransformation(portal, toWorld.dimension(), target, null, 1.0);
        portal.specialShape = triangleShape(pa.dot(axisW), pa.dot(axisH), pb.dot(axisW), pb.dot(axisH), pc.dot(axisW), pc.dot(axisH));
        portal.setTeleportable(false);
        portal.setIsVisible(false);
        portal.portalTag = new BubbleTag(linkId, side, fromWorld.dimension().location(), toWorld.dimension().location(),
            fromCenter, toCenter, radius, range, border, true).encode();

        Portal reverse = PortalAPI.createReversePortal(portal);
        String reverseSide = side.equals("a") ? "b" : "a";
        reverse.portalTag = new BubbleTag(linkId, reverseSide, toWorld.dimension().location(), fromWorld.dimension().location(),
            toCenter, fromCenter, radius, range, border, true).encode();
        for (Portal portalEntity : List.of(portal, reverse)) {
            portalEntity.setTeleportable(false);
            portalEntity.setIsVisible(false);
            portalEntity.setInteractable(false);
        }

        PortalAPI.spawnServerEntity(portal);
        PortalAPI.spawnServerEntity(reverse);
        portal.reloadAndSyncToClient();
        reverse.reloadAndSyncToClient();
    }

    private static GeometryPortalShape triangleShape(double x1, double y1, double x2, double y2, double x3, double y3) {
        GeometryPortalShape shape = new GeometryPortalShape();
        shape.triangles.add(new GeometryPortalShape.TriangleInPlane(x1, y1, x2, y2, x3, y3));
        return shape;
    }

    public static void removeLink(MinecraftServer server, String linkId) {
        for (ServerLevel level : server.getAllLevels()) {
            for (net.minecraft.world.entity.Entity entity : toList(level.getAllEntities())) {
                if (!(entity instanceof Portal portal)) continue;
                BubbleTag tag = BubbleTag.parse(portal.portalTag);
                if (tag != null && tag.linkId().equals(linkId)) portal.discard();
            }
        }
    }

    private static List<net.minecraft.world.entity.Entity> toList(Iterable<net.minecraft.world.entity.Entity> entities) {
        List<net.minecraft.world.entity.Entity> result = new ArrayList<>();
        for (net.minecraft.world.entity.Entity entity : entities) result.add(entity);
        return result;
    }

    public static List<Portal> findPortals(ServerLevel level, Vec3 position, double radius) {
        AABB area = new AABB(position, position).inflate(radius);
        return level.getEntitiesOfClass(Portal.class, area, portal -> BubbleTag.parse(portal.portalTag) != null);
    }

    public static BubbleTag findAnyTag(MinecraftServer server, String linkId) {
        BubbleTag fallback = null;
        for (ServerLevel level : server.getAllLevels()) {
            for (net.minecraft.world.entity.Entity entity : level.getAllEntities()) {
                if (!(entity instanceof Portal portal)) continue;
                BubbleTag tag = BubbleTag.parse(portal.portalTag);
                if (tag == null || !tag.linkId().equals(linkId)) continue;
                if (tag.side().equals("a")) return tag;
                fallback = tag;
            }
        }
        return fallback;
    }

    public static void setRange(MinecraftServer server, String linkId, double range) {
        if (range < 2 || range > 128) throw new IllegalArgumentException("Range must be between 2 and 128 blocks");
        updateTags(server, linkId, tag -> tag.withRange(range));
    }

    public static void setEnabled(MinecraftServer server, String linkId, boolean enabled) {
        updateTags(server, linkId, tag -> tag.withEnabled(enabled));
    }

    public static void setScale(MinecraftServer server, String linkId, double scale) {
        if (scale < 0.25 || scale > 4.0) throw new IllegalArgumentException("Scale must be between 0.25 and 4.0");
        for (ServerLevel level : server.getAllLevels()) {
            for (net.minecraft.world.entity.Entity entity : level.getAllEntities()) {
                if (!(entity instanceof Portal portal)) continue;
                BubbleTag tag = BubbleTag.parse(portal.portalTag);
                if (tag == null || !tag.linkId().equals(linkId)) continue;
                portal.setScaleTransformation(tag.side().equals("a") ? scale : 1.0 / scale);
                portal.reloadAndSyncToClient();
            }
        }
    }

    public static void retarget(MinecraftServer server, String linkId, ServerLevel destination, Vec3 targetCenter) {
        BubbleTag source = findSideTag(server, linkId, "a");
        if (source == null) return;
        ServerLevel from = server.getLevel(ResourceKey.create(Registries.DIMENSION, source.sourceDimension()));
        if (from == null) return;
        removeLink(server, linkId);
        createPair(from, source.center(), destination, targetCenter, source.radius(), source.activationRange(), source.border(), linkId);
    }

    private static void updateTags(MinecraftServer server, String linkId, java.util.function.UnaryOperator<BubbleTag> update) {
        for (ServerLevel level : server.getAllLevels()) {
            for (net.minecraft.world.entity.Entity entity : level.getAllEntities()) {
                if (!(entity instanceof Portal portal)) continue;
                BubbleTag tag = BubbleTag.parse(portal.portalTag);
                if (tag == null || !tag.linkId().equals(linkId)) continue;
                portal.portalTag = update.apply(tag).encode();
                portal.reloadAndSyncToClient();
            }
        }
    }

    public static void resize(MinecraftServer server, String linkId, double radius) {
        if (radius < 1 || radius > 8) throw new IllegalArgumentException("Radius must be between 1 and 8 blocks");
        BubbleTag data = findSideTag(server, linkId, "a");
        if (data == null) return;
        ServerLevel sourceWorld = server.getLevel(ResourceKey.create(Registries.DIMENSION, data.sourceDimension()));
        ServerLevel targetWorld = server.getLevel(ResourceKey.create(Registries.DIMENSION, data.destinationDimension()));
        if (sourceWorld == null || targetWorld == null) return;
        removeLink(server, linkId);
        createPair(sourceWorld, data.center(), targetWorld, data.targetCenter(), radius, data.activationRange(), data.border(), linkId);
    }

    private static BubbleTag findSideTag(MinecraftServer server, String linkId, String side) {
        for (ServerLevel level : server.getAllLevels()) {
            for (net.minecraft.world.entity.Entity entity : level.getAllEntities()) {
                if (!(entity instanceof Portal portal)) continue;
                BubbleTag tag = BubbleTag.parse(portal.portalTag);
                if (tag != null && tag.linkId().equals(linkId) && tag.side().equals(side)) return tag;
            }
        }
        return null;
    }

    public static Vec3 defaultDestination(ServerLevel from, ServerLevel to, Vec3 source) {
        double x = source.x;
        double z = source.z;
        if (from.dimension().equals(Level.OVERWORLD) && to.dimension().equals(Level.NETHER)) {
            x /= 8.0;
            z /= 8.0;
        } else if (from.dimension().equals(Level.NETHER) && to.dimension().equals(Level.OVERWORLD)) {
            x *= 8.0;
            z *= 8.0;
        } else if (to.dimension().equals(Level.END)) {
            BlockPos spawn = to.getSharedSpawnPos();
            x = spawn.getX() + 0.5;
            z = spawn.getZ() + 0.5;
        } else if (!from.dimension().equals(to.dimension())) {
            BlockPos spawn = to.getSharedSpawnPos();
            x = spawn.getX() + 0.5;
            z = spawn.getZ() + 0.5;
        }
        int bx = (int) Math.floor(x);
        int bz = (int) Math.floor(z);
        int y = to.getHeight(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, bx, bz);
        y = Math.max(to.getMinBuildHeight() + 2, Math.min(to.getMaxBuildHeight() - 3, y + 1));
        return new Vec3(bx + 0.5, y, bz + 0.5);
    }

    private static Vec3[] createVertices() {
        return new Vec3[] {
            new Vec3(-1, PHI, 0).normalize(), new Vec3(1, PHI, 0).normalize(),
            new Vec3(-1, -PHI, 0).normalize(), new Vec3(1, -PHI, 0).normalize(),
            new Vec3(0, -1, PHI).normalize(), new Vec3(0, 1, PHI).normalize(),
            new Vec3(0, -1, -PHI).normalize(), new Vec3(0, 1, -PHI).normalize(),
            new Vec3(PHI, 0, -1).normalize(), new Vec3(PHI, 0, 1).normalize(),
            new Vec3(-PHI, 0, -1).normalize(), new Vec3(-PHI, 0, 1).normalize()
        };
    }
}
