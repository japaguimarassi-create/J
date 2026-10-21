package app.deta.mobile;

import android.content.res.AssetManager;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.Random;

final class DetaLocalModel {
    private static final byte[] MAGIC = "DTA400K1".getBytes(StandardCharsets.US_ASCII);
    private static final int PARAMETER_COUNT = 400_000;
    private static final int GROUP_COUNT = 5;
    private static final int VOCAB_SIZE = 256;
    private static final int EMBEDDING_SIZE = 64;
    private static final int HIDDEN_SIZE = 88;
    private static final int GATE_SIZE = HIDDEN_SIZE * 3;
    private static final int CONTEXT_SIZE = 128;
    private static final int MAX_WEIGHT_BYTES = MAGIC.length + PARAMETER_COUNT * Float.BYTES;

    private static final class Group {
        final float[] embedding;
        final float[] weightInput;
        final float[] weightHidden;
        final float[] biasInput;
        final float[] biasHidden;
        final float[] hiddenScale;
        final float[] hiddenBias;
        final float[] outputWeight;
        final float[] outputBias;
        final float[] hidden = new float[HIDDEN_SIZE];

        Group(ByteBuffer buffer) throws IOException {
            embedding = readFloats(buffer, VOCAB_SIZE * EMBEDDING_SIZE);
            weightInput = readFloats(buffer, GATE_SIZE * EMBEDDING_SIZE);
            weightHidden = readFloats(buffer, GATE_SIZE * HIDDEN_SIZE);
            biasInput = readFloats(buffer, GATE_SIZE);
            biasHidden = readFloats(buffer, GATE_SIZE);
            hiddenScale = readFloats(buffer, HIDDEN_SIZE);
            hiddenBias = readFloats(buffer, HIDDEN_SIZE);
            outputWeight = readFloats(buffer, VOCAB_SIZE * HIDDEN_SIZE);
            outputBias = readFloats(buffer, VOCAB_SIZE);
        }

        void step(int token) {
            int embeddingOffset = token * EMBEDDING_SIZE;
            float[] inputGate = new float[GATE_SIZE];
            float[] hiddenGate = new float[GATE_SIZE];

            for (int row = 0; row < GATE_SIZE; row++) {
                int inputOffset = row * EMBEDDING_SIZE;
                float inputSum = biasInput[row];
                for (int column = 0; column < EMBEDDING_SIZE; column++) {
                    inputSum += weightInput[inputOffset + column] * embedding[embeddingOffset + column];
                }
                inputGate[row] = inputSum;

                int hiddenOffset = row * HIDDEN_SIZE;
                float hiddenSum = biasHidden[row];
                for (int column = 0; column < HIDDEN_SIZE; column++) {
                    hiddenSum += weightHidden[hiddenOffset + column] * hidden[column];
                }
                hiddenGate[row] = hiddenSum;
            }

            float[] nextHidden = new float[HIDDEN_SIZE];
            for (int index = 0; index < HIDDEN_SIZE; index++) {
                float reset = sigmoid(inputGate[index] + hiddenGate[index]);
                float update = sigmoid(inputGate[HIDDEN_SIZE + index] + hiddenGate[HIDDEN_SIZE + index]);
                float candidate = (float) Math.tanh(
                        inputGate[2 * HIDDEN_SIZE + index]
                                + reset * hiddenGate[2 * HIDDEN_SIZE + index]
                );
                nextHidden[index] = (1.0f - update) * candidate + update * hidden[index];
            }
            System.arraycopy(nextHidden, 0, hidden, 0, HIDDEN_SIZE);
        }

        void addLogits(float[] sum) {
            for (int token = 0; token < VOCAB_SIZE; token++) {
                int offset = token * HIDDEN_SIZE;
                float value = outputBias[token];
                for (int index = 0; index < HIDDEN_SIZE; index++) {
                    float adjusted = hidden[index] * (1.0f + (float) Math.tanh(hiddenScale[index])) + hiddenBias[index];
                    value += outputWeight[offset + index] * adjusted;
                }
                sum[token] += value;
            }
        }
    }

    private final Group[] groups;
    private final JSONObject metadata;

    private DetaLocalModel(Group[] groups, JSONObject metadata) {
        this.groups = groups;
        this.metadata = metadata;
    }

    static DetaLocalModel load(AssetManager assets) throws IOException {
        byte[] weights = readAsset(assets, "deta-400k.weights", MAX_WEIGHT_BYTES);
        if (weights.length != MAX_WEIGHT_BYTES) {
            throw new IOException("O tamanho do modelo não corresponde aos 400.000 parâmetros esperados.");
        }
        ByteBuffer buffer = ByteBuffer.wrap(weights).order(ByteOrder.LITTLE_ENDIAN);
        for (byte expected : MAGIC) {
            if (!buffer.hasRemaining() || buffer.get() != expected) {
                throw new IOException("O arquivo de pesos da Deta tem um cabeçalho inválido.");
            }
        }
        Group[] groups = new Group[GROUP_COUNT];
        for (int index = 0; index < GROUP_COUNT; index++) groups[index] = new Group(buffer);
        if (buffer.hasRemaining()) throw new IOException("O arquivo de pesos contém dados inesperados.");

        JSONObject metadata;
        try {
            byte[] metaBytes = readAsset(assets, "deta-model-info.json", 32 * 1024);
            metadata = new JSONObject(new String(metaBytes, StandardCharsets.UTF_8));
        } catch (JSONException exception) {
            throw new IOException("Os metadados do modelo estão inválidos.", exception);
        }
        if (metadata.optInt("parameter_count", -1) != PARAMETER_COUNT
                || metadata.optInt("group_count", -1) != GROUP_COUNT
                || !"DTA400K1".equals(metadata.optString("format", ""))) {
            throw new IOException("Os metadados não correspondem ao modelo Deta 400k.");
        }
        return new DetaLocalModel(groups, metadata);
    }

    int parameterCount() {
        return metadata.optInt("parameter_count", PARAMETER_COUNT);
    }

    int trainingSteps() {
        return metadata.optInt("cumulative_training_steps", 0);
    }

    JSONObject metadata() {
        return metadata;
    }

    String generate(String prompt, int maxTokens, float temperature, int topK, long seed) {
        if (prompt == null) throw new IllegalArgumentException("O texto de entrada não pode ser nulo.");
        if (maxTokens < 1 || maxTokens > 160) throw new IllegalArgumentException("A geração deve ter de 1 a 160 bytes.");
        if (!(temperature >= 0.15f && temperature <= 1.5f)) throw new IllegalArgumentException("Temperatura fora do intervalo permitido.");
        if (topK < 1 || topK > 64) throw new IllegalArgumentException("top-k deve estar entre 1 e 64.");

        byte[] bytes = prompt.getBytes(StandardCharsets.UTF_8);
        int start = Math.max(0, bytes.length - CONTEXT_SIZE);
        for (Group group : groups) Arrays.fill(group.hidden, 0.0f);
        for (int index = start; index < bytes.length; index++) stepAll(bytes[index] & 0xFF);
        if (bytes.length == 0) stepAll((int) '\n');

        Random random = new Random(seed);
        ByteArrayOutputStream output = new ByteArrayOutputStream(maxTokens);
        for (int index = 0; index < maxTokens; index++) {
            float[] logits = logits();
            int nextToken = sample(logits, temperature, topK, random);
            output.write(nextToken);
            stepAll(nextToken);
        }
        return output.toString(StandardCharsets.UTF_8);
    }

    private void stepAll(int token) {
        for (Group group : groups) group.step(token);
    }

    private float[] logits() {
        float[] result = new float[VOCAB_SIZE];
        for (Group group : groups) group.addLogits(result);
        return result;
    }

    private int sample(float[] logits, float temperature, int topK, Random random) {
        int count = Math.min(topK, logits.length);
        int[] indices = new int[count];
        float[] values = new float[count];
        Arrays.fill(values, Float.NEGATIVE_INFINITY);

        for (int token = 0; token < logits.length; token++) {
            float value = logits[token] / temperature;
            for (int slot = 0; slot < count; slot++) {
                if (value > values[slot]) {
                    for (int move = count - 1; move > slot; move--) {
                        values[move] = values[move - 1];
                        indices[move] = indices[move - 1];
                    }
                    values[slot] = value;
                    indices[slot] = token;
                    break;
                }
            }
        }

        float maximum = values[0];
        double total = 0.0;
        double[] probabilities = new double[count];
        for (int index = 0; index < count; index++) {
            probabilities[index] = Math.exp(Math.max(-80.0, values[index] - maximum));
            total += probabilities[index];
        }
        double draw = random.nextDouble() * total;
        for (int index = 0; index < count; index++) {
            draw -= probabilities[index];
            if (draw <= 0.0) return indices[index];
        }
        return indices[0];
    }

    private static float[] readFloats(ByteBuffer buffer, int count) throws IOException {
        if (count < 0 || buffer.remaining() < count * Float.BYTES) {
            throw new IOException("Os pesos do modelo estão truncados.");
        }
        float[] result = new float[count];
        for (int index = 0; index < count; index++) {
            float value = buffer.getFloat();
            if (Float.isNaN(value) || Float.isInfinite(value)) {
                throw new IOException("O modelo contém pesos não finitos.");
            }
            result[index] = value;
        }
        return result;
    }

    private static byte[] readAsset(AssetManager assets, String filename, int maximumBytes) throws IOException {
        try (InputStream stream = assets.open(filename); ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[8192];
            int count;
            while ((count = stream.read(buffer)) != -1) {
                if (output.size() + count > maximumBytes) throw new IOException("O arquivo " + filename + " excede o limite permitido.");
                output.write(buffer, 0, count);
            }
            return output.toByteArray();
        }
    }

    private static float sigmoid(float value) {
        if (value >= 0.0f) {
            double exp = Math.exp(-Math.min(value, 80.0f));
            return (float) (1.0 / (1.0 + exp));
        }
        double exp = Math.exp(Math.max(value, -80.0f));
        return (float) (exp / (1.0 + exp));
    }
}
