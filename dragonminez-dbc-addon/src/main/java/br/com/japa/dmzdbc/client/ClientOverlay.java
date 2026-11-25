package br.com.japa.dmzdbc.client;

import br.com.japa.dmzdbc.player.DMZDBCData;
import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;
import net.minecraft.client.Minecraft;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraftforge.client.event.RenderGameOverlayEvent;
import cpw.mods.fml.common.eventhandler.SubscribeEvent;

@SideOnly(Side.CLIENT)
public class ClientOverlay {
    @SubscribeEvent
    public void onOverlay(RenderGameOverlayEvent.Post event) {
        if (event.type != RenderGameOverlayEvent.ElementType.ALL) {
            return;
        }

        EntityPlayer player = Minecraft.getMinecraft().thePlayer;
        if (player == null) {
            return;
        }

        DMZDBCData data = DMZDBCData.get(player);
        if (!data.isAngelUnlocked()) {
            return;
        }

        String state = data.isActive() ? "ACTIVE" : "IDLE";
        String text = "ANGEL LINEAGE  |  DIVINE ENERGY " + data.getDivineEnergy() + "  |  " + state;
        Minecraft.getMinecraft().fontRenderer.drawStringWithShadow(text, 6, 6, 0xBFEFFF);
    }
}
