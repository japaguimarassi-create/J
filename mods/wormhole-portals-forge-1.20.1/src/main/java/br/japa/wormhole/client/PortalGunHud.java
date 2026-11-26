package br.japa.wormhole.client;
import br.japa.wormhole.WormholePortals;
import br.japa.wormhole.item.PortalGunItem;
import net.minecraft.client.Minecraft;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.RenderGuiEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
@Mod.EventBusSubscriber(modid = WormholePortals.MOD_ID, bus = Mod.EventBusSubscriber.Bus.FORGE, value = Dist.CLIENT)
public final class PortalGunHud {
    private PortalGunHud() {}
    @SubscribeEvent public static void render(RenderGuiEvent.Post event) {
        Minecraft mc = Minecraft.getInstance(); if (mc.player == null) return;
        var stack = mc.player.getMainHandItem().is(WormholePortals.PORTAL_GUN.get()) ? mc.player.getMainHandItem() : mc.player.getOffhandItem();
        if (!stack.is(WormholePortals.PORTAL_GUN.get())) return;
        String text = String.format(java.util.Locale.ROOT, "PORTAL SIZE  %.2f", PortalGunItem.getRadius(stack));
        int x = event.getWindow().getGuiScaledWidth() / 2;
        int y = event.getWindow().getGuiScaledHeight() / 2 + 24;
        event.getGuiGraphics().drawCenteredString(mc.font, text, x, y, 0xBFA6FF);
        event.getGuiGraphics().drawCenteredString(mc.font, "SCROLL: RESIZE  |  SHIFT: PRESET", x, y + 12, 0xC0C0C0);
    }
}