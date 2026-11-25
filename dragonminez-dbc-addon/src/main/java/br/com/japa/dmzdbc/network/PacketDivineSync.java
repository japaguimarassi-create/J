package br.com.japa.dmzdbc.network;

import br.com.japa.dmzdbc.DMZDBC;
import br.com.japa.dmzdbc.player.DMZDBCData;
import cpw.mods.fml.common.network.simpleimpl.IMessage;
import cpw.mods.fml.common.network.simpleimpl.IMessageHandler;
import cpw.mods.fml.common.network.simpleimpl.MessageContext;
import cpw.mods.fml.relauncher.Side;
import cpw.mods.fml.relauncher.SideOnly;
import io.netty.buffer.ByteBuf;
import net.minecraft.entity.player.EntityPlayerMP;

public class PacketDivineSync implements IMessage {
    private boolean unlocked;
    private int energy;
    private int activeTicks;
    private int cooldownTicks;

    public PacketDivineSync() {
    }

    public PacketDivineSync(DMZDBCData data) {
        unlocked = data.isAngelUnlocked();
        energy = data.getDivineEnergy();
        activeTicks = data.getActiveTicks();
        cooldownTicks = data.getCooldownTicks();
    }

    @Override
    public void fromBytes(ByteBuf buffer) {
        unlocked = buffer.readBoolean();
        energy = buffer.readInt();
        activeTicks = buffer.readInt();
        cooldownTicks = buffer.readInt();
    }

    @Override
    public void toBytes(ByteBuf buffer) {
        buffer.writeBoolean(unlocked);
        buffer.writeInt(energy);
        buffer.writeInt(activeTicks);
        buffer.writeInt(cooldownTicks);
    }

    public static void send(EntityPlayerMP player) {
        DMZDBC.NETWORK.sendTo(new PacketDivineSync(DMZDBCData.get(player)), player);
    }

    @SideOnly(Side.CLIENT)
    public static class ClientHandler implements IMessageHandler<PacketDivineSync, IMessage> {
        @Override
        public IMessage onMessage(final PacketDivineSync message, MessageContext context) {
            net.minecraft.client.Minecraft.getMinecraft().func_152344_a(new Runnable() {
                @Override
                public void run() {
                    net.minecraft.client.Minecraft minecraft = net.minecraft.client.Minecraft.getMinecraft();
                    if (minecraft.thePlayer != null) {
                        DMZDBCData.get(minecraft.thePlayer).applySync(
                            message.unlocked,
                            message.energy,
                            message.activeTicks,
                            message.cooldownTicks
                        );
                    }
                }
            });
            return null;
        }
    }
}
