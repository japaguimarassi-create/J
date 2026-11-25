package br.com.japa.dmzdbc.combat;

import br.com.japa.dmzdbc.DMZDBC;
import br.com.japa.dmzdbc.config.DMZDBCConfig;
import br.com.japa.dmzdbc.player.DMZDBCData;
import cpw.mods.fml.common.eventhandler.SubscribeEvent;
import cpw.mods.fml.common.gameevent.TickEvent;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.potion.Potion;
import net.minecraft.potion.PotionEffect;
import net.minecraft.util.ChatComponentText;
import net.minecraftforge.event.entity.living.LivingHurtEvent;

public class DivineCombatHandler {
    @SubscribeEvent
    public void onPlayerTick(TickEvent.PlayerTickEvent event) {
        if (event.phase != TickEvent.Phase.END || event.player.worldObj.isRemote) {
            return;
        }

        EntityPlayer player = event.player;
        DMZDBCData data = DMZDBCData.get(player);

        if (data.isActive()) {
            player.addPotionEffect(new PotionEffect(Potion.moveSpeed.id, 5, 1));
            player.addPotionEffect(new PotionEffect(Potion.jump.id, 5, 0));
        }

        boolean ended = data.tickServer();
        if (ended) {
            player.addChatMessage(new ChatComponentText("§bDivine Instinct ended. §fEnergy regenerates while inactive."));
        }

        if (player.ticksExisted % 20 == 0) {
            DMZDBC.sync(player);
        }
    }

    @SubscribeEvent
    public void onLivingHurt(LivingHurtEvent event) {
        if (!(event.entityLiving instanceof EntityPlayer)) {
            return;
        }

        EntityPlayer player = (EntityPlayer) event.entityLiving;
        if (player.worldObj.isRemote) {
            return;
        }

        DMZDBCData data = DMZDBCData.get(player);
        if (!data.isActive() || event.source.getEntity() == null) {
            return;
        }

        if (player.getRNG().nextFloat() < DMZDBCConfig.DODGE_CHANCE) {
            event.setCanceled(true);
            player.addChatMessage(new ChatComponentText("§bDivine Instinct evaded the attack."));
        }
    }
}
