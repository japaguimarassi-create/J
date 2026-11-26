package br.japa.wormhole.client;

import br.japa.wormhole.portal.BubbleTag;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.RenderLevelStageEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import qouteall.imm_ptl.core.portal.Portal;

import java.util.HashSet;
import java.util.Set;

@Mod.EventBusSubscriber(modid = "wormhole_portals", bus = Mod.EventBusSubscriber.Bus.FORGE, value = Dist.CLIENT)
public final class BubbleRenderer {
    private BubbleRenderer() {}

    @SubscribeEvent
    public static void renderClosedBubbles(RenderLevelStageEvent event) {
        if (event.getStage() != RenderLevelStageEvent.Stage.AFTER_TRANSLUCENT_BLOCKS) return;
        Minecraft minecraft = Minecraft.getInstance();
        if (minecraft.level == null || minecraft.player == null) return;

        Vec3 camera = event.getCamera().getPosition();
        PoseStack pose = event.getPoseStack();
        pose.pushPose();
        pose.translate(-camera.x, -camera.y, -camera.z);
        VertexConsumer lines = minecraft.renderBuffers().bufferSource().getBuffer(RenderType.lines());
        Set<String> rendered = new HashSet<>();

        for (Entity entity : minecraft.level.entitiesForRendering()) {
            if (!(entity instanceof Portal portal)) continue;
            if (portal.isVisible()) continue;
            BubbleTag tag = BubbleTag.parse(portal.portalTag);
            if (tag == null) continue;
            String group = tag.linkId() + ":" + tag.side();
            if (!rendered.add(group)) continue;
            drawShell(lines, pose, tag.center(), tag.radius(), minecraft.level.getGameTime());
        }

        minecraft.renderBuffers().bufferSource().endBatch(RenderType.lines());
        pose.popPose();
    }

    private static void drawShell(VertexConsumer lines, PoseStack pose, Vec3 center, double radius, long ticks) {
        double pulse = 0.65 + 0.18 * Math.sin(ticks * 0.12);
        int alpha = (int) (150 * pulse);
        int latitudeCount = 7;
        int longitudeCount = 20;
        for (int lat = 1; lat < latitudeCount; lat++) {
            double phi = Math.PI * lat / latitudeCount;
            for (int lon = 0; lon < longitudeCount; lon++) {
                double t1 = Math.PI * 2.0 * lon / longitudeCount;
                double t2 = Math.PI * 2.0 * (lon + 1) / longitudeCount;
                Vec3 p1 = sphere(center, radius, phi, t1);
                Vec3 p2 = sphere(center, radius, phi, t2);
                line(lines, pose, p1, p2, 95, 210, 255, alpha);
            }
        }
        for (int lon = 0; lon < longitudeCount; lon += 2) {
            double theta = Math.PI * 2.0 * lon / longitudeCount;
            for (int lat = 0; lat < latitudeCount; lat++) {
                double p1 = Math.PI * lat / latitudeCount;
                double p2 = Math.PI * (lat + 1) / latitudeCount;
                line(lines, pose, sphere(center, radius, p1, theta), sphere(center, radius, p2, theta), 165, 125, 255, alpha);
            }
        }
    }

    private static Vec3 sphere(Vec3 center, double radius, double phi, double theta) {
        double sin = Math.sin(phi);
        return center.add(
            radius * sin * Math.cos(theta),
            radius * Math.cos(phi),
            radius * sin * Math.sin(theta)
        );
    }

    private static void line(VertexConsumer consumer, PoseStack pose, Vec3 a, Vec3 b, int r, int g, int blue, int alpha) {
        PoseStack.Pose last = pose.last();
        consumer.vertex(last.pose(), (float) a.x, (float) a.y, (float) a.z)
            .color(r, g, blue, alpha)
            .normal(last.normal(), 0.0F, 1.0F, 0.0F)
            .endVertex();
        consumer.vertex(last.pose(), (float) b.x, (float) b.y, (float) b.z)
            .color(r, g, blue, alpha)
            .normal(last.normal(), 0.0F, 1.0F, 0.0F)
            .endVertex();
    }
}
