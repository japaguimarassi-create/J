package io.github.japaguimarassi.voxmobs.goal;

import io.github.japaguimarassi.voxmobs.action.ActionExecutor;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.ai.goal.Goal;
import net.minecraft.world.entity.monster.Monster;

import java.util.EnumSet;
import java.util.UUID;

public final class FollowPlayerGoal extends Goal {
    private final Mob mob;
    private ServerPlayer target;
    private int recalcTicks;

    public FollowPlayerGoal(Mob mob) {
        this.mob = mob;
        setFlags(EnumSet.of(Flag.MOVE, Flag.LOOK));
    }

    @Override
    public boolean canUse() {
        if (!mob.getPersistentData().hasUUID(ActionExecutor.followKey()) || mob.level().getServer() == null) {
            return false;
        }
        UUID id = mob.getPersistentData().getUUID(ActionExecutor.followKey());
        MinecraftServer server = mob.level().getServer();
        ServerPlayer player = server.getPlayerList().getPlayer(id);
        if (player == null || !player.isAlive() || player.level() != mob.level()
                || mob.distanceToSqr(player) > 24.0D * 24.0D) {
            return false;
        }
        target = player;
        return true;
    }

    @Override
    public boolean canContinueToUse() {
        return target != null && target.isAlive() && target.level() == mob.level()
                && mob.getPersistentData().hasUUID(ActionExecutor.followKey())
                && mob.distanceToSqr(target) <= 32.0D * 32.0D;
    }

    @Override
    public void start() {
        recalcTicks = 0;
    }

    @Override
    public void stop() {
        target = null;
        mob.getNavigation().stop();
    }

    @Override
    public void tick() {
        if (target == null) {
            return;
        }
        mob.getLookControl().setLookAt(target, 30.0F, 30.0F);
        if (mob.getPersistentData().getBoolean(ActionExecutor.protectKey())
                && target.getLastHurtByMob() instanceof Monster attacker
                && attacker.isAlive() && attacker.level() == mob.level()
                && attacker.distanceToSqr(target) <= 24.0D * 24.0D) {
            mob.setTarget(attacker);
        }
        if (--recalcTicks <= 0) {
            recalcTicks = 10;
            if (mob.distanceToSqr(target) > 3.0D * 3.0D) {
                mob.getNavigation().moveTo(target, 1.12D);
            } else {
                mob.getNavigation().stop();
            }
        }
    }
}
