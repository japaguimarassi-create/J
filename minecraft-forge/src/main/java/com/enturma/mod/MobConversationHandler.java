package com.enturma.mod;

import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.player.Player;
import net.minecraftforge.event.ServerChatEvent;
import net.minecraftforge.event.entity.player.PlayerInteractEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;

import java.util.Comparator;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

public final class MobConversationHandler {
    private static final Map<UUID, UUID> ACTIVE_MOB_BY_PLAYER = new ConcurrentHashMap<>();
    private static final Map<UUID, UUID> ACTIVE_PLAYER_BY_MOB = new ConcurrentHashMap<>();
    private static final Map<UUID, java.util.List<AIClient.Turn>> MEMORY = new ConcurrentHashMap<>();
    private static final Map<UUID, Long> LAST_TALK_TICK = new ConcurrentHashMap<>();

    @SubscribeEvent
    public void onEntityInteract(PlayerInteractEvent.EntityInteract event) {
        if (event.getLevel().isClientSide() || !EnturmaConfig.ENABLED.get()) return;
        if (!(event.getEntity() instanceof ServerPlayer player) || !(event.getTarget() instanceof Mob mob)) return;
        if (!MobSettings.allows(mob) || !player.isCrouching() || !event.getItemStack().isEmpty()) return;
        event.setCanceled(true);
        event.setCancellationResult(InteractionResult.SUCCESS);
        beginConversation(mob, player, "__greeting__");
    }

    @SubscribeEvent
    public void onServerChat(ServerChatEvent event) {
        if (!EnturmaConfig.ENABLED.get() || !EnturmaConfig.CHAT_CAPTURE.get()) return;
        ServerPlayer player = event.getPlayer();
        String message = event.getMessage().getString().trim();
        if (message.isEmpty() || message.startsWith("/") || message.length() > 1500) return;
        UUID mobId = ACTIVE_MOB_BY_PLAYER.get(player.getUUID());
        if (mobId == null) return;
        Mob mob = findMob(player.serverLevel(), mobId);
        if (mob == null || !mob.isAlive() || mob.distanceToSqr(player) > Math.pow(EnturmaConfig.TALK_RADIUS.get(), 2)) {
            ACTIVE_MOB_BY_PLAYER.remove(player.getUUID());
            ACTIVE_PLAYER_BY_MOB.remove(mobId);
            return;
        }
        sendTurn(mob, player, message);
    }

    public static int forceTalk(ServerPlayer player, String message) {
        if (!EnturmaConfig.ENABLED.get()) {
            player.sendSystemMessage(Component.literal("Enturma AI está desligado."));
            return 0;
        }
        double radius = EnturmaConfig.TALK_RADIUS.get();
        Mob closest = player.serverLevel().getEntitiesOfClass(Mob.class, player.getBoundingBox().inflate(radius), MobSettings::allows)
            .stream().min(Comparator.comparingDouble(player::distanceToSqr)).orElse(null);
        if (closest == null) {
            player.sendSystemMessage(Component.literal("Nenhuma criatura configurada por perto. Agache e clique em um mob ou ajuste a lista de IDs."));
            return 0;
        }
        beginConversation(closest, player, message);
        return 1;
    }

    private static void beginConversation(Mob mob, ServerPlayer player, String message) {
        ACTIVE_MOB_BY_PLAYER.put(player.getUUID(), mob.getUUID());
        ACTIVE_PLAYER_BY_MOB.put(mob.getUUID(), player.getUUID());
        MEMORY.computeIfAbsent(mob.getUUID(), ignored -> new java.util.ArrayList<>());
        mob.lookAt(player, 180.0F, 90.0F);
        sendTurn(mob, player, message);
    }

    private static Mob findMob(ServerLevel level, UUID id) {
        return level.getEntity(id) instanceof Mob mob ? mob : null;
    }

    private static void sendTurn(Mob mob, ServerPlayer player, String message) {
        long currentTick = player.serverLevel().getServer().getTickCount();
        Long previous = LAST_TALK_TICK.put(mob.getUUID(), currentTick);
        if (previous != null && currentTick - previous < 10) return;
        java.util.List<AIClient.Turn> memory = MEMORY.computeIfAbsent(mob.getUUID(), ignored -> new java.util.ArrayList<>());
        synchronized (memory) {
            memory.add(new AIClient.Turn("user", message));
            while (memory.size() > 8) memory.remove(0);
        }
        AIClient.request(mob, player, message, java.util.List.copyOf(memory));
    }

    public static void acceptReply(Mob mob, ServerPlayer player, String dialogue, String emotion, com.google.gson.JsonArray actions) {
        if (!mob.isAlive() || !player.isAlive() || mob.level() != player.level()) return;
        if (mob.distanceToSqr(player) > Math.pow(EnturmaConfig.TALK_RADIUS.get() + 2, 2)) return;
        String name = mob.getDisplayName().getString();
        Component line = Component.literal("[" + name + "] " + dialogue);
        double radiusSqr = Math.pow(EnturmaConfig.TALK_RADIUS.get() + 2, 2);
        for (ServerPlayer nearby : player.serverLevel().players()) {
            if (nearby.distanceToSqr(mob) <= radiusSqr) nearby.sendSystemMessage(line);
        }
        ActionExecutor.execute(mob, player, actions, emotion);
        VoiceBridge.speak(mob, dialogue);
        java.util.List<AIClient.Turn> memory = MEMORY.computeIfAbsent(mob.getUUID(), ignored -> new java.util.ArrayList<>());
        synchronized (memory) {
            memory.add(new AIClient.Turn("assistant", dialogue));
            while (memory.size() > 8) memory.remove(0);
        }
    }
}
