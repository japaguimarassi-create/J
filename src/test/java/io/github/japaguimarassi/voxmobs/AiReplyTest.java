package io.github.japaguimarassi.voxmobs;

import io.github.japaguimarassi.voxmobs.ai.AiReply;
import io.github.japaguimarassi.voxmobs.ai.MobAction;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class AiReplyTest {
    @Test
    void parsesOnlyWhitelistedActions() {
        AiReply allowed = AiReply.parse("{\"reply\":\"Olá\",\"action\":\"FOLLOW\",\"emotion\":\"amigável\"}");
        AiReply invalid = AiReply.parse("{\"reply\":\"Olá\",\"action\":\"EXECUTE_COMMAND\"}");
        assertEquals(MobAction.FOLLOW, allowed.action());
        assertEquals(MobAction.NONE, invalid.action());
    }
}
