package io.github.japaguimarassi.voxmobs;

import io.github.japaguimarassi.voxmobs.ai.IntentInterpreter;
import io.github.japaguimarassi.voxmobs.ai.MobAction;
import io.github.japaguimarassi.voxmobs.ai.ActionRequest;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class IntentInterpreterTest {
    @Test
    void recognizesPortugueseCommandsWithAccents() {
        assertEquals(MobAction.FOLLOW, IntentInterpreter.interpret("Me siga, por favor!"));
        assertEquals(MobAction.FLEE, IntentInterpreter.interpret("Fuja daqui."));
        assertEquals(MobAction.PROTECT, IntentInterpreter.interpret("Me proteja"));
        assertEquals(MobAction.LOOK, IntentInterpreter.interpret("Olhe pra mim"));
    }

    @Test
    void avoidsMatchingInsideUnrelatedWords() {
        assertEquals(MobAction.NONE, IntentInterpreter.interpret("Parece que vai chover"));
        assertEquals(MobAction.NONE, IntentInterpreter.interpret("Isso é para mim"));
    }

    @Test
    void recognizesItemAndModdedEntityCommands() {
        assertEquals(MobAction.PICKUP_ITEM, IntentInterpreter.parseCommand("Pegue o item no chão").action());
        assertEquals(MobAction.DROP_ITEM, IntentInterpreter.parseCommand("Solte o item").action());
        ActionRequest request = IntentInterpreter.parseCommand("Invoque mymod:forest_guardian");
        assertEquals(MobAction.SPAWN_MOB, request.action());
        assertEquals("mymod:forest_guardian", request.argument());
        assertEquals(MobAction.SPAWN_MOB, IntentInterpreter.parseCommand("spawn minecraft:zombie").action());
    }

    @Test
    void recognizesStopAndMovementCommands() {
        assertEquals(MobAction.STOP, IntentInterpreter.interpret("Fica aqui"));
        assertEquals(MobAction.APPROACH, IntentInterpreter.interpret("Venha aqui"));
        assertEquals(MobAction.JUMP, IntentInterpreter.interpret("Dá um pulo"));
    }
}
