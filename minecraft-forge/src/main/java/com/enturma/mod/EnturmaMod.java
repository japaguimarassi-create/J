package com.enturma.mod;

import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.fml.ModLoadingContext;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.config.ModConfig;

@Mod(EnturmaMod.MOD_ID)
public final class EnturmaMod {
    public static final String MOD_ID = "enturma";

    public EnturmaMod() {
        ModLoadingContext.get().registerConfig(ModConfig.Type.COMMON, EnturmaConfig.SPEC);
        MinecraftForge.EVENT_BUS.register(new MobConversationHandler());
        MinecraftForge.EVENT_BUS.addListener(EnturmaCommands::register);
        MobSettings.reload();
    }
}
