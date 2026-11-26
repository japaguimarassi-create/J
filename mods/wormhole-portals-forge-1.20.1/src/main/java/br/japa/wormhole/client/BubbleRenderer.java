package br.japa.wormhole.client;
import br.japa.wormhole.WormholePortals;
import br.japa.wormhole.portal.PortalEndpointEntity;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.RenderLevelStageEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.util.HashSet;
import java.util.Set;
@Mod.EventBusSubscriber(modid = WormholePortals.MOD_ID, bus = Mod.EventBusSubscriber.Bus.FORGE, value = Dist.CLIENT)
public final class BubbleRenderer {
    private BubbleRenderer() {}
    @SubscribeEvent public static void prepareRemoteViews(RenderLevelStageEvent event) {
        if (event.getStage() != RenderLevelStageEvent.Stage.AFTER_SKY || RemoteDimensionManager.isRenderingRemote()) return;
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null || mc.player == null) return;
        Set<Integer> active = new HashSet<>();
        for (Entity entity : mc.level.entitiesForRendering()) {
            if (!(entity instanceof PortalEndpointEntity portal) || !portal.isOpen()) continue;
            if (portal.distanceToSqr(mc.player) > portal.activationRange() * portal.activationRange()) continue;
            active.add(portal.getId());
            RemoteDimensionManager.renderView(portal, event.getPartialTick());
        }
        RemoteDimensionManager.pruneTargets(active);
    }
    @SubscribeEvent public static void renderPlacementPreview(RenderLevelStageEvent event) {
        if (event.getStage() != RenderLevelStageEvent.Stage.AFTER_TRANSLUCENT_BLOCKS || RemoteDimensionManager.isRenderingRemote()) return;
        Minecraft mc = Minecraft.getInstance(); if (mc.level == null || mc.player == null) return;
        ItemStack held = mc.player.getMainHandItem();
        if (!held.is(WormholePortals.PORTAL_ANCHOR.get())) return;
        if (mc.hitResult == null || mc.hitResult.getType() != net.minecraft.world.phys.HitResult.Type.BLOCK) return;
        BlockHitResult hit = (BlockHitResult) mc.hitResult;
        String mode = held.getTag() == null || held.getTag().getString("wormhole_anchor_mode").isBlank()
            ? "bubble" : held.getTag().getString("wormhole_anchor_mode");
        Direction normal = hit.getDirection();
        if (mode.equals("floor")) normal = Direction.UP;
        if (mode.equals("ceiling")) normal = Direction.DOWN;
        Vec3 center = Vec3.atCenterOf(hit.getBlockPos()).add(Vec3.atLowerCornerOf(normal.getNormal()).scale(0.55));
        boolean blocked = isPlacementBlocked(mc, center, normal, mode, 2.25)
            || mc.level.getEntitiesOfClass(Entity.class, new net.minecraft.world.phys.AABB(center, center).inflate(2.2),
                e -> e != mc.player && !(e instanceof PortalEndpointEntity)).size() > 0;
        PoseStack pose = event.getPoseStack(); Vec3 camera = event.getCamera().getPosition();
        pose.pushPose(); pose.translate(-camera.x, -camera.y, -camera.z);
        VertexConsumer lines = mc.renderBuffers().bufferSource().getBuffer(RenderType.lines());
        double radius = 2.25;
        for (int lat = 1; lat < 10; lat++) {
            double phi = Math.PI * lat / 10.0;
            for (int lon = 0; lon < 24; lon++) {
                double a = Math.PI * 2 * lon / 24.0, b = Math.PI * 2 * (lon + 1) / 24.0;
                Vec3 p1 = sphere(center, radius, phi, a), p2 = sphere(center, radius, phi, b);
                line(lines, pose, p1, p2, blocked ? 255 : 130, blocked ? 45 : 130, blocked ? 45 : 255, 210);
            }
        }
        mc.renderBuffers().bufferSource().endBatch(RenderType.lines()); pose.popPose();
    }
    private static boolean isPlacementBlocked(Minecraft mc, Vec3 center, Direction normal, String mode, double radius) {
        BlockPos origin = BlockPos.containing(center);
        int r = (int)Math.ceil(radius);
        if (mode.equals("bubble")) {
            for (int x = -r; x <= r; x++) for (int y = -r; y <= r; y++) for (int z = -r; z <= r; z++) {
                if (x*x + y*y + z*z > radius*radius) continue;
                BlockPos pos = origin.offset(x, y, z);
                if (!mc.level.hasChunkAt(pos)) return true;
                BlockState state = mc.level.getBlockState(pos);
                if (state.isAir()) continue;
                float hardness = state.getDestroySpeed(mc.level, pos);
                if (state.hasBlockEntity() || state.is(Blocks.BEDROCK) || state.is(Blocks.BARRIER) || hardness < 0 || hardness > 1.5F) return true;
            }
            return false;
        }
        int ux, uy, uz, vx, vy, vz;
        if (normal.getAxis() == Direction.Axis.X) {
            ux=0; uy=1; uz=0; vx=0; vy=0; vz=1;
        } else if (normal.getAxis() == Direction.Axis.Y) {
            ux=1; uy=0; uz=0; vx=0; vy=0; vz=1;
        } else {
            ux=1; uy=0; uz=0; vx=0; vy=1; vz=0;
        }
        for (int u=-r; u<=r; u++) for (int v=-r; v<=r; v++) {
            if (u*u+v*v > radius*radius) continue;
            for (int depth=-1; depth<=1; depth++) {
                BlockPos pos=origin.offset(ux*u+vx*v+normal.getStepX()*depth,
                    uy*u+vy*v+normal.getStepY()*depth, uz*u+vz*v+normal.getStepZ()*depth);
                if (!mc.level.hasChunkAt(pos)) return true;
                BlockState state=mc.level.getBlockState(pos);
                if (state.isAir()) continue;
                if (state.hasBlockEntity() || state.is(Blocks.BEDROCK) || state.is(Blocks.BARRIER)
                    || state.getDestroySpeed(mc.level, pos) < 0) return true;
            }
        }
        return false;
    }

    private static Vec3 sphere(Vec3 c, double r, double phi, double theta) {
        double s = Math.sin(phi); return c.add(r*s*Math.cos(theta), r*Math.cos(phi), r*s*Math.sin(theta));
    }
    private static void line(VertexConsumer out, PoseStack stack, Vec3 a, Vec3 b, int r, int g, int blue, int alpha) {
        PoseStack.Pose p = stack.last();
        out.vertex(p.pose(), (float)a.x, (float)a.y, (float)a.z).color(r,g,blue,alpha).normal(p.normal(),0,1,0).endVertex();
        out.vertex(p.pose(), (float)b.x, (float)b.y, (float)b.z).color(r,g,blue,alpha).normal(p.normal(),0,1,0).endVertex();
    }
}