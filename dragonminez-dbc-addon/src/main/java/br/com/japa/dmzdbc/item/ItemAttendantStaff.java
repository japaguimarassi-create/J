package br.com.japa.dmzdbc.item;

import br.com.japa.dmzdbc.DMZDBC;
import br.com.japa.dmzdbc.player.DMZDBCData;
import net.minecraft.creativetab.CreativeTabs;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.item.Item;
import net.minecraft.item.ItemStack;
import net.minecraft.util.ChatComponentText;
import net.minecraft.world.World;

public class ItemAttendantStaff extends Item {
    public ItemAttendantStaff() {
        setUnlocalizedName("attendantStaff");
        setTextureName(DMZDBC.MODID + ":attendant_staff");
        setCreativeTab(CreativeTabs.tabCombat);
        setMaxStackSize(1);
        setFull3D();
    }

    @Override
    public ItemStack onItemRightClick(ItemStack stack, World world, EntityPlayer player) {
        if (!world.isRemote) {
            DMZDBCData data = DMZDBCData.get(player);
            int result = data.activateDivineInstinct();

            if (result == 0) {
                player.addChatMessage(new ChatComponentText("§bDivine Instinct activated. §fEnergy: " + data.getDivineEnergy()));
            } else if (result == 1) {
                player.addChatMessage(new ChatComponentText("§cYou have not awakened the Angel Lineage."));
            } else if (result == 2) {
                player.addChatMessage(new ChatComponentText("§eDivine Instinct is already active."));
            } else if (result == 3) {
                player.addChatMessage(new ChatComponentText("§eDivine Instinct is recharging: " + (data.getCooldownTicks() / 20) + "s."));
            } else {
                player.addChatMessage(new ChatComponentText("§cNot enough Divine Energy."));
            }

            DMZDBC.sync(player);
        }
        return stack;
    }
}
