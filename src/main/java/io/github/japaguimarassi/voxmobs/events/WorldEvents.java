package io.github.japaguimarassi.voxmobs.events;

import io.github.japaguimarassi.voxmobs.goal.FollowPlayerGoal;
import net.minecraft.world.entity.Mob;
import net.minecraftforge.event.entity.EntityJoinLevelEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;

import java.util.Collections;
import java.util.Map;
import java.util.WeakHashMap;

public final class WorldEvents {
    private final Map<Mob, Boolean> installedGoals = Collections.synchronizedMap(new WeakHashMap<>());

    @SubscribeEvent
    public void onEntityJoin(EntityJoinLevelEvent event) {
        if (event.getLevel().isClientSide() || !(event.getEntity() instanceof Mob mob)) {
            return;
        }
        if (installedGoals.putIfAbsent(mob, Boolean.TRUE) == null) {
            mob.goalSelector.addGoal(3, new FollowPlayerGoal(mob));
        }
    }
}
