package com.enturma.mod;

import net.minecraftforge.common.ForgeConfigSpec;

public final class EnturmaConfig {
    public static final ForgeConfigSpec SPEC;
    public static final ForgeConfigSpec.BooleanValue ENABLED;
    public static final ForgeConfigSpec.BooleanValue CHAT_CAPTURE;
    public static final ForgeConfigSpec.BooleanValue WEB_RESEARCH;
    public static final ForgeConfigSpec.BooleanValue VOICE_ENABLED;
    public static final ForgeConfigSpec.IntValue TALK_RADIUS;
    public static final ForgeConfigSpec.ConfigValue<String> AI_ENDPOINT;

    static {
        ForgeConfigSpec.Builder builder = new ForgeConfigSpec.Builder();
        builder.push("general");
        ENABLED = builder.comment("Liga ou desliga conversas com mobs.").define("enabled", true);
        CHAT_CAPTURE = builder.comment("Permite que o mob ativo responda ao chat de jogadores próximos.").define("chatCapture", true);
        WEB_RESEARCH = builder.comment("Permite pesquisa web leve sobre mods instalados, quando disponível no backend.").define("webResearch", true);
        VOICE_ENABLED = builder.comment("Voz gerada por TTS e transmitida pelo Simple Voice Chat, se instalado.").define("voiceEnabled", true);
        TALK_RADIUS = builder.comment("Distância máxima para conversas em blocos.").defineInRange("talkRadius", 12, 3, 32);
        AI_ENDPOINT = builder.comment("URL base do backend Enturma AI. O backend deve ser acessível pelo servidor Minecraft.").define("aiEndpoint", "http://127.0.0.1:8000");
        builder.pop();
        SPEC = builder.build();
    }

    private EnturmaConfig() {}
}
