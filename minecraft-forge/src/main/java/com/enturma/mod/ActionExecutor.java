package com.enturma.mod;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.monster.Monster;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;

import java.util.Optional;

public final class ActionExecutor {
    private ActionExecutor() {}

    public static void execute(Mob mob, ServerPlayer player, JsonArray actions, String emotion) {
        if (!(mob.level() instanceof ServerLevel level) || !mob.isAlive() || !player.isAlive()) return;
        if (actions == null) actions = new JsonArray();
        int budget = Math.min(actions.size(), 3);
        for (int index = 0; index < budget; index++) {
            JsonElement element = actions.get(index);
            if (!element.isJsonObject()) continue;
            JsonObject action = element.getAsJsonObject();
            String type = string(action, "type", "");
            switch (type) {
                case "look_at_player" -> mob.lookAt(player, 180.0F, 90.0F);
                case "follow_player" -> {
                    if (!(mob instanceof Monster) && mob.distanceToSqr(player) > 3.0) {
                        mob.getNavigation().moveTo(player, 0.9D);
                    }
                }
                case "give_item" -> dropItem(level, mob, action);
                case "emote" -> level.sendParticles(ParticleTypes.HAPPY_VILLAGER, mob.getX(), mob.getY() + mob.getBbHeight() * 0.75D, mob.getZ(), 5, 0.25D, 0.25D, 0.25D, 0.02D);
                case "play_ambient_sound" -> mob.playAmbientSound();
                default -> {
                }
            }
        }
        if ("happy".equals(emotion) || "excited".equals(emotion)) {
            level.sendParticles(ParticleTypes.HAPPY_VILLAGER, mob.getX(), mob.getY() + mob.getBbHeight(), mob.getZ(), 2, 0.2D, 0.2D, 0.2D, 0.01D);
        }
    }

    private static void dropItem(ServerLevel level, Mob mob, JsonObject action) {
        String rawId = string(action, "item_id", "minecraft:bread");
        ResourceLocation id = ResourceLocation.tryParse(rawId);
        if (id == null) return;
        Optional<Item> item = BuiltInRegistries.ITEM.getOptional(id);
        if (item.isEmpty() || item.get() == net.minecraft.world.item.Items.AIR) return;
        int count;
        try {
            count = Math.max(1, Math.min(16, action.has("count") ? action.get("count").getAsInt() : 1));
        } catch (RuntimeException exception) {
            count = 1;
        }
        ItemStack stack = new ItemStack(item.get(), count);
        ItemEntity dropped = new ItemEntity(level, mob.getX(), mob.getY() + 0.45D, mob.getZ(), stack);
        dropped.setDefaultPickUpDelay();
        level.addFreshEntity(dropped);
    }

    private static String string(JsonObject object, String key, String fallback) {
        return object.has(key) && object.get(key).isJsonPrimitive() ? object.get(key).getAsString() : fallback;
    }
}
