package io.github.japaguimarassi.voxmobs.action;

import io.github.japaguimarassi.voxmobs.ai.MobAction;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.PathfinderMob;
import net.minecraft.world.entity.TamableAnimal;
import net.minecraft.world.entity.ai.util.DefaultRandomPos;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.entity.monster.Monster;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;

public final class ActionExecutor {
    private static final String FOLLOW_KEY = "voxmobs_follow_player";
    private static final String PROTECT_KEY = "voxmobs_protect_player";
    private static final String SPAWN_COOLDOWN_KEY = "voxmobs_spawn_cooldown";

    private ActionExecutor() {
    }

    public static boolean execute(Mob mob, Player player, MobAction action) {
        return execute(mob, player, action, "");
    }

    public static boolean execute(Mob mob, Player player, MobAction action, String argument) {
        if (mob == null || player == null || action == null || mob.level().isClientSide || mob.isRemoved()
                || !mob.isAlive() || mob.level() != player.level()) {
            return false;
        }
        return switch (action) {
            case FOLLOW -> {
                mob.getPersistentData().putUUID(FOLLOW_KEY, player.getUUID());
                mob.getPersistentData().remove(PROTECT_KEY);
                mob.getNavigation().moveTo(player, 1.12D);
                mob.getLookControl().setLookAt(player, 30.0F, 30.0F);
                yield true;
            }
            case APPROACH -> {
                mob.getNavigation().moveTo(player, 1.2D);
                mob.getLookControl().setLookAt(player, 30.0F, 30.0F);
                yield true;
            }
            case FLEE -> {
                clearFollow(mob);
                Vec3 away;
                if (mob instanceof PathfinderMob pathfinder) {
                    away = DefaultRandomPos.getPosAway(pathfinder, 12, 7, player.position());
                } else {
                    Vec3 direction = mob.position().subtract(player.position()).normalize();
                    away = mob.position().add(direction.scale(8.0D));
                }
                yield away != null && mob.getNavigation().moveTo(away.x, away.y, away.z, 1.18D);
            }
            case LOOK -> {
                mob.getLookControl().setLookAt(player, 30.0F, 30.0F);
                yield true;
            }
            case SIT -> {
                if (mob instanceof TamableAnimal tameable && tameable.isTame()
                        && player.getUUID().equals(tameable.getOwnerUUID())) {
                    tameable.setOrderedToSit(true);
                    mob.getNavigation().stop();
                    yield true;
                }
                yield false;
            }
            case JUMP -> {
                mob.getJumpControl().jump();
                yield true;
            }
            case STOP -> {
                clearFollow(mob);
                mob.getNavigation().stop();
                yield true;
            }
            case PROTECT -> {
                mob.getPersistentData().putUUID(FOLLOW_KEY, player.getUUID());
                mob.getPersistentData().putBoolean(PROTECT_KEY, true);
                mob.getNavigation().moveTo(player, 1.1D);
                mob.getLookControl().setLookAt(player, 30.0F, 30.0F);
                if (player.getLastHurtByMob() instanceof Monster attacker && attacker.isAlive()
                        && attacker.level() == mob.level() && attacker.distanceToSqr(player) <= 20.0D) {
                    mob.setTarget(attacker);
                }
                yield true;
            }
            case PICKUP_ITEM -> pickupNearbyItem(mob);
            case DROP_ITEM -> dropHeldItem(mob);
            case SPAWN_MOB -> spawnRegisteredMob(mob, argument);
            default -> false;
        };
    }

    private static boolean pickupNearbyItem(Mob mob) {
        if (!mob.getItemBySlot(EquipmentSlot.MAINHAND).isEmpty()) {
            return false;
        }
        AABB search = mob.getBoundingBox().inflate(5.0D, 2.5D, 5.0D);
        ItemEntity nearest = mob.level().getEntitiesOfClass(ItemEntity.class, search,
                item -> item.isAlive() && !item.getItem().isEmpty()).stream()
                .min((left, right) -> Double.compare(mob.distanceToSqr(left), mob.distanceToSqr(right)))
                .orElse(null);
        if (nearest == null) {
            return false;
        }
        ItemStack source = nearest.getItem();
        ItemStack picked = source.split(1);
        if (picked.isEmpty()) {
            return false;
        }
        mob.setItemSlot(EquipmentSlot.MAINHAND, picked);
        mob.take(nearest, 1);
        if (source.isEmpty()) {
            nearest.discard();
        } else {
            nearest.setItem(source);
        }
        return true;
    }

    private static boolean dropHeldItem(Mob mob) {
        ItemStack held = mob.getItemBySlot(EquipmentSlot.MAINHAND);
        if (held.isEmpty()) {
            return false;
        }
        ItemStack dropped = held.copy();
        if (mob.spawnAtLocation(dropped, 0.2F) == null) {
            return false;
        }
        mob.setItemSlot(EquipmentSlot.MAINHAND, ItemStack.EMPTY);
        return true;
    }

    private static boolean spawnRegisteredMob(Mob source, String rawId) {
        if (!(source.level() instanceof ServerLevel level) || rawId == null || rawId.isBlank()
                || rawId.length() > 128) {
            return false;
        }
        long now = level.getGameTime();
        long last = source.getPersistentData().getLong(SPAWN_COOLDOWN_KEY);
        if (source.getPersistentData().contains(SPAWN_COOLDOWN_KEY) && now - last < 200L) {
            return false;
        }
        AABB nearby = source.getBoundingBox().inflate(8.0D);
        if (level.getEntitiesOfClass(Mob.class, nearby).size() >= 12) {
            return false;
        }
        String normalizedId = rawId.contains(":") ? rawId : "minecraft:" + rawId;
        ResourceLocation id = ResourceLocation.tryParse(normalizedId);
        if (id == null) {
            return false;
        }
        var type = BuiltInRegistries.ENTITY_TYPE.getOptional(id).orElse(null);
        if (type == null) {
            return false;
        }
        Entity created = type.create(level);
        if (!(created instanceof Mob spawned)) {
            if (created != null) {
                created.discard();
            }
            return false;
        }
        Direction direction = source.getDirection();
        BlockPos requested = source.blockPosition().relative(direction, 2);
        BlockPos spawnPos = level.getHeightmapPos(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, requested);
        if (!level.getWorldBorder().isWithinBounds(spawnPos)) {
            spawned.discard();
            return false;
        }
        spawned.moveTo(spawnPos.getX() + 0.5D, spawnPos.getY(), spawnPos.getZ() + 0.5D,
                source.getYRot(), 0.0F);
        if (!level.noCollision(spawned)) {
            spawned.discard();
            return false;
        }
        if (!level.addFreshEntity(spawned)) {
            spawned.discard();
            return false;
        }
        source.getPersistentData().putLong(SPAWN_COOLDOWN_KEY, now);
        return true;
    }

    private static void clearFollow(Mob mob) {
        mob.getPersistentData().remove(FOLLOW_KEY);
        mob.getPersistentData().remove(PROTECT_KEY);
    }

    public static String followKey() {
        return FOLLOW_KEY;
    }

    public static String protectKey() {
        return PROTECT_KEY;
    }
}
