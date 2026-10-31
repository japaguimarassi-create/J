package io.github.japaguimarassi.voxmobs;

import io.github.japaguimarassi.voxmobs.ai.CognitiveCore100k;
import io.github.japaguimarassi.voxmobs.ai.CognitivePrediction;
import io.github.japaguimarassi.voxmobs.ai.MobAction;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.*;

class CognitiveCoreTest {
    @TempDir
    Path temporaryDirectory;

    @Test
    void exposesExactlyOneHundredThousandTrainableParametersAndPersistsThem() throws Exception {
        Path file = temporaryDirectory.resolve("brain.dat");
        CognitiveCore100k first = CognitiveCore100k.loadOrTrain(file);
        assertEquals(100_000, first.parameterCount());
        assertTrue(first.trainingSteps() > 0);
        first.learnFromOutcome("me siga", "minecraft:wolf", MobAction.FOLLOW, true);
        long beforeLesson = first.trainingSteps();
        first.learnFromTeaching("venha comigo agora", "minecraft:generic", MobAction.FOLLOW);
        assertEquals(beforeLesson + 48L, first.trainingSteps());
        first.save(file);

        CognitiveCore100k restored = CognitiveCore100k.loadOrTrain(file);
        assertEquals(first.trainingSteps(), restored.trainingSteps());
        CognitivePrediction greeting = restored.predict("olá", "minecraft:villager");
        CognitivePrediction follow = restored.predict("me siga", "minecraft:wolf");
        CognitivePrediction pickup = restored.predict("pegue o item", "minecraft:creeper");
        assertEquals(1, greeting.speechAct());
        assertEquals(1, follow.action());
        assertEquals(9, pickup.action());
        assertTrue(greeting.speechConfidence() > 0.0F);
        assertTrue(follow.actionConfidence() > 0.0F);
    }
}
