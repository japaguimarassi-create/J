package br.com.japa.intx.network;

import br.com.japa.intx.data.PlayerNumbers;
import cpw.mods.fml.common.network.NetworkRegistry;
import cpw.mods.fml.common.network.simpleimpl.SimpleNetworkWrapper;
import cpw.mods.fml.relauncher.Side;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.entity.player.EntityPlayerMP;

public final class IntXNetwork {
    private static final SimpleNetworkWrapper CHANNEL =
        NetworkRegistry.INSTANCE.newSimpleChannel("intx");

    private IntXNetwork() {
    }

    public static void init() {
        CHANNEL.registerMessage(SyncNumbersHandler.class, SyncNumbersMessage.class, 0, Side.CLIENT);
    }

    public static void sync(EntityPlayer player) {
        if (player instanceof EntityPlayerMP && player.worldObj != null && !player.worldObj.isRemote) {
            CHANNEL.sendTo(
                new SyncNumbersMessage(PlayerNumbers.get(player).snapshot()),
                (EntityPlayerMP) player
            );
        }
    }
}
