package br.com.realityengineai;

import org.junit.Test;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

public class BotPromptEngineTest {
    @Test
    public void mapPromptsAreRecognized() {
        assertTrue(BotPromptEngine.isMapPrompt("crie um mapa do zero"));
        assertTrue(BotPromptEngine.isMapPrompt("create a map with snowy terrain"));
        assertFalse(BotPromptEngine.isMapPrompt("crie uma espada"));
    }

    @Test
    public void mapRadiusIsBounded() {
        assertEquals(24, BotPromptEngine.parseRadius("mapa raio 24", 16, 64));
        assertEquals(64, BotPromptEngine.parseRadius("mapa raio 999", 16, 64));
        assertEquals(16, BotPromptEngine.parseRadius("mapa sem raio", 16, 64));
    }

    @Test
    public void moduleDimensionsAreParsedAndClamped() {
        int[] d = BotPromptEngine.parseDimensions("módulo garagem 15x9x7");
        assertEquals(15, d[0]);
        assertEquals(9, d[1]);
        assertEquals(7, d[2]);
        assertEquals(128, BotPromptEngine.parseDimensions("módulo 999x200x7")[0]);
        assertEquals(64, BotPromptEngine.parseDimensions("módulo 9x9x80")[2]);
    }
}
