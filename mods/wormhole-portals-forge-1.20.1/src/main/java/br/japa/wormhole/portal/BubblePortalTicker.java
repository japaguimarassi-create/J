package br.japa.wormhole.portal;
import net.minecraft.core.registries.Registries;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.common.util.ITeleporter;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.util.ArrayList;
import java.util.List;
import java.util.function.Function;
@Mod.EventBusSubscriber(modid = "wormhole_portals", bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class BubblePortalTicker {
    private static final String COOLDOWN = "wormhole_portal_cooldown";
    private BubblePortalTicker() {}
    @SubscribeEvent public static void onLevelTick(TickEvent.LevelTickEvent event) {
        if (event.phase != TickEvent.Phase.END || !(event.level instanceof ServerLevel level)) return;
        List<PortalEndpointEntity> portals = new ArrayList<>();
        for (Entity entity : level.getAllEntities()) if (entity instanceof PortalEndpointEntity portal) portals.add(portal);
        for (PortalEndpointEntity portal : portals) {
            boolean nearby = portal.isEnabled() && level.players().stream().anyMatch(player -> player.distanceToSqr(portal) <= portal.activationRange() * portal.activationRange());
            boolean changed = portal.isOpen() != nearby;
            portal.setOpen(nearby);
            if (changed) level.playSound(null, portal.getX(), portal.getY(), portal.getZ(), SoundEvents.ENDERMAN_TELEPORT, SoundSource.BLOCKS, 0.28F, nearby ? 1.22F : 0.76F);
            if (!nearby) continue;
            double radius = portal.radius();
            AABB area = AABB.ofSize(portal.position(), radius * 2.0 + 2.0, radius * 2.0 + 2.0, radius * 2.0 + 2.0);
            List<Entity> candidates = level.getEntitiesOfClass(Entity.class, area, e -> e != portal && !(e instanceof PortalEndpointEntity) && e.getVehicle() == null);
            for (Entity entity : candidates) {
                if (entity.isRemoved() || entity.getPersistentData().getLong(COOLDOWN) > level.getGameTime()) continue;
                Vec3 entry = findEntryPoint(entity, portal, radius + Math.max(entity.getBbWidth(), entity.getBbHeight()) * 0.5);
                if (entry != null) transfer(entity, portal, level, entry);
            }
            if (portal.hasBorder() && level.getGameTime() % 6 == 0) emitBorder(level, portal);
        }
    }
    private static Vec3 findEntryPoint(Entity entity, PortalEndpointEntity portal, double radius) {
        Vec3 start = new Vec3(entity.xo, entity.yo, entity.zo).subtract(portal.position());
        Vec3 end = entity.position().subtract(portal.position());
        if (start.lengthSqr() <= radius * radius) return null;
        Vec3 movement = end.subtract(start);
        double a = movement.lengthSqr();
        if (a < 1.0E-10) return null;
        double b = start.dot(movement);
        double c = start.lengthSqr() - radius * radius;
        double discriminant = b * b - a * c;
        if (discriminant < 0.0) return null;
        double t = (-b - Math.sqrt(discriminant)) / a;
        if (t < 0.0 || t > 1.0) return null;
        Vec3 localHit = start.add(movement.scale(t));
        if (movement.dot(localHit) >= 0.0) return null;
        return portal.position().add(localHit);
    }
    private static void transfer(Entity entity, PortalEndpointEntity portal, ServerLevel source, Vec3 entryPoint) {
        ResourceKey<Level> key = ResourceKey.create(Registries.DIMENSION, portal.destinationId());
        ServerLevel destination = source.getServer().getLevel(key);
        if (destination == null) return;
        Vec3 outward = entryPoint.subtract(portal.position()).normalize();
        Vec3 exit = portal.targetPosition().add(outward.scale(portal.radius() + Math.max(entity.getBbWidth(), entity.getBbHeight()) * 0.5 + 0.35));
        Vec3 velocity = entity.getDeltaMovement();
        float yaw = entity.getYRot();
        float pitch = entity.getXRot();
        entity.getPersistentData().putLong(COOLDOWN, source.getGameTime() + 30);
        if (destination == source) {
            entity.teleportTo(exit.x, exit.y, exit.z);
            entity.setDeltaMovement(velocity);
            entity.getPersistentData().putLong(COOLDOWN, source.getGameTime() + 30);
            return;
        }
        ITeleporter teleporter = new ITeleporter() {
            @Override public Entity placeEntity(Entity moved, ServerLevel currentWorld, ServerLevel destinationWorld, float suggestedYaw, Function<Boolean, Entity> repositionEntity) {
                Entity result = repositionEntity.apply(false);
                result.moveTo(exit.x, exit.y, exit.z, yaw, pitch);
                result.setDeltaMovement(velocity);
                result.getPersistentData().putLong(COOLDOWN, destinationWorld.getGameTime() + 30);
                return result;
            }
        };
        entity.changeDimension(destination, teleporter);
    }
    private static void emitBorder(ServerLevel level, PortalEndpointEntity portal) {
        double radius = portal.radius() + 0.05;
        for (int i = 0; i < 24; i++) {
            double phi = Math.PI * (i / 23.0), theta = i * Math.PI * (3.0 - Math.sqrt(5.0));
            double x = Math.cos(theta) * Math.sin(phi), y = Math.cos(phi), z = Math.sin(theta) * Math.sin(phi);
            level.sendParticles(ParticleTypes.SOUL_FIRE_FLAME, portal.getX() + x * radius, portal.getY() + y * radius, portal.getZ() + z * radius, 1, 0, 0, 0, 0);
        }
    }
}