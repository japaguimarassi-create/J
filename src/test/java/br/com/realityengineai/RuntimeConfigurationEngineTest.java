package br.com.realityengineai;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;

import org.junit.Test;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

public class RuntimeConfigurationEngineTest {
    @Test
    public void runtimeRulesCanBeLoadedAndReloadedWithoutChangingMinecraftFiles() throws Exception {
        File config = Files.createTempDirectory("reality-engine-runtime-test").toFile();
        RuntimeConfigurationEngine engine = RuntimeConfigurationEngine.INSTANCE;
        engine.initialize(config);

        File rules = new File(new File(config, "realityengineai"), "runtime-rules.json");
        assertTrue(rules.isFile());
        assertTrue(engine.getRuleCount() >= 1);

        String valid = "{\n"
            + "  \"enabled\": true,\n"
            + "  \"rules\": [{\n"
            + "    \"id\": \"test_click\",\n"
            + "    \"event\": \"player_interact\",\n"
            + "    \"block\": \"minecraft:stone\",\n"
            + "    \"cooldown_ticks\": 20,\n"
            + "    \"actions\": [{\"type\": \"message\", \"text\": \"ok\"}]\n"
            + "  }]\n"
            + "}\n";
        Files.write(rules.toPath(), valid.getBytes(StandardCharsets.UTF_8));
        assertTrue(engine.reload());
        assertEquals(1, engine.getRuleCount());

        Files.write(rules.toPath(), "{ not valid json".getBytes(StandardCharsets.UTF_8));
        assertFalse(engine.reload());
        assertEquals(1, engine.getRuleCount());

        delete(config);
    }

    private static void delete(File file) {
        if (file.isDirectory()) {
            File[] children = file.listFiles();
            if (children != null) {
                for (File child : children) {
                    delete(child);
                }
            }
        }
        file.delete();
    }
}
