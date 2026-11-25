package br.com.japa.dmzdbc.item;

import br.com.japa.dmzdbc.DMZDBC;
import net.minecraft.creativetab.CreativeTabs;
import net.minecraft.item.Item;

public class ItemDivineSigil extends Item {
    public ItemDivineSigil() {
        setUnlocalizedName("divineSigil");
        setTextureName(DMZDBC.MODID + ":divine_sigil");
        setCreativeTab(CreativeTabs.tabMaterials);
        setMaxStackSize(16);
    }
}
