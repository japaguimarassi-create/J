package br.com.realityengineai;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.text.Normalizer;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class OfflineBrain {
    public static final int PARAMETER_COUNT = 300000;
    private static final int VOCABULARY = 881;
    private static final int EMBEDDING = 256;
    private static final int HIDDEN = 264;
    private static final int OUTPUTS = 24;
    private static final String RESOURCE = "/assets/realityengineai/brain/weights.bin";
    public static final String[] LABELS = {
        "block_computer", "block_crystal", "block_generic", "entity_dragon",
        "entity_hostile", "entity_creature", "item_sword", "item_tool",
        "item_food", "item_generic", "dimension_desert", "dimension_cold",
        "dimension_forest", "dimension_space", "dimension_infernal",
        "dimension_generic", "query_mods", "query_blocks", "query_items",
        "query_entities", "query_dimensions", "command_enter", "ask_help",
        "ambiguous"
    };
    private static final Pattern TOKENS = Pattern.compile("[a-z0-9]+");
    private float[] parameters;
    private boolean ready;
    private int parameterCount;

    public OfflineBrain() {
        load();
    }

    private void load() {
        try {
            InputStream stream = OfflineBrain.class.getResourceAsStream(RESOURCE);
            if (stream == null) {
                return;
            }
            ByteArrayOutputStream output = new ByteArrayOutputStream();
            byte[] chunk = new byte[8192];
            int length;
            while ((length = stream.read(chunk)) != -1) {
                output.write(chunk, 0, length);
            }
            stream.close();
            byte[] bytes = output.toByteArray();
            byte[] magic = "REAI300K1".getBytes("US-ASCII");
            if (bytes.length != magic.length + PARAMETER_COUNT * 4) {
                return;
            }
            for (int i = 0; i < magic.length; i++) {
                if (bytes[i] != magic[i]) {
                    return;
                }
            }
            ByteBuffer buffer = ByteBuffer.wrap(bytes, magic.length, bytes.length - magic.length).order(ByteOrder.LITTLE_ENDIAN);
            parameters = new float[PARAMETER_COUNT];
            for (int i = 0; i < parameters.length; i++) {
                parameters[i] = buffer.getFloat();
            }
            parameterCount = parameters.length;
            ready = true;
        } catch (IOException exception) {
            RealityEngineAI.LOG.warn("Offline brain weights could not be loaded.", exception);
        }
    }

    public boolean isReady() {
        return ready;
    }

    public int getParameterCount() {
        return parameterCount;
    }

    public String predict(String input) {
        return predictDetailed(input).label;
    }

    public Prediction predictDetailed(String input) {
        if (!ready || input == null) {
            return new Prediction("ambiguous", 0.0F);
        }
        Set<Integer> features = featureIds(input);
        if (features.isEmpty()) {
            return new Prediction("ambiguous", 0.0F);
        }

        int offset = 0;
        float[] embeddingWeights = parameters;
        offset += VOCABULARY * EMBEDDING;
        float[] inputBias = slice(offset, EMBEDDING);
        offset += EMBEDDING;
        float[] hiddenWeights = slice(offset, EMBEDDING * HIDDEN);
        offset += EMBEDDING * HIDDEN;
        float[] hiddenBias = slice(offset, HIDDEN);
        offset += HIDDEN;
        float[] outputWeights = slice(offset, HIDDEN * OUTPUTS);
        offset += HIDDEN * OUTPUTS;
        float[] outputBias = slice(offset, OUTPUTS);

        float[] inputVector = inputBias.clone();
        float scale = 1.0F / features.size();
        for (Integer feature : features) {
            int base = feature.intValue() * EMBEDDING;
            for (int j = 0; j < EMBEDDING; j++) {
                inputVector[j] += embeddingWeights[base + j] * scale;
            }
        }

        float[] hidden = new float[HIDDEN];
        for (int j = 0; j < HIDDEN; j++) {
            float sum = hiddenBias[j];
            for (int i = 0; i < EMBEDDING; i++) {
                sum += inputVector[i] * hiddenWeights[i * HIDDEN + j];
            }
            hidden[j] = sum > 0.0F ? sum : 0.0F;
        }

        float[] logits = new float[OUTPUTS];
        float max = -Float.MAX_VALUE;
        int best = 0;
        for (int j = 0; j < OUTPUTS; j++) {
            float sum = outputBias[j];
            for (int i = 0; i < HIDDEN; i++) {
                sum += hidden[i] * outputWeights[i * OUTPUTS + j];
            }
            logits[j] = sum;
            if (sum > max) {
                max = sum;
                best = j;
            }
        }

        double total = 0.0D;
        double[] probabilities = new double[OUTPUTS];
        for (int j = 0; j < OUTPUTS; j++) {
            probabilities[j] = Math.exp(Math.max(-60.0D, Math.min(0.0D, logits[j] - max)));
            total += probabilities[j];
        }
        return new Prediction(LABELS[best], total == 0.0D ? 0.0F : (float) (probabilities[best] / total));
    }

    private float[] slice(int start, int length) {
        float[] result = new float[length];
        System.arraycopy(parameters, start, result, 0, length);
        return result;
    }

    static Set<Integer> featureIds(String input) {
        String normalized = Normalizer.normalize(input.toLowerCase(Locale.ROOT), Normalizer.Form.NFD).replaceAll("\\p{M}", "");
        Matcher matcher = TOKENS.matcher(normalized);
        List<String> words = new ArrayList<String>();
        while (matcher.find()) {
            words.add(matcher.group());
        }
        Set<Integer> features = new HashSet<Integer>();
        for (String word : words) {
            features.add(Integer.valueOf(hashBucket(word)));
        }
        for (int i = 0; i + 1 < words.size(); i++) {
            features.add(Integer.valueOf(hashBucket(words.get(i) + " " + words.get(i + 1))));
        }
        return features;
    }

    private static int hashBucket(String value) {
        int hash = 0;
        for (int i = 0; i < value.length(); i++) {
            hash = 31 * hash + value.charAt(i);
        }
        return (hash & 0x7fffffff) % VOCABULARY;
    }

    public static final class Prediction {
        public final String label;
        public final float confidence;

        public Prediction(String label, float confidence) {
            this.label = label;
            this.confidence = confidence;
        }
    }
}
