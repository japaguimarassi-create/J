package br.japa.wormhole.portal;

import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.protocol.Packet;
import net.minecraft.network.syncher.EntityDataAccessor;
import net.minecraft.network.syncher.EntityDataSerializers;
import net.minecraft.network.syncher.SynchedEntityData;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.network.NetworkHooks;

public final class PortalEndpointEntity extends Entity {
    private static final EntityDataAccessor<String> LINK = SynchedEntityData.defineId(PortalEndpointEntity.class, EntityDataSerializers.STRING);
    private static final EntityDataAccessor<Integer> SIDE = SynchedEntityData.defineId(PortalEndpointEntity.class, EntityDataSerializers.INT);
    private static final EntityDataAccessor<String> DESTINATION = SynchedEntityData.defineId(PortalEndpointEntity.class, EntityDataSerializers.STRING);
    private static final EntityDataAccessor<Float> TARGET_X = SynchedEntityData.defineId(PortalEndpointEntity.class, EntityDataSerializers.FLOAT);
    private static final EntityDataAccessor<Float> TARGET_Y = SynchedEntityData.defineId(PortalEndpointEntity.class, EntityDataSerializers.FLOAT);
    private static final EntityDataAccessor<Float> TARGET_Z = SynchedEntityData.defineId(PortalEndpointEntity.class, EntityDataSerializers.FLOAT);
    private static final EntityDataAccessor<Float> RADIUS = SynchedEntityData.defineId(PortalEndpointEntity.class, EntityDataSerializers.FLOAT);
    private static final EntityDataAccessor<Float> RANGE = SynchedEntityData.defineId(PortalEndpointEntity.class, EntityDataSerializers.FLOAT);
    private static final EntityDataAccessor<Boolean> OPEN = SynchedEntityData.defineId(PortalEndpointEntity.class, EntityDataSerializers.BOOLEAN);
    private static final EntityDataAccessor<Boolean> BORDER = SynchedEntityData.defineId(PortalEndpointEntity.class, EntityDataSerializers.BOOLEAN);
    private static final EntityDataAccessor<Boolean> ENABLED = SynchedEntityData.defineId(PortalEndpointEntity.class, EntityDataSerializers.BOOLEAN);
    private int animationTicks;

    public PortalEndpointEntity(EntityType<? extends PortalEndpointEntity> type, Level level) {
        super(type, level);
        noPhysics = true;
        setNoGravity(true);
    }

    @Override
    protected void defineSynchedData() {
        entityData.define(LINK, "");
        entityData.define(SIDE, 0);
        entityData.define(DESTINATION, "minecraft:overworld");
        entityData.define(TARGET_X, 0.0F);
        entityData.define(TARGET_Y, 64.0F);
        entityData.define(TARGET_Z, 0.0F);
        entityData.define(RADIUS, 2.25F);
        entityData.define(RANGE, 18.0F);
        entityData.define(OPEN, false);
        entityData.define(BORDER, false);
        entityData.define(ENABLED, true);
    }

    public void configure(String link, int side, ResourceLocation destination, Vec3 target, double radius, double range, boolean border) {
        entityData.set(LINK, link);
        entityData.set(SIDE, side);
        entityData.set(DESTINATION, destination.toString());
        entityData.set(TARGET_X, (float) target.x);
        entityData.set(TARGET_Y, (float) target.y);
        entityData.set(TARGET_Z, (float) target.z);
        entityData.set(RADIUS, (float) radius);
        entityData.set(RANGE, (float) range);
        entityData.set(BORDER, border);
        entityData.set(ENABLED, true);
    }

    public String linkId() { return entityData.get(LINK); }
    public int side() { return entityData.get(SIDE); }
    public ResourceLocation destinationId() { return ResourceLocation.tryParse(entityData.get(DESTINATION)); }
    public Vec3 targetPosition() { return new Vec3(entityData.get(TARGET_X), entityData.get(TARGET_Y), entityData.get(TARGET_Z)); }
    public double radius() { return entityData.get(RADIUS); }
    public double activationRange() { return entityData.get(RANGE); }
    public boolean isOpen() { return entityData.get(OPEN); }
    public boolean hasBorder() { return entityData.get(BORDER); }
    public boolean isEnabled() { return entityData.get(ENABLED); }
    public int animationTicks() { return animationTicks; }

    public void setOpen(boolean value) {
        if (entityData.get(OPEN) != value) {
            entityData.set(OPEN, value);
            animationTicks = 0;
        }
    }
    public void setRadius(double value) { entityData.set(RADIUS, (float) value); }
    public void setRange(double value) { entityData.set(RANGE, (float) value); }
    public void setEnabled(boolean value) { entityData.set(ENABLED, value); }
    public void setBorder(boolean value) { entityData.set(BORDER, value); }
    public void retarget(ResourceLocation dimension, Vec3 target) {
        entityData.set(DESTINATION, dimension.toString());
        entityData.set(TARGET_X, (float) target.x);
        entityData.set(TARGET_Y, (float) target.y);
        entityData.set(TARGET_Z, (float) target.z);
    }

    @Override
    public void tick() {
        super.tick();
        if (animationTicks < 100000) animationTicks++;
    }

    @Override
    protected void readAdditionalSaveData(CompoundTag tag) {
        entityData.set(LINK, tag.getString("Link"));
        entityData.set(SIDE, tag.getInt("Side"));
        entityData.set(DESTINATION, tag.getString("Destination"));
        entityData.set(TARGET_X, tag.getFloat("TargetX"));
        entityData.set(TARGET_Y, tag.getFloat("TargetY"));
        entityData.set(TARGET_Z, tag.getFloat("TargetZ"));
        entityData.set(RADIUS, tag.getFloat("Radius"));
        entityData.set(RANGE, tag.getFloat("Range"));
        entityData.set(OPEN, false);
        entityData.set(BORDER, tag.getBoolean("Border"));
        entityData.set(ENABLED, tag.getBoolean("Enabled"));
    }

    @Override
    protected void addAdditionalSaveData(CompoundTag tag) {
        tag.putString("Link", linkId());
        tag.putInt("Side", side());
        tag.putString("Destination", entityData.get(DESTINATION));
        tag.putFloat("TargetX", entityData.get(TARGET_X));
        tag.putFloat("TargetY", entityData.get(TARGET_Y));
        tag.putFloat("TargetZ", entityData.get(TARGET_Z));
        tag.putFloat("Radius", (float) radius());
        tag.putFloat("Range", (float) activationRange());
        tag.putBoolean("Border", hasBorder());
        tag.putBoolean("Enabled", isEnabled());
    }

    @Override
    public Packet<?> getAddEntityPacket() { return NetworkHooks.getEntitySpawningPacket(this); }
    @Override
    public boolean isPickable() { return false; }
    @Override
    public boolean isPushable() { return false; }
}