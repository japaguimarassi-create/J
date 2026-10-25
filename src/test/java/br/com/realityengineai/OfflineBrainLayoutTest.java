package br.com.realityengineai;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;

import org.junit.Test;
import static org.junit.Assert.*;

public final class OfflineBrainLayoutTest {
    @Test
    public void parameterLayoutIsExactlyThreeHundredThousand() {
        assertEquals(300000, 1000 * 256 + 256 + 256 * 120 + 120 + 120 * 24 + 24);
        assertEquals(300000, OfflineBrain.PARAMETER_COUNT);
        assertEquals(24, OfflineBrain.LABELS.length);
    }

    @Test
    public void tokenizerRecognizesAccentedPortuguese() {
        assertFalse(OfflineBrain.featureIds("computador de cristal").isEmpty());
        assertEquals(OfflineBrain.featureIds("dimensão de neve"), OfflineBrain.featureIds("DIMENSAO de neve"));
    }

    @Test
    public void trainedWeightsAreBundledWithExactSize() throws IOException {
        InputStream input = getClass().getResourceAsStream("/assets/realityengineai/brain/weights.bin");
        assertNotNull("The CI training step must generate the weight file before tests.", input);
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        byte[] chunk = new byte[4096];
        int read;
        while ((read = input.read(chunk)) != -1) {
            output.write(chunk, 0, read);
        }
        input.close();
        assertEquals(9 + 300000 * 4, output.toByteArray().length);
        OfflineBrain brain = new OfflineBrain();
        assertTrue(brain.isReady());
        assertEquals(300000, brain.getParameterCount());
    }
}
