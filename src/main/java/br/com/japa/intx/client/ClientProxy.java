package br.com.japa.intx.client;

import br.com.japa.intx.config.IntXConfig;
import br.com.japa.intx.numeric.NumberFormatter;
import br.com.japa.intx.proxy.CommonProxy;
import cpw.mods.fml.common.eventhandler.SubscribeEvent;
import net.minecraft.client.Minecraft;
import net.minecraftforge.client.event.RenderGameOverlayEvent;
import net.minecraftforge.common.MinecraftForge;
import java.math.BigInteger;
import java.util.Map;
import java.util.TreeMap;

public final class ClientProxy extends CommonProxy {
    private final Map<String, BigInteger> values = new TreeMap<String, BigInteger>();

    @Override
    public void init() {
        MinecraftForge.EVENT_BUS.register(this);
    }

    @Override
    public synchronized void handleSync(Map<String, BigInteger> incoming) {
        values.clear();
        if (incoming != null) values.putAll(incoming);
    }

    @SubscribeEvent
    public void onRenderOverlay(RenderGameOverlayEvent.Post event) {
        if (event.type != RenderGameOverlayEvent.ElementType.TEXT || !IntXConfig.showHud) return;
        Minecraft mc = Minecraft.getMinecraft();
        if (mc.thePlayer == null || mc.fontRenderer == null) return;
        Map<String, BigInteger> snapshot;
        synchronized (this) {
            snapshot = new TreeMap<String, BigInteger>(values);
        }
        int y = 4;
        int count = 0;
        for (Map.Entry<String, BigInteger> entry : snapshot.entrySet()) {
            if (count++ >= 5) break;
            mc.fontRenderer.drawStringWithShadow(
                entry.getKey() + ": " + NumberFormatter.compact(entry.getValue()),
                4, y, 0xFFFFFF
            );
            y += 10;
        }
    }
}
