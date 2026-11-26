package br.japa.wormhole.portal;
import br.japa.wormhole.item.PortalGunItem;
import net.minecraft.network.protocol.Packet;
import net.minecraft.network.protocol.game.ClientGamePacketListener;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.projectile.ThrowableProjectile;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.network.NetworkHooks;
public final class PortalOrbEntity extends ThrowableProjectile {
    public PortalOrbEntity(EntityType<? extends PortalOrbEntity> type, Level level) { super(type, level); setNoGravity(true); }
    @Override protected void defineSynchedData() { }
    @Override protected float getGravity() { return 0.002F; }
    @Override public void tick() {
        super.tick();
        if (tickCount > 100) discard();
        if (level().isClientSide && tickCount % 2 == 0) level().addParticle(net.minecraft.core.particles.ParticleTypes.PORTAL, getX(), getY(), getZ(), 0, 0.01, 0);
    }
    @Override protected void onHit(HitResult result) {
        super.onHit(result);
        if (!level().isClientSide && level() instanceof ServerLevel server && getOwner() instanceof ServerPlayer player) {
            Vec3 point = result.getLocation();
            if (result instanceof BlockHitResult block) point = point.add(Vec3.atLowerCornerOf(block.getDirection().getNormal()).scale(0.12));
            PortalGunItem.onOrbImpact(player, server, point);
        }
        discard();
    }
    @Override public Packet<ClientGamePacketListener> getAddEntityPacket() { return NetworkHooks.getEntitySpawningPacket(this); }
    @Override public boolean isPickable() { return false; }
}