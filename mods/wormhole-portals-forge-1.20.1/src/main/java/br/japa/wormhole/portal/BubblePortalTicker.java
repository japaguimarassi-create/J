package br.japa.wormhole.portal;

import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import qouteall.imm_ptl.core.portal.Portal;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Mod.EventBusSubscriber(modid = "wormhole_portals", bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class BubblePortalTicker {
    private BubblePortalTicker() {}

    @SubscribeEvent
    public static void onLevelTick(TickEvent.LevelTickEvent event) {
        if (event.phase != TickEvent.Phase.END || !(event.level instanceof ServerLevel level)) return;
        if (level.getGameTime() % 5 != 0) return;

        Map<String, List<Portal>> groups = new HashMap<>();
        Map<String, BubbleTag> metadata = new HashMap<>();
        for (net.minecraft.world.entity.Entity entity : level.getAllEntities()) {
            if (!(entity instanceof Portal portal)) continue;
            BubbleTag tag = BubbleTag.parse(portal.portalTag);
            if (tag == null) continue;
            String key = tag.linkId() + ":" + tag.side();
            groups.computeIfAbsent(key, ignored -> new ArrayList<>()).add(portal);
            metadata.putIfAbsent(key, tag);
        }

        for (Map.Entry<String, List<Portal>> entry : groups.entrySet()) {
            BubbleTag tag = metadata.get(entry.getKey());
            boolean opened = tag.enabled() && isPlayerNearby(level, tag.center(), tag.activationRange());
            boolean changed = false;
            for (Portal portal : entry.getValue()) {
                if (portal.isVisible() != opened || portal.getTeleportable() != opened) {
                    portal.setIsVisible(opened);
                    portal.setTeleportable(opened);
                    portal.setInteractable(opened);
                    changed = true;
                }
            }
            if (changed) {
                for (Portal portal : entry.getValue()) portal.reloadAndSyncToClient();
                level.playSound(null, tag.center().x, tag.center().y, tag.center().z,
                    SoundEvents.ENDERMAN_TELEPORT, SoundSource.BLOCKS, 0.32F, opened ? 1.25F : 0.72F);
            }
            if (opened && tag.border() && level.getGameTime() % 10 == 0) emitBorder(level, tag);
        }
    }

    private static boolean isPlayerNearby(ServerLevel level, Vec3 center, double range) {
        double squared = range * range;
        for (Player player : level.players()) {
            if (player.position().distanceToSqr(center) <= squared) return true;
        }
        return false;
    }

    private static void emitBorder(ServerLevel level, BubbleTag tag) {
        for (int i = 0; i < 20; i++) {
            double angle = Math.PI * 2.0 * i / 20.0;
            double x = tag.center().x + Math.cos(angle) * tag.radius();
            double z = tag.center().z + Math.sin(angle) * tag.radius();
            double y = tag.center().y;
            level.sendParticles(ParticleTypes.END_ROD, x, y, z, 1, 0, 0, 0, 0);
        }
    }
}
