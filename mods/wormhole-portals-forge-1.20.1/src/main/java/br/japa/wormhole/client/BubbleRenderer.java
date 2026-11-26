package br.japa.wormhole.client;
import br.japa.wormhole.WormholePortals;
import br.japa.wormhole.portal.PortalEndpointEntity;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.RenderType;
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
        if (event.getStage() != RenderLevelStageEvent.Stage.AFTER_SKY) return;
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
        if (event.getStage() != RenderLevelStageEvent.Stage.AFTER_TRANSLUCENT_BLOCKS) return;
        Minecraft mc = Minecraft.getInstance(); if (mc.level == null || mc.player == null) return;
        ItemStack held = mc.player.getMainHandItem();
        if (!held.is(WormholePortals.PORTAL_ANCHOR.get())) return;
        if (mc.hitResult == null || mc.hitResult.getType() != net.minecraft.world.phys.HitResult.Type.BLOCK) return;
        Vec3 center = mc.hitResult.getLocation().add(mc.player.getLookAngle().scale(0.1));
        boolean blocked = mc.level.getEntitiesOfClass(Entity.class, new net.minecraft.world.phys.AABB(center, center).inflate(2.2), e -> e != mc.player && !(e instanceof PortalEndpointEntity)).size() > 0;
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
    private static Vec3 sphere(Vec3 c, double r, double phi, double theta) {
        double s = Math.sin(phi); return c.add(r*s*Math.cos(theta), r*Math.cos(phi), r*s*Math.sin(theta));
    }
    private static void line(VertexConsumer out, PoseStack stack, Vec3 a, Vec3 b, int r, int g, int blue, int alpha) {
        PoseStack.Pose p = stack.last();
        out.vertex(p.pose(), (float)a.x, (float)a.y, (float)a.z).color(r,g,blue,alpha).normal(p.normal(),0,1,0).endVertex();
        out.vertex(p.pose(), (float)b.x, (float)b.y, (float)b.z).color(r,g,blue,alpha).normal(p.normal(),0,1,0).endVertex();
    }
}