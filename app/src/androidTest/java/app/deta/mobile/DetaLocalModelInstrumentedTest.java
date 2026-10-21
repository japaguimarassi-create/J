package app.deta.mobile;

import android.content.Context;

import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;

import org.json.JSONObject;
import org.junit.BeforeClass;
import org.junit.Test;
import org.junit.runner.RunWith;

import java.nio.charset.StandardCharsets;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

@RunWith(AndroidJUnit4.class)
public final class DetaLocalModelInstrumentedTest {
    private static DetaLocalModel model;

    @BeforeClass
    public static void loadVerifiedWeights() throws Exception {
        Context context = InstrumentationRegistry.getInstrumentation().getTargetContext();
        model = DetaLocalModel.load(context.getAssets());
    }

    @Test
    public void loadsAllTrainedParametersAndLineage() {
        assertEquals(400_000, model.parameterCount());
        assertEquals(30_000, model.trainingSteps());
        JSONObject metadata = model.metadata();
        assertEquals(5, metadata.optInt("groups_completed"));
        assertNotNull(metadata.optString("weights_sha256", null));
        JSONObject losses = metadata.optJSONObject("validation_losses");
        assertNotNull(losses);
        for (int group = 1; group <= 5; group++) assertTrue(losses.has(String.valueOf(group)));
    }

    @Test
    public void generatesUtf8OutputWithoutAnyNetworkService() {
        String completion = model.generate("def add(a, b):", 12, 0.85f, 1, 42L);
        assertNotNull(completion);
        assertTrue(completion.length() > 0);
        assertTrue(completion.getBytes(StandardCharsets.UTF_8).length > 0);
    }

    @Test
    public void rejectsUnsafeGenerationSettings() {
        try {
            model.generate("x", 0, 0.8f, 1, 1L);
            fail("Expected token limit validation");
        } catch (IllegalArgumentException expected) {
            assertTrue(expected.getMessage().contains("1 a 160"));
        }
        try {
            model.generate("x", 4, 0.8f, 65, 1L);
            fail("Expected top-k validation");
        } catch (IllegalArgumentException expected) {
            assertTrue(expected.getMessage().contains("top-k"));
        }
    }
}
