package br.com.japa.dmzdbc.block;

import br.com.japa.dmzdbc.DMZDBC;
import br.com.japa.dmzdbc.item.DMZDBCItems;
import br.com.japa.dmzdbc.player.DMZDBCData;
import net.minecraft.block.Block;
import net.minecraft.block.material.Material;
import net.minecraft.creativetab.CreativeTabs;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.util.ChatComponentText;
import net.minecraft.world.World;

public class BlockDivineAltar extends Block {
    public BlockDivineAltar() {
        super(Material.rock);
        setBlockName("divineAltar");
        setBlockTextureName(DMZDBC.MODID + ":divine_altar");
        setCreativeTab(CreativeTabs.tabBlock);
        setHardness(4.0F);
        setResistance(12.0F);
        setLightLevel(0.65F);
        setStepSound(soundTypeStone);
    }

    @Override
    public boolean onBlockActivated(World world, int x, int y, int z, EntityPlayer player, int side, float hitX, float hitY, float hitZ) {
        if (world.isRemote) {
            return true;
        }

        DMZDBCData data = DMZDBCData.get(player);

        if (data.isAngelUnlocked()) {
            player.addChatMessage(new ChatComponentText("§bThe Angel Lineage is already awakened."));
            return true;
        }

        boolean creative = player.capabilities.isCreativeMode;
        if (!creative && player.experienceLevel < 30) {
            player.addChatMessage(new ChatComponentText("§cThe altar requires 30 XP levels."));
            return true;
        }

        if (!creative && !player.inventory.hasItem(DMZDBCItems.DIVINE_SIGIL)) {
            player.addChatMessage(new ChatComponentText("§cA Divine Sigil is required."));
            return true;
        }

        if (!creative) {
            if (!player.inventory.consumeInventoryItem(DMZDBCItems.DIVINE_SIGIL)) {
                player.addChatMessage(new ChatComponentText("§cA Divine Sigil is required."));
                return true;
            }
            player.addExperienceLevel(-30);
        }

        data.unlockAngel();
        player.addChatMessage(new ChatComponentText("§bThe Angel Lineage has awakened. §fDivine Instinct is now available."));
        DMZDBC.sync(player);
        return true;
    }
}
