package br.com.japa.dmzdbc.item;

import br.com.japa.dmzdbc.block.BlockDivineAltar;
import cpw.mods.fml.common.registry.GameRegistry;

public final class DMZDBCItems {
    public static final ItemDivineSigil DIVINE_SIGIL = new ItemDivineSigil();
    public static final ItemAttendantStaff ATTENDANT_STAFF = new ItemAttendantStaff();
    public static final BlockDivineAltar DIVINE_ALTAR = new BlockDivineAltar();

    private DMZDBCItems() {
    }

    public static void register() {
        GameRegistry.registerItem(DIVINE_SIGIL, "divine_sigil");
        GameRegistry.registerItem(ATTENDANT_STAFF, "attendant_staff");
        GameRegistry.registerBlock(DIVINE_ALTAR, "divine_altar");
    }
}
