package io.github.japaguimarassi.voxmobs;

import io.github.japaguimarassi.voxmobs.speech.FormantTtsEngine;
import io.github.japaguimarassi.voxmobs.speech.VoiceProfile;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class SpeechEngineTest {
    @Test
    void createsOfflinePcmForPortugueseText() {
        byte[] audio = FormantTtsEngine.synthesize("Olá, jogador!", VoiceProfile.forEntityType("villager"));
        assertNotNull(audio);
        assertTrue(audio.length > 1000);
        assertEquals(0, audio.length % 2);
    }

    @Test
    void assignsDistinctVoiceProfilesToDifferentMobs() {
        java.util.UUID firstId = java.util.UUID.fromString("00000000-0000-0000-0000-000000000001");
        java.util.UUID secondId = java.util.UUID.fromString("00000000-0000-0000-0000-000000000002");
        VoiceProfile first = VoiceProfile.forMob("minecraft:creeper", "Creeper", firstId);
        VoiceProfile second = VoiceProfile.forMob("minecraft:creeper", "Creeper", secondId);
        assertNotEquals(first.pitch(), second.pitch());
        assertNotEquals(first.voiceName(), second.voiceName());
        assertNotEquals(java.util.Arrays.toString(FormantTtsEngine.synthesize("Olá, jogador!", first)),
                java.util.Arrays.toString(FormantTtsEngine.synthesize("Olá, jogador!", second)));
        assertTrue(first.gender().equals("feminina") || first.gender().equals("masculina"));
        assertEquals("feminina", VoiceProfile.forMob("minecraft:wolf", "Wolf", firstId, "feminine").gender());
        assertEquals("masculina", VoiceProfile.forMob("minecraft:wolf", "Wolf", firstId, "masculine").gender());
        assertNotEquals(VoiceProfile.forMob("minecraft:cat", "Mimi", firstId).pitch(),
                VoiceProfile.forMob("minecraft:creeper", "Creeper", firstId).pitch());
    }

    @Test
    void keepsVoiceIdentityStableAndDistinctAcrossAnEntitySet() {
        java.util.Set<String> names = new java.util.HashSet<>();
        for (int i = 1; i <= 64; i++) {
            java.util.UUID id = new java.util.UUID(0L, i);
            VoiceProfile profile = VoiceProfile.forMob("mymod:forest_guardian", "Guardião", id);
            VoiceProfile repeated = VoiceProfile.forMob("mymod:forest_guardian", "Guardião", id);
            assertEquals(profile, repeated);
            assertTrue(names.add(profile.voiceName()));
        }
    }
    @Test
    void voiceIdentityDoesNotChangeWhenMobIsRenamed() {
        java.util.UUID id = java.util.UUID.fromString("f17b03e2-09bb-4e2e-8d0a-10fa8d4c2a11");
        VoiceProfile original = VoiceProfile.forMob("minecraft:wolf", "Lobo", id);
        VoiceProfile renamed = VoiceProfile.forMob("minecraft:wolf", "Guardião", id);
        assertEquals(original, renamed);
    }

    @Test
    void randomizedGenderAndVoiceNameAlwaysMatch() {
        java.util.Set<String> feminineNames = java.util.Set.of(
                "Alice", "Bia", "Clara", "Dara", "Eva", "Flora", "Gaia", "Jade",
                "Lia", "Maya", "Nina", "Olivia", "Rosa", "Sora", "Zoe", "Yara");
        java.util.Set<String> masculineNames = java.util.Set.of(
                "Alex", "Bento", "Caio", "Dante", "Enzo", "Gael", "Hugo", "Icaro",
                "Leo", "Nilo", "Otto", "Ravi", "Theo", "Yuki", "Zeca", "Noah");
        java.util.Set<String> observedGenders = new java.util.HashSet<>();
        for (int i = 1; i <= 128; i++) {
            VoiceProfile profile = VoiceProfile.forMob("minecraft:villager", "Villager",
                    new java.util.UUID(0L, i));
            String baseName = profile.voiceName().substring(0, profile.voiceName().indexOf('-'));
            if (profile.gender().equals("feminina")) {
                assertTrue(feminineNames.contains(baseName), profile.voiceName());
            } else {
                assertEquals("masculina", profile.gender());
                assertTrue(masculineNames.contains(baseName), profile.voiceName());
            }
            observedGenders.add(profile.gender());
        }
        assertEquals(java.util.Set.of("feminina", "masculina"), observedGenders);
    }

}
