package io.github.japaguimarassi.voxmobs.ai;

public record TrainingExample(String text, String mobType, int speechAct, int action,
                              int reaction, int memory, int voiceEmotion) {
    public TrainingExample {
        text = text == null ? "" : text;
        mobType = mobType == null ? "minecraft:unknown" : mobType;
        speechAct = clamp(speechAct);
        action = clamp(action);
        reaction = clamp(reaction);
        memory = clamp(memory);
        voiceEmotion = clamp(voiceEmotion);
    }

    private static int clamp(int value) {
        return Math.max(0, Math.min(15, value));
    }
}
