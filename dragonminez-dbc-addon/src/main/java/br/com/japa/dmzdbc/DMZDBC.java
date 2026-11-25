package br.com.japa.dmzdbc;

import br.com.japa.dmzdbc.command.CommandDMZDBC;
import br.com.japa.dmzdbc.config.DMZDBCConfig;
import br.com.japa.dmzdbc.compat.DbcCompatibility;
import br.com.japa.dmzdbc.item.DMZDBCItems;
import br.com.japa.dmzdbc.network.PacketDivineSync;
import br.com.japa.dmzdbc.proxy.CommonProxy;
import cpw.mods.fml.common.Mod;
import cpw.mods.fml.common.SidedProxy;
import cpw.mods.fml.common.event.FMLInitializationEvent;
import cpw.mods.fml.common.event.FMLPostInitializationEvent;
import cpw.mods.fml.common.event.FMLPreInitializationEvent;
import cpw.mods.fml.common.event.FMLServerStartingEvent;
import cpw.mods.fml.common.network.NetworkRegistry;
import cpw.mods.fml.common.network.simpleimpl.SimpleNetworkWrapper;
import cpw.mods.fml.common.registry.GameRegistry;
import cpw.mods.fml.relauncher.Side;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.entity.player.EntityPlayerMP;
import net.minecraft.init.Blocks;
import net.minecraft.init.Items;
import net.minecraft.item.ItemStack;
import net.minecraftforge.common.MinecraftForge;

@Mod(
    modid = DMZDBC.MODID,
    name = DMZDBC.NAME,
    version = DMZDBC.VERSION,
    acceptedMinecraftVersions = "[1.7.10]"
)
public class DMZDBC {
    public static final String MODID = "dmzdbc";
    public static final String NAME = "DragonMine Z - DBC Edition";
    public static final String VERSION = "0.1.0";

    @Mod.Instance(MODID)
    public static DMZDBC INSTANCE;

    @SidedProxy(
        clientSide = "br.com.japa.dmzdbc.proxy.ClientProxy",
        serverSide = "br.com.japa.dmzdbc.proxy.CommonProxy"
    )
    public static CommonProxy PROXY;

    public static SimpleNetworkWrapper NETWORK;

    @Mod.EventHandler
    public void preInit(FMLPreInitializationEvent event) {
        DMZDBCConfig.load(event.getSuggestedConfigurationFile());
        DMZDBCItems.register();
        NETWORK = NetworkRegistry.INSTANCE.newSimpleChannel(MODID);
        NETWORK.registerMessage(PacketDivineSync.ClientHandler.class, PacketDivineSync.class, 0, Side.CLIENT);
        MinecraftForge.EVENT_BUS.register(new br.com.japa.dmzdbc.player.PlayerDataEvents());
        MinecraftForge.EVENT_BUS.register(new br.com.japa.dmzdbc.combat.DivineCombatHandler());
        PROXY.preInit();
    }

    @Mod.EventHandler
    public void init(FMLInitializationEvent event) {
        registerRecipes();
        PROXY.init();
    }

    @Mod.EventHandler
    public void postInit(FMLPostInitializationEvent event) {
        if (DbcCompatibility.isPresent()) {
            System.out.println("[DMZ-DBC] DBC and JRMCore classes detected. Safe compatibility mode enabled.");
        } else {
            System.out.println("[DMZ-DBC] DBC was not detected. The addon foundation can still load in Forge.");
        }
    }

    @Mod.EventHandler
    public void serverStarting(FMLServerStartingEvent event) {
        event.registerServerCommand(new CommandDMZDBC());
    }

    private void registerRecipes() {
        GameRegistry.addRecipe(
            new ItemStack(DMZDBCItems.DIVINE_SIGIL),
            " E ",
            "GNG",
            " D ",
            'E', Items.ender_pearl,
            'G', Items.gold_ingot,
            'N', Items.nether_star,
            'D', Items.diamond
        );

        GameRegistry.addRecipe(
            new ItemStack(DMZDBCItems.DIVINE_ALTAR),
            "OOO",
            "OSO",
            "OOO",
            'O', Blocks.obsidian,
            'S', DMZDBCItems.DIVINE_SIGIL
        );

        GameRegistry.addRecipe(
            new ItemStack(DMZDBCItems.ATTENDANT_STAFF),
            "  B",
            " S ",
            "B  ",
            'B', Items.blaze_rod,
            'S', DMZDBCItems.DIVINE_SIGIL
        );
    }

    public static void sync(EntityPlayer player) {
        if (NETWORK != null && player instanceof EntityPlayerMP) {
            PacketDivineSync.send((EntityPlayerMP) player);
        }
    }
}
