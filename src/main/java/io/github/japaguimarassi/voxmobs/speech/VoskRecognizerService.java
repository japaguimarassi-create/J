package io.github.japaguimarassi.voxmobs.speech;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import org.vosk.Model;
import org.vosk.Recognizer;

import java.nio.file.Path;

public final class VoskRecognizerService {
    private static Model cachedModel;
    private static Path cachedPath;

    private VoskRecognizerService() {
    }

    public static String transcribe(byte[] pcm16k) throws Exception {
        if (pcm16k == null || pcm16k.length < 1600) {
            return "";
        }
        Path path = SpeechModelManager.modelDirectory();
        Model model = getModel(path);
        try (Recognizer recognizer = new Recognizer(model, 16000.0F)) {
            recognizer.acceptWaveForm(pcm16k, pcm16k.length);
            JsonObject result = JsonParser.parseString(recognizer.getFinalResult()).getAsJsonObject();
            return result.has("text") ? result.get("text").getAsString().trim() : "";
        }
    }

    private static synchronized Model getModel(Path path) throws Exception {
        if (cachedModel != null && path.equals(cachedPath)) {
            return cachedModel;
        }
        if (cachedModel != null) {
            cachedModel.close();
        }
        cachedModel = new Model(path.toString());
        cachedPath = path;
        return cachedModel;
    }
}
