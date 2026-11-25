package br.com.japa.dmzdbc.player;

import br.com.japa.dmzdbc.DMZDBC;
import cpw.mods.fml.common.eventhandler.SubscribeEvent;
import cpw.mods.fml.common.gameevent.PlayerEvent;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraftforge.event.entity.EntityEvent;
import net.minecraftforge.event.entity.player.PlayerEvent.Clone;

public class PlayerDataEvents {
    @SubscribeEvent
    public void onEntityConstructing(EntityEvent.EntityConstructing event) {
        if (event.entity instanceof EntityPlayer && event.entity.getExtendedProperties(DMZDBCData.KEY) == null) {
            event.entity.registerExtendedProperties(DMZDBCData.KEY, new DMZDBCData());
        }
    }

    @SubscribeEvent
    public void onPlayerClone(Clone event) {
        DMZDBCData oldData = DMZDBCData.get(event.original);
        DMZDBCData newData = DMZDBCData.get(event.entity);
        newData.copyFrom(oldData);
    }

    @SubscribeEvent
    public void onPlayerLoggedIn(PlayerEvent.PlayerLoggedInEvent event) {
        DMZDBC.sync(event.player);
    }
}
