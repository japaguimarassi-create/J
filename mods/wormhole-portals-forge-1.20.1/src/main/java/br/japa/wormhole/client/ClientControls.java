package br.japa.wormhole.client;

import br.japa.wormhole.WormholePortals;
import br.japa.wormhole.portal.PortalEndpointEntity;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.minecraft.network.chat.Component;
import net.minecraft.world.phys.AABB;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.RegisterKeyMappingsEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import org.lwjgl.glfw.GLFW;

@Mod.EventBusSubscriber(modid = WormholePortals.MOD_ID, bus = Mod.EventBusSubscriber.Bus.MOD, value = Dist.CLIENT)
public final class ClientControls {
    public static final KeyMapping OPEN_PANEL = new KeyMapping(
        "key.wormhole_portals.open_panel", GLFW.GLFW_KEY_P, "key.categories.misc"
    );

    private ClientControls() {}

    @SubscribeEvent
    public static void registerKeys(RegisterKeyMappingsEvent event) {
        event.register(OPEN_PANEL);
    }

    @Mod.EventBusSubscriber(modid = WormholePortals.MOD_ID, bus = Mod.EventBusSubscriber.Bus.FORGE, value = Dist.CLIENT)
    public static final class Ticks {
        private Ticks() {}

        @SubscribeEvent
        public static void clientTick(TickEvent.ClientTickEvent event) {
            if (event.phase != TickEvent.Phase.END || !OPEN_PANEL.consumeClick()) return;
            Minecraft minecraft = Minecraft.getInstance();
            if (minecraft.player == null || minecraft.level == null || minecraft.screen != null) return;
            var area = minecraft.player.getBoundingBox().inflate(12.0);
            PortalEndpointEntity nearest = minecraft.level.getEntitiesOfClass(PortalEndpointEntity.class, area)
                .stream().min((a, b) -> Double.compare(a.distanceToSqr(minecraft.player), b.distanceToSqr(minecraft.player)))
                .orElse(null);
            if (nearest == null) {
                minecraft.player.displayClientMessage(Component.literal("Nenhum portal próximo."), true);
                return;
            }
            minecraft.setScreen(new PortalSettingsScreen(nearest.getId(), nearest.linkId(),
                nearest.radius(), nearest.activationRange(), nearest.isEnabled()));
        }
    }
}