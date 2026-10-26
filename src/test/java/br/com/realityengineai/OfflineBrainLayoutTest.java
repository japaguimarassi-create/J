package br.com.realityengineai;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import org.junit.Test;
import static org.junit.Assert.*;

public final class OfflineBrainLayoutTest {
    @Test
    public void parameterLayoutMatchesExpandedClassifier() {
        assertEquals(300393, 2048 * 128 + 128 + 128 * 224 + 224 + 224 * 41 + 41);
        assertEquals(300393, OfflineBrain.PARAMETER_COUNT);
        assertEquals(41, OfflineBrain.LABELS.length);
    }

    @Test
    public void tokenizerRecognizesAccentedPortuguese() {
        assertFalse(OfflineBrain.featureIds("computador de cristal").isEmpty());
        assertEquals(OfflineBrain.featureIds("dimensão de neve"), OfflineBrain.featureIds("DIMENSAO de neve"));
    }

    @Test
    public void trainedWeightsAreBundledWithExactSize() throws IOException {
        InputStream input = getClass().getResourceAsStream("/assets/realityengineai/brain/weights.bin");
        assertNotNull("CI must generate classifier weights before tests.", input);
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        byte[] chunk = new byte[4096];
        int read;
        while ((read = input.read(chunk)) != -1) output.write(chunk, 0, read);
        input.close();
        byte[] bytes = output.toByteArray();
        assertEquals(9 + 300393 * 4, bytes.length);
        assertEquals("REAI300K2", new String(bytes, 0, 9, "US-ASCII"));
        OfflineBrain brain = new OfflineBrain();
        assertTrue(brain.isReady());
        assertEquals(300393, brain.getParameterCount());
    }
}
