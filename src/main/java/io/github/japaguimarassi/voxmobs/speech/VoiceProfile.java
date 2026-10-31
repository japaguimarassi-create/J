package io.github.japaguimarassi.voxmobs.speech;

import java.nio.charset.StandardCharsets;
import java.util.Locale;
import java.util.UUID;

public record VoiceProfile(float pitch, float brightness, float speed, float nasal,
                           String gender, String voiceName, float formantScale,
                           float rasp, long seed) {
    private static final String[] FEMININE_NAMES = {
            "Alice", "Bia", "Clara", "Dara", "Eva", "Flora", "Gaia", "Jade",
            "Lia", "Maya", "Nina", "Olivia", "Rosa", "Sora", "Zoe", "Yara"
    };
    private static final String[] MASCULINE_NAMES = {
            "Alex", "Bento", "Caio", "Dante", "Enzo", "Gael", "Hugo", "Icaro",
            "Leo", "Nilo", "Otto", "Ravi", "Theo", "Yuki", "Zeca", "Noah"
    };

    public VoiceProfile(float pitch, float brightness, float speed, float nasal) {
        this(pitch, brightness, speed, nasal, "neutra", "Vox", 1.0F, 0.0F, 0L);
    }

    public static VoiceProfile forEntityType(String entityType) {
        return forMob(entityType, "", new UUID(0L, stableHash(entityType == null ? "mob" : entityType)));
    }

    public static VoiceProfile forMob(String entityType, String mobName, UUID entityId) {
        return forMob(entityType, mobName, entityId, "random");
    }

    public static VoiceProfile forMob(String entityType, String mobName, UUID entityId, String genderMode) {
        String type = entityType == null ? "mob" : entityType.toLowerCase(Locale.ROOT);
        String name = mobName == null ? "" : mobName;
        UUID id = entityId == null ? new UUID(0L, stableHash(type + name)) : entityId;
        // UUID + entity type define the identity. A nametag change must never
        // silently assign a different voice to the same creature.
        long seed = mix64(id.getMostSignificantBits() ^ id.getLeastSignificantBits()
                ^ stableHash(type));
        boolean feminine = switch (genderMode == null ? "random" : genderMode) {
            case "feminine" -> true;
            case "masculine" -> false;
            default -> (seed & 1L) != 0L;
        };
        double unit = ((seed >>> 1) & 0xFFFFL) / 65535.0D;
        float variation = (float) (0.91D + unit * 0.18D);
        float basePitch;
        float brightness;
        float speed;
        float nasal;
        float formant;
        float rasp;
        switch (pathOf(type)) {
            case "creeper" -> { basePitch = 102.0F; brightness = 0.75F; speed = 0.91F; nasal = 0.18F; formant = 0.94F; rasp = 0.24F; }
            case "enderman" -> { basePitch = 84.0F; brightness = 0.68F; speed = 0.84F; nasal = 0.25F; formant = 0.83F; rasp = 0.16F; }
            case "wolf" -> { basePitch = 154.0F; brightness = 1.12F; speed = 1.06F; nasal = 0.08F; formant = 1.05F; rasp = 0.08F; }
            case "cat", "ocelot", "allay", "parrot" -> { basePitch = 194.0F; brightness = 1.25F; speed = 1.09F; nasal = 0.06F; formant = 1.16F; rasp = 0.02F; }
            case "villager", "wandering_trader" -> { basePitch = 134.0F; brightness = 1.04F; speed = 0.97F; nasal = 0.12F; formant = 1.02F; rasp = 0.04F; }
            case "pig", "chicken", "sheep", "rabbit" -> { basePitch = 174.0F; brightness = 1.2F; speed = 1.1F; nasal = 0.15F; formant = 1.12F; rasp = 0.03F; }
            case "cow", "mooshroom", "iron_golem", "ravager" -> { basePitch = 96.0F; brightness = 0.82F; speed = 0.88F; nasal = 0.19F; formant = 0.91F; rasp = 0.1F; }
            case "skeleton", "stray", "wither_skeleton" -> { basePitch = 148.0F; brightness = 1.18F; speed = 0.94F; nasal = 0.05F; formant = 1.08F; rasp = 0.12F; }
            case "zombie", "husk", "drowned" -> { basePitch = 111.0F; brightness = 0.73F; speed = 0.86F; nasal = 0.29F; formant = 0.88F; rasp = 0.3F; }
            case "horse", "donkey", "mule", "camel" -> { basePitch = 126.0F; brightness = 0.93F; speed = 0.99F; nasal = 0.1F; formant = 1.0F; rasp = 0.04F; }
            case "ender_dragon", "wither" -> { basePitch = 72.0F; brightness = 0.62F; speed = 0.78F; nasal = 0.3F; formant = 0.78F; rasp = 0.38F; }
            default -> { basePitch = 132.0F; brightness = 1.0F; speed = 0.99F; nasal = 0.12F; formant = 1.0F; rasp = 0.07F; }
        }
        float genderFactor = feminine ? 1.22F : 0.86F;
        float pitch = clamp(basePitch * genderFactor * variation, 62.0F, 265.0F);
        float individualBrightness = clamp(brightness * (0.88F + variation * 0.12F), 0.45F, 1.5F);
        String baseName = (feminine ? FEMININE_NAMES : MASCULINE_NAMES)
                [Math.floorMod((int) (seed >>> 17), FEMININE_NAMES.length)];
        String voiceName = baseName + "-" + Long.toUnsignedString(seed, 36).toUpperCase(Locale.ROOT);
        return new VoiceProfile(pitch, individualBrightness, speed * (0.96F + variation * 0.04F),
                nasal, feminine ? "feminina" : "masculina", voiceName,
                formant * variation, rasp, seed);
    }


    public VoiceProfile withEmotion(String emotion) {
        String value = emotion == null ? "" : emotion.toLowerCase(Locale.ROOT);
        float pitchFactor = 1.0F;
        float speedFactor = 1.0F;
        float brightnessFactor = 1.0F;
        switch (value) {
            case "animado", "feliz", "animada", "happy", "excited" -> {
                pitchFactor = 1.07F;
                speedFactor = 1.08F;
                brightnessFactor = 1.08F;
            }
            case "medo", "assustado", "fearful", "afraid" -> {
                pitchFactor = 1.1F;
                speedFactor = 1.04F;
                brightnessFactor = 0.92F;
            }
            case "alerta", "serio", "serious", "alert" -> {
                pitchFactor = 0.96F;
                speedFactor = 0.94F;
            }
            case "triste", "sad", "cansado", "tired" -> {
                pitchFactor = 0.91F;
                speedFactor = 0.82F;
                brightnessFactor = 0.88F;
            }
            case "sussurro", "whisper" -> {
                pitchFactor = 0.94F;
                speedFactor = 0.88F;
                brightnessFactor = 0.68F;
            }
            case "brincalhao", "playful", "curioso", "curious" -> {
                pitchFactor = 1.04F;
                speedFactor = 1.03F;
                brightnessFactor = 1.1F;
            }
            default -> {
            }
        }
        return new VoiceProfile(clamp(pitch * pitchFactor, 60.0F, 280.0F),
                clamp(brightness * brightnessFactor, 0.4F, 1.6F),
                clamp(speed * speedFactor, 0.65F, 1.35F), nasal,
                gender, voiceName, formantScale, rasp, seed);
    }

    private static String pathOf(String value) {
        int separator = value.indexOf(':');
        return separator >= 0 ? value.substring(separator + 1) : value;
    }

    private static long stableHash(String value) {
        long hash = 0xcbf29ce484222325L;
        for (byte item : value.getBytes(StandardCharsets.UTF_8)) {
            hash ^= item & 0xFFL;
            hash *= 0x100000001b3L;
        }
        return hash;
    }

    private static long mix64(long value) {
        value = (value ^ (value >>> 30)) * 0xbf58476d1ce4e5b9L;
        value = (value ^ (value >>> 27)) * 0x94d049bb133111ebL;
        return value ^ (value >>> 31);
    }

    private static float clamp(float value, float minimum, float maximum) {
        return Math.max(minimum, Math.min(maximum, value));
    }
}
