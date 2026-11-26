package br.japa.wormhole.client;
import br.japa.wormhole.portal.PortalOrbEntity;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.entity.EntityRenderer;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.phys.Vec3;
public final class PortalOrbRenderer extends EntityRenderer<PortalOrbEntity> {
    private static final ResourceLocation TEXTURE = new ResourceLocation("minecraft", "textures/block/crying_obsidian.png");
    public PortalOrbRenderer(EntityRendererProvider.Context context) { super(context); shadowRadius = 0.0F; }
    @Override public void render(PortalOrbEntity entity, float yaw, float partialTick, PoseStack pose, MultiBufferSource buffers, int packedLight) {
        pose.pushPose(); VertexConsumer out = buffers.getBuffer(RenderType.lines());
        double phase = entity.tickCount * 0.19, radius = 0.16;
        for (int i = 0; i < 3; i++) {
            double tilt = phase + i * Math.PI / 3.0;
            Vec3 last = null;
            for (int n = 0; n <= 24; n++) {
                double a = n * Math.PI * 2.0 / 24.0;
                Vec3 p = i == 0 ? new Vec3(Math.cos(a) * radius, Math.sin(a) * radius, 0) :
                    i == 1 ? new Vec3(0, Math.cos(a) * radius, Math.sin(a) * radius) :
                    new Vec3(Math.cos(a + tilt) * radius, 0, Math.sin(a + tilt) * radius);
                if (last != null) line(out, pose, last, p, i == 1 ? 105 : 175, 115, 255, 240);
                last = p;
            }
        }
        pose.popPose(); super.render(entity, yaw, partialTick, pose, buffers, packedLight);
    }
    private static void line(VertexConsumer out, PoseStack stack, Vec3 a, Vec3 b, int r, int g, int blue, int alpha) {
        PoseStack.Pose p = stack.last();
        out.vertex(p.pose(), (float)a.x, (float)a.y, (float)a.z).color(r,g,blue,alpha).normal(p.normal(),0,1,0).endVertex();
        out.vertex(p.pose(), (float)b.x, (float)b.y, (float)b.z).color(r,g,blue,alpha).normal(p.normal(),0,1,0).endVertex();
    }
    @Override public ResourceLocation getTextureLocation(PortalOrbEntity entity) { return TEXTURE; }
}