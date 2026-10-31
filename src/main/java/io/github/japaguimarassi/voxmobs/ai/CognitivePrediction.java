package io.github.japaguimarassi.voxmobs.ai;

public record CognitivePrediction(int speechAct, float speechConfidence,
                                  int action, float actionConfidence,
                                  int reaction, float reactionConfidence,
                                  int memory, float memoryConfidence,
                                  int voiceEmotion, float voiceConfidence) {
    public static final String[] SPEECH_ACTS = {
            "other", "greeting", "identity", "question", "thanks", "apology", "farewell", "help",
            "warning", "command", "preference", "story", "agreement", "disagreement", "curiosity", "comfort"
    };
    public static final String[] ACTIONS = {
            "none", "follow", "approach", "flee", "look", "sit", "jump", "stop",
            "protect", "pickup_item", "drop_item", "spawn_mob", "attack", "trade", "interact", "guard"
    };
    public static final String[] REACTIONS = {
            "neutral", "curious", "happy", "afraid", "defensive", "angry", "shy", "grateful",
            "sad", "alert", "playful", "confused", "stubborn", "affectionate", "tired", "excited"
    };
    public static final String[] MEMORY_TYPES = {
            "none", "player_name", "preference", "promise", "important_event", "relationship", "danger",
            "location", "item", "recent_conversation", "trust", "fear", "goal", "trade", "group", "other"
    };
    public static final String[] VOICE_EMOTIONS = {
            "neutral", "calm", "happy", "fearful", "angry", "whisper", "excited", "sad",
            "curious", "tired", "alert", "warm", "robotic", "playful", "serious", "surprised"
    };
}
