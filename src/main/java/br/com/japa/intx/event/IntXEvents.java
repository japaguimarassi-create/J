package br.com.japa.intx.event;

import br.com.japa.intx.data.PlayerNumbers;
import br.com.japa.intx.network.IntXNetwork;
import cpw.mods.fml.common.eventhandler.SubscribeEvent;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.entity.player.EntityPlayerMP;
import net.minecraftforge.event.entity.EntityEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;

public final class IntXEvents {
    @SubscribeEvent
    public void onEntityConstructing(EntityEvent.EntityConstructing event) {
        if (event.entity instanceof EntityPlayer
            && event.entity.getExtendedProperties(PlayerNumbers.ID) == null) {
            event.entity.registerExtendedProperties(PlayerNumbers.ID, new PlayerNumbers());
        }
    }

    @SubscribeEvent
    public void onPlayerClone(PlayerEvent.Clone event) {
        PlayerNumbers.get(event.entityPlayer).copyFrom(PlayerNumbers.get(event.original));
    }

    @SubscribeEvent
    public void onPlayerLogin(PlayerEvent.PlayerLoggedInEvent event) {
        sync(event.entityPlayer);
    }

    @SubscribeEvent
    public void onPlayerRespawn(PlayerEvent.PlayerRespawnEvent event) {
        sync(event.entityPlayer);
    }

    @SubscribeEvent
    public void onPlayerChangedDimension(PlayerEvent.PlayerChangedDimensionEvent event) {
        sync(event.entityPlayer);
    }

    private void sync(EntityPlayer player) {
        if (player instanceof EntityPlayerMP && player.worldObj != null && !player.worldObj.isRemote) {
            IntXNetwork.sync(player);
        }
    }
}
