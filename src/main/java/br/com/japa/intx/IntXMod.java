package br.com.japa.intx;

import br.com.japa.intx.command.CommandIntX;
import br.com.japa.intx.config.IntXConfig;
import br.com.japa.intx.event.IntXEvents;
import br.com.japa.intx.network.IntXNetwork;
import br.com.japa.intx.proxy.CommonProxy;
import cpw.mods.fml.common.Mod;
import cpw.mods.fml.common.SidedProxy;
import cpw.mods.fml.common.event.FMLPreInitializationEvent;
import cpw.mods.fml.common.event.FMLServerStartingEvent;
import net.minecraftforge.common.MinecraftForge;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

@Mod(modid = IntXMod.MOD_ID, name = IntXMod.NAME, version = IntXMod.VERSION,
     acceptedMinecraftVersions = "[1.7.10]")
public final class IntXMod {
    public static final String MOD_ID = "intx";
    public static final String NAME = "IntX - Expanded Numeric Engine";
    public static final String VERSION = "0.1.0";
    public static final Logger LOGGER = LogManager.getLogger(MOD_ID);

    @Mod.Instance(MOD_ID)
    public static IntXMod INSTANCE;

    @SidedProxy(clientSide = "br.com.japa.intx.client.ClientProxy",
                serverSide = "br.com.japa.intx.proxy.CommonProxy")
    public static CommonProxy proxy;

    @Mod.EventHandler
    public void preInit(FMLPreInitializationEvent event) {
        IntXConfig.load(event.getSuggestedConfigurationFile());
        IntXNetwork.init();
        MinecraftForge.EVENT_BUS.register(new IntXEvents());
        proxy.init();
        LOGGER.info("IntX {} initialized for Minecraft 1.7.10", VERSION);
    }

    @Mod.EventHandler
    public void serverStarting(FMLServerStartingEvent event) {
        event.registerServerCommand(new CommandIntX());
    }
}
