package app.deta.mobile;

import org.junit.Test;

import java.io.File;
import java.io.FileInputStream;
import java.io.InputStream;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

public final class DetaLocalModelTest {
    @Test
    public void packagedCheckpointLoadsAndGeneratesLocally() throws Exception {
        File asset = new File("src/main/assets/deta-model.bin");
        if (!asset.isFile()) asset = new File("app/src/main/assets/deta-model.bin");
        assertTrue("The trained Deta model asset must be present before Android tests.", asset.isFile());
        try (InputStream input = new FileInputStream(asset)) {
            DetaLocalModel model = new DetaLocalModel(input);
            assertEquals(400000, model.parameterCount());
            String result = model.generate("def add(a, b):", 8, 0.8f, 1, 42L);
            assertTrue("The local neural model must emit bytes.", result.length() > 0);
        }
    }

    @Test
    public void invalidGenerationLimitsAreRejected() throws Exception {
        File asset = new File("src/main/assets/deta-model.bin");
        if (!asset.isFile()) asset = new File("app/src/main/assets/deta-model.bin");
        try (InputStream input = new FileInputStream(asset)) {
            DetaLocalModel model = new DetaLocalModel(input);
            try {
                model.generate("prompt", 0, 0.8f, 8, 42L);
                throw new AssertionError("Invalid length must be rejected.");
            } catch (IllegalArgumentException expected) {
                assertTrue(expected.getMessage().contains("length"));
            }
        }
    }
    @Test
    public void greedyOutputIsReproducibleForSameSeed() throws Exception {
        File asset = new File("src/main/assets/deta-model.bin");
        if (!asset.isFile()) asset = new File("app/src/main/assets/deta-model.bin");
        try (InputStream first = new FileInputStream(asset);
             InputStream second = new FileInputStream(asset)) {
            DetaLocalModel modelA = new DetaLocalModel(first);
            DetaLocalModel modelB = new DetaLocalModel(second);
            assertEquals(
                    modelA.generate("def add(a, b):", 16, 0.8f, 1, 42L),
                    modelB.generate("def add(a, b):", 16, 0.8f, 1, 42L)
            );
        }
    }

}
