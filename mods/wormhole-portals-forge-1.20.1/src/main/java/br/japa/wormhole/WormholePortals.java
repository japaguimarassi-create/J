package br.japa.wormhole;

import br.japa.wormhole.command.WormholeCommands;
import br.japa.wormhole.item.PortalAnchorItem;
import br.japa.wormhole.item.PortalGunItem;
import br.japa.wormhole.item.PortalTunerItem;
import net.minecraft.world.item.CreativeModeTabs;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.Rarity;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.event.BuildCreativeModeTabContentsEvent;
import net.minecraftforge.event.RegisterCommandsEvent;
import net.minecraftforge.eventbus.api.IEventBus;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.javafmlmod.FMLJavaModLoadingContext;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;

@Mod(WormholePortals.MOD_ID)
public final class WormholePortals {
    public static final String MOD_ID = "wormhole_portals";
    public static final DeferredRegister<Item> ITEMS = DeferredRegister.create(ForgeRegistries.ITEMS, MOD_ID);
    public static final RegistryObject<Item> PORTAL_ANCHOR = ITEMS.register("portal_anchor",
        () -> new PortalAnchorItem(new Item.Properties().stacksTo(1).rarity(Rarity.UNCOMMON)));
    public static final RegistryObject<Item> PORTAL_TUNER = ITEMS.register("portal_tuner",
        () -> new PortalTunerItem(new Item.Properties().stacksTo(1)));
    public static final RegistryObject<Item> PORTAL_GUN = ITEMS.register("portal_gun",
        () -> new PortalGunItem(new Item.Properties().stacksTo(1).rarity(Rarity.EPIC)));

    public WormholePortals() {
        IEventBus modBus = FMLJavaModLoadingContext.get().getModEventBus();
        ITEMS.register(modBus);
        modBus.addListener(this::addCreative);
        MinecraftForge.EVENT_BUS.register(this);
    }

    private void addCreative(BuildCreativeModeTabContentsEvent event) {
        if (event.getTabKey() == CreativeModeTabs.TOOLS_AND_UTILITIES) {
            event.accept(PORTAL_ANCHOR);
            event.accept(PORTAL_TUNER);
            event.accept(PORTAL_GUN);
        }
    }

    @SubscribeEvent
    public void onRegisterCommands(RegisterCommandsEvent event) {
        WormholeCommands.register(event.getDispatcher());
    }
}
