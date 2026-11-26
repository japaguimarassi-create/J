package br.japa.wormhole.client;
import br.japa.wormhole.portal.PortalEndpointEntity;
import com.mojang.blaze3d.systems.RenderSystem;
import com.mojang.blaze3d.vertex.BufferBuilder;
import com.mojang.blaze3d.vertex.BufferUploader;
import com.mojang.blaze3d.vertex.DefaultVertexFormat;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.Tesselator;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.mojang.blaze3d.vertex.VertexFormat;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.GameRenderer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.entity.EntityRenderer;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.phys.Vec3;
import org.joml.Matrix4f;
public final class PortalEndpointRenderer extends EntityRenderer<PortalEndpointEntity> {
    private static final ResourceLocation TEXTURE = new ResourceLocation("minecraft", "textures/block/white_concrete.png");
    public PortalEndpointRenderer(EntityRendererProvider.Context context) { super(context); shadowRadius = 0.0F; }
    @Override public void render(PortalEndpointEntity entity, float yaw, float partialTick, PoseStack pose, MultiBufferSource buffers, int packedLight) {
        pose.pushPose();
        double radius = entity.radius();
        double phase = entity.animationTicks() * 0.09 + entity.getId() * 0.31;
        if (entity.isOpen()) {
            RemoteDimensionManager.renderView(entity, partialTick);
            if (RemoteDimensionManager.hasRemoteView(entity)) {
                drawRemoteSurface(entity, pose, radius * 0.992, partialTick);
            }
        }
        VertexConsumer lines = buffers.getBuffer(RenderType.lines());
        int alpha = entity.isOpen() ? (int)(170 + 65 * Math.sin(phase)) : (int)(95 + 55 * Math.sin(phase * 1.7));
        drawSphere(lines, pose, radius, alpha, entity.isOpen(), phase);
        drawSwirl(lines, pose, radius * 0.78, phase, entity.isOpen());
        if (entity.hasBorder()) drawBorder(lines, pose, radius + 0.04, phase);
        pose.popPose();
        super.render(entity, yaw, partialTick, pose, buffers, packedLight);
    }

    private static void drawRemoteSurface(PortalEndpointEntity endpoint, PoseStack pose, double radius, float partialTick) {
        Minecraft minecraft = Minecraft.getInstance();
        if (minecraft.player == null) return;
        int texture = RemoteDimensionManager.textureId(endpoint.getId());
        if (texture < 0) return;
        Vec3 forward = minecraft.player.getLookAngle().normalize();
        Vec3 upAxis = new Vec3(0.0, 1.0, 0.0);
        Vec3 right = upAxis.cross(forward);
        if (right.lengthSqr() < 1.0E-5) right = new Vec3(1.0, 0.0, 0.0);
        right = right.normalize();
        Vec3 cameraUp = forward.cross(right).normalize();
        Vec3 cameraOffset = minecraft.player.getEyePosition(partialTick).subtract(endpoint.position());
        double fov = Math.toRadians(minecraft.options.fov().get().doubleValue());
        double tanHalfFov = Math.tan(fov * 0.5);
        int latitudeSteps = 28;
        int longitudeSteps = 56;
        RenderSystem.enableBlend();
        RenderSystem.defaultBlendFunc();
        RenderSystem.disableCull();
        RenderSystem.depthMask(false);
        RenderSystem.setShader(GameRenderer::getPositionTexColorShader);
        RenderSystem.setShaderTexture(0, texture);
        BufferBuilder builder = Tesselator.getInstance().getBuilder();
        builder.begin(VertexFormat.Mode.TRIANGLES, DefaultVertexFormat.POSITION_TEX_COLOR);
        Matrix4f matrix = pose.last().pose();
        for (int lat = 0; lat < latitudeSteps; lat++) {
            double phi0 = Math.PI * lat / latitudeSteps;
            double phi1 = Math.PI * (lat + 1) / latitudeSteps;
            for (int lon = 0; lon < longitudeSteps; lon++) {
                double theta0 = Math.PI * 2.0 * lon / longitudeSteps;
                double theta1 = Math.PI * 2.0 * (lon + 1) / longitudeSteps;
                MappedVertex a = mapPoint(radius, phi0, theta0, cameraOffset, forward, right, cameraUp, tanHalfFov);
                MappedVertex b = mapPoint(radius, phi0, theta1, cameraOffset, forward, right, cameraUp, tanHalfFov);
                MappedVertex c = mapPoint(radius, phi1, theta1, cameraOffset, forward, right, cameraUp, tanHalfFov);
                MappedVertex d = mapPoint(radius, phi1, theta0, cameraOffset, forward, right, cameraUp, tanHalfFov);
                if (a == null || b == null || c == null || d == null) continue;
                vertex(builder, matrix, a); vertex(builder, matrix, b); vertex(builder, matrix, c);
                vertex(builder, matrix, a); vertex(builder, matrix, c); vertex(builder, matrix, d);
            }
        }
        BufferUploader.drawWithShader(builder.end());
        RenderSystem.depthMask(true);
        RenderSystem.enableCull();
        RenderSystem.disableBlend();
    }

    private static MappedVertex mapPoint(double radius, double phi, double theta, Vec3 cameraOffset, Vec3 forward, Vec3 right, Vec3 up, double tanHalfFov) {
        double sin = Math.sin(phi);
        Vec3 direction = new Vec3(sin * Math.cos(theta), Math.cos(phi), sin * Math.sin(theta));
        Vec3 ray = direction.scale(radius).subtract(cameraOffset);
        double depth = ray.dot(forward);
        if (depth <= 0.08) return null;
        double nx = ray.dot(right) / (depth * tanHalfFov);
        double ny = ray.dot(up) / (depth * tanHalfFov);
        if (nx < -1.02 || nx > 1.02 || ny < -1.02 || ny > 1.02) return null;
        double u = 0.5 + nx * 0.5;
        double v = 0.5 + ny * 0.5;
        Vec3 position = direction.scale(radius);
        return new MappedVertex(position, (float)u, (float)v);
    }

    private static void vertex(BufferBuilder builder, Matrix4f matrix, MappedVertex vertex) {
        builder.vertex(matrix, (float)vertex.position.x, (float)vertex.position.y, (float)vertex.position.z)
            .uv(vertex.u, vertex.v).color(255, 255, 255, 255).endVertex();
    }

    private static void drawSphere(VertexConsumer out, PoseStack pose, double radius, int alpha, boolean open, double phase) {
        int latitudes = 14, longitudes = 36;
        for (int lat = 1; lat < latitudes; lat++) {
            double phi = Math.PI * lat / latitudes;
            for (int lon = 0; lon < longitudes; lon++) {
                double a = Math.PI * 2.0 * lon / longitudes, b = Math.PI * 2.0 * (lon + 1) / longitudes;
                line(out, pose, point(radius, phi, a), point(radius, phi, b), open ? 100 : 145, open ? 210 : 75, 255, alpha);
            }
        }
        for (int lon = 0; lon < longitudes; lon += 2) {
            double theta = Math.PI * 2.0 * lon / longitudes;
            for (int lat = 0; lat < latitudes; lat++) {
                line(out, pose, point(radius, Math.PI * lat / latitudes, theta), point(radius, Math.PI * (lat + 1) / latitudes, theta), 185, 100, 255, alpha);
            }
        }
        if (!open) {
            for (int i = 0; i < 18; i++) {
                double a = phase * 2.3 + i * 0.71;
                Vec3 p1 = point(radius * 1.015, Math.PI * (0.12 + (i % 6) * 0.13), a);
                Vec3 p2 = point(radius * 1.015, Math.PI * (0.12 + (i % 6) * 0.13), a + 0.09 + (i % 4) * 0.03);
                line(out, pose, p1, p2, 205, 95, 255, 210);
            }
        }
    }

    private static void drawBorder(VertexConsumer out, PoseStack pose, double radius, double phase) {
        for (int i = 0; i < 64; i++) {
            double a = Math.PI * 2.0 * i / 64.0, b = Math.PI * 2.0 * (i + 1) / 64.0;
            Vec3 p1 = new Vec3(Math.cos(a) * radius, Math.sin(a * 2 + phase) * radius * 0.12, Math.sin(a) * radius);
            Vec3 p2 = new Vec3(Math.cos(b) * radius, Math.sin(b * 2 + phase) * radius * 0.12, Math.sin(b) * radius);
            line(out, pose, p1, p2, 255, 110, 35, 230);
        }
    }

    private static void drawSwirl(VertexConsumer out, PoseStack pose, double radius, double phase, boolean open) {
        Vec3 last = null;
        for (int i = 0; i <= 120; i++) {
            double t = i / 120.0, a = t * Math.PI * 8.0 + phase, r = radius * (0.025 + 0.94 * t);
            Vec3 p = new Vec3(Math.cos(a) * r, Math.sin(a * 0.55) * r * 0.38, Math.sin(a) * r);
            if (last != null) line(out, pose, last, p, 190, 120, 255, open ? 100 : 220);
            last = p;
        }
    }

    private static Vec3 point(double radius, double phi, double theta) {
        double sin = Math.sin(phi);
        return new Vec3(radius * sin * Math.cos(theta), radius * Math.cos(phi), radius * sin * Math.sin(theta));
    }
    private static void line(VertexConsumer consumer, PoseStack stack, Vec3 a, Vec3 b, int r, int g, int blue, int alpha) {
        PoseStack.Pose pose = stack.last();
        consumer.vertex(pose.pose(), (float)a.x, (float)a.y, (float)a.z).color(r, g, blue, alpha).normal(pose.normal(), 0, 1, 0).endVertex();
        consumer.vertex(pose.pose(), (float)b.x, (float)b.y, (float)b.z).color(r, g, blue, alpha).normal(pose.normal(), 0, 1, 0).endVertex();
    }
    @Override public ResourceLocation getTextureLocation(PortalEndpointEntity entity) { return TEXTURE; }
    private record MappedVertex(Vec3 position, float u, float v) {}
}