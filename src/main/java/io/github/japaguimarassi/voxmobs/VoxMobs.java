package io.github.japaguimarassi.voxmobs;

import io.github.japaguimarassi.voxmobs.client.ClientBootstrap;
import io.github.japaguimarassi.voxmobs.command.CommandHandler;
import io.github.japaguimarassi.voxmobs.ai.ConversationService;
import io.github.japaguimarassi.voxmobs.config.VoxMobsConfig;
import io.github.japaguimarassi.voxmobs.events.WorldEvents;
import io.github.japaguimarassi.voxmobs.network.NetworkHandler;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.fml.DistExecutor;
import net.minecraftforge.fml.ModLoadingContext;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.config.ModConfig;
import net.minecraftforge.fml.javafmlmod.FMLJavaModLoadingContext;

@Mod(VoxMobs.MOD_ID)
public final class VoxMobs {
    public static final String MOD_ID = "voxmobs";

    public VoxMobs() {
        ModLoadingContext.get().registerConfig(ModConfig.Type.COMMON, VoxMobsConfig.COMMON);
        ModLoadingContext.get().registerConfig(ModConfig.Type.CLIENT, VoxMobsConfig.CLIENT);
        NetworkHandler.register();
        ConversationService.initialize();
        MinecraftForge.EVENT_BUS.addListener(CommandHandler::register);
        MinecraftForge.EVENT_BUS.addListener(ConversationService::saveBrain);
        MinecraftForge.EVENT_BUS.register(new WorldEvents());
        DistExecutor.unsafeRunWhenOn(Dist.CLIENT, () -> () ->
                ClientBootstrap.register(FMLJavaModLoadingContext.get().getModEventBus()));
    }
}
