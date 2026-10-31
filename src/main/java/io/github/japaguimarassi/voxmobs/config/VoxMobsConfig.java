package io.github.japaguimarassi.voxmobs.config;

import net.minecraftforge.common.ForgeConfigSpec;

public final class VoxMobsConfig {
    public static final ForgeConfigSpec COMMON;
    public static final CommonValues COMMON_VALUES;
    public static final ForgeConfigSpec CLIENT;
    public static final ClientValues CLIENT_VALUES;

    static {
        ForgeConfigSpec.Builder common = new ForgeConfigSpec.Builder();
        COMMON_VALUES = new CommonValues(common);
        COMMON = common.build();
        ForgeConfigSpec.Builder client = new ForgeConfigSpec.Builder();
        CLIENT_VALUES = new ClientValues(client);
        CLIENT = client.build();
    }

    private VoxMobsConfig() {
    }

    public static final class CommonValues {
        public final ForgeConfigSpec.DoubleValue conversationRange;
        public final ForgeConfigSpec.IntValue memoryLines;
        public final ForgeConfigSpec.IntValue requestsPerMinute;
        public final ForgeConfigSpec.BooleanValue enableOnlineLearning;
        public final ForgeConfigSpec.BooleanValue allowMobSpawning;

        private CommonValues(ForgeConfigSpec.Builder builder) {
            builder.push("brain");
            builder.comment("VoxMobs uses an entirely local 100,000-parameter cognitive model. No HTTP endpoints, keys, or hosted AI APIs are used.");
            enableOnlineLearning = builder.define("enableOnlineLearning", true);
            memoryLines = builder.defineInRange("memoryLines", 16, 0, 64);
            requestsPerMinute = builder.defineInRange("requestsPerMinute", 8, 1, 30);
            conversationRange = builder.defineInRange("conversationRange", 8.0D, 2.0D, 16.0D);
            allowMobSpawning = builder.define("allowMobSpawning", true);
            builder.pop();
        }
    }

    public static final class ClientValues {
        public final ForgeConfigSpec.BooleanValue microphoneEnabled;
        public final ForgeConfigSpec.BooleanValue voiceEnabled;
        public final ForgeConfigSpec.DoubleValue voiceVolume;
        public final ForgeConfigSpec.IntValue maxRecordingSeconds;
        public final ForgeConfigSpec.BooleanValue showRecognizedText;
        public final ForgeConfigSpec.ConfigValue<String> voiceGenderMode;
        public final ForgeConfigSpec.BooleanValue showVoiceIdentity;

        private ClientValues(ForgeConfigSpec.Builder builder) {
            builder.push("voice");
            microphoneEnabled = builder.define("microphoneEnabled", true);
            voiceEnabled = builder.define("voiceEnabled", true);
            voiceVolume = builder.defineInRange("voiceVolume", 0.75D, 0.0D, 1.0D);
            maxRecordingSeconds = builder.defineInRange("maxRecordingSeconds", 12, 2, 20);
            showRecognizedText = builder.define("showRecognizedText", true);
            voiceGenderMode = builder.define("voiceGenderMode", "random", value ->
                    value instanceof String text && (text.equals("random") || text.equals("feminine") || text.equals("masculine")));
            showVoiceIdentity = builder.define("showVoiceIdentity", true);
            builder.pop();
        }
    }
}
