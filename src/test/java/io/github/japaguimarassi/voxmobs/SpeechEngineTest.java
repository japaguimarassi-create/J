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
}
