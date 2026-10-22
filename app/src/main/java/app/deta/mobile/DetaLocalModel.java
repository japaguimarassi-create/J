package app.deta.mobile;

import android.content.res.AssetManager;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.Random;

final class DetaLocalModel {
    static final int PARAMETER_COUNT = 400000;
    static final int GROUP_COUNT = 5;
    private static final int HIDDEN = 88;
    private static final int EMBEDDING = 64;
    private static final int VOCABULARY = 256;
    private static final int GATES = HIDDEN * 3;
    private final Group[] groups = new Group[GROUP_COUNT];

    static DetaLocalModel fromAssets(AssetManager assets) throws IOException {
        return new DetaLocalModel(assets.open("deta-model.bin"));
    }

    DetaLocalModel(InputStream stream) throws IOException {
        byte[] bytes;
        try (InputStream input = stream; ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[16384];
            int read;
            while ((read = input.read(buffer)) != -1) output.write(buffer, 0, read);
            bytes = output.toByteArray();
        }
        if (bytes.length != PARAMETER_COUNT * 4) {
            throw new IOException("The bundled Deta model has an invalid size.");
        }
        ByteBuffer buffer = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN);
        int counted = 0;
        for (int index = 0; index < groups.length; index++) {
            groups[index] = new Group(buffer);
            counted += groups[index].parameterCount();
        }
        if (counted != PARAMETER_COUNT || buffer.hasRemaining()) {
            throw new IOException("The bundled Deta model failed its parameter-layout check.");
        }
    }

    int parameterCount() {
        return PARAMETER_COUNT;
    }

    String generate(String prompt, int maxNewBytes, float temperature, int topK, long seed) {
        if (prompt == null) throw new IllegalArgumentException("Prompt is required.");
        if (maxNewBytes < 1 || maxNewBytes > 256) throw new IllegalArgumentException("Generation length must be from 1 to 256 bytes.");
        if (!(temperature >= 0.1f && temperature <= 1.5f)) throw new IllegalArgumentException("Temperature must be from 0.1 to 1.5.");
        if (topK < 1 || topK > 64) throw new IllegalArgumentException("topK must be from 1 to 64.");

        byte[] promptBytes = prompt.getBytes(StandardCharsets.UTF_8);
        if (promptBytes.length == 0) promptBytes = new byte[]{10};
        int start = Math.max(0, promptBytes.length - 128);
        float[][] states = new float[GROUP_COUNT][HIDDEN];
        for (int index = start; index < promptBytes.length; index++) {
            stepAll(promptBytes[index] & 0xff, states);
        }

        Random random = new Random(seed);
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        for (int index = 0; index < maxNewBytes; index++) {
            float[] logits = combinedLogits(states);
            int next = sample(logits, temperature, topK, random);
            output.write(next);
            stepAll(next, states);
        }
        return new String(output.toByteArray(), StandardCharsets.UTF_8);
    }

    private void stepAll(int token, float[][] states) {
        for (int index = 0; index < groups.length; index++) groups[index].step(token, states[index]);
    }

    private float[] combinedLogits(float[][] states) {
        float[] total = new float[VOCABULARY];
        for (int groupIndex = 0; groupIndex < groups.length; groupIndex++) {
            Group group = groups[groupIndex];
            float[] hidden = states[groupIndex];
            float[] adjusted = group.adjustedHidden(hidden);
            for (int token = 0; token < VOCABULARY; token++) {
                float value = group.outputBias[token];
                int row = token * HIDDEN;
                for (int index = 0; index < HIDDEN; index++) value += group.outputWeight[row + index] * adjusted[index];
                total[token] += value;
            }
        }
        return total;
    }

    private static int sample(float[] logits, float temperature, int topK, Random random) {
        int count = Math.min(topK, logits.length);
        int[] bestIndices = new int[count];
        float[] bestValues = new float[count];
        Arrays.fill(bestValues, Float.NEGATIVE_INFINITY);
        for (int index = 0; index < logits.length; index++) {
            float value = logits[index] / temperature;
            for (int rank = 0; rank < count; rank++) {
                if (value > bestValues[rank]) {
                    for (int move = count - 1; move > rank; move--) {
                        bestValues[move] = bestValues[move - 1];
                        bestIndices[move] = bestIndices[move - 1];
                    }
                    bestValues[rank] = value;
                    bestIndices[rank] = index;
                    break;
                }
            }
        }
        if (count == 1) return bestIndices[0];
        float max = bestValues[0];
        double sum = 0;
        double[] probabilities = new double[count];
        for (int index = 0; index < count; index++) {
            probabilities[index] = Math.exp(bestValues[index] - max);
            sum += probabilities[index];
        }
        double choice = random.nextDouble() * sum;
        for (int index = 0; index < count; index++) {
            choice -= probabilities[index];
            if (choice <= 0) return bestIndices[index];
        }
        return bestIndices[0];
    }

    private static float sigmoid(float value) {
        if (value >= 0) {
            double e = Math.exp(-value);
            return (float) (1.0 / (1.0 + e));
        }
        double e = Math.exp(value);
        return (float) (e / (1.0 + e));
    }

    private static final class Group {
        final float[] hiddenScale = new float[HIDDEN];
        final float[] hiddenBias = new float[HIDDEN];
        final float[] embedding = new float[VOCABULARY * EMBEDDING];
        final float[] inputWeight = new float[GATES * EMBEDDING];
        final float[] hiddenWeight = new float[GATES * HIDDEN];
        final float[] inputBias = new float[GATES];
        final float[] recurrentBias = new float[GATES];
        final float[] outputWeight = new float[VOCABULARY * HIDDEN];
        final float[] outputBias = new float[VOCABULARY];
        final float[] inputGates = new float[GATES];
        final float[] recurrentGates = new float[GATES];
        final float[] nextHidden = new float[HIDDEN];

        Group(ByteBuffer source) throws IOException {
            read(source, hiddenScale);
            read(source, hiddenBias);
            read(source, embedding);
            read(source, inputWeight);
            read(source, hiddenWeight);
            read(source, inputBias);
            read(source, recurrentBias);
            read(source, outputWeight);
            read(source, outputBias);
        }

        int parameterCount() {
            return hiddenScale.length + hiddenBias.length + embedding.length
                    + inputWeight.length + hiddenWeight.length + inputBias.length
                    + recurrentBias.length + outputWeight.length + outputBias.length;
        }

        float[] adjustedHidden(float[] hidden) {
            float[] adjusted = new float[HIDDEN];
            for (int index = 0; index < HIDDEN; index++) {
                adjusted[index] = hidden[index] * (1.0f + (float) Math.tanh(hiddenScale[index])) + hiddenBias[index];
            }
            return adjusted;
        }

        void step(int token, float[] hidden) {
            int embeddingOffset = (token & 0xff) * EMBEDDING;
            for (int gate = 0; gate < GATES; gate++) {
                int row = gate * EMBEDDING;
                float value = inputBias[gate];
                for (int index = 0; index < EMBEDDING; index++) {
                    value += inputWeight[row + index] * embedding[embeddingOffset + index];
                }
                inputGates[gate] = value;
            }
            for (int gate = 0; gate < GATES; gate++) {
                int row = gate * HIDDEN;
                float value = recurrentBias[gate];
                for (int index = 0; index < HIDDEN; index++) value += hiddenWeight[row + index] * hidden[index];
                recurrentGates[gate] = value;
            }
            for (int index = 0; index < HIDDEN; index++) {
                float reset = sigmoid(inputGates[index] + recurrentGates[index]);
                float update = sigmoid(inputGates[HIDDEN + index] + recurrentGates[HIDDEN + index]);
                float candidate = (float) Math.tanh(
                        inputGates[HIDDEN * 2 + index]
                                + reset * recurrentGates[HIDDEN * 2 + index]
                );
                nextHidden[index] = (1.0f - update) * candidate + update * hidden[index];
            }
            System.arraycopy(nextHidden, 0, hidden, 0, HIDDEN);
        }

        private static void read(ByteBuffer source, float[] destination) throws IOException {
            if (source.remaining() < destination.length * 4) throw new IOException("Truncated Deta model weights.");
            for (int index = 0; index < destination.length; index++) {
                float value = source.getFloat();
                if (Float.isNaN(value) || Float.isInfinite(value)) throw new IOException("Invalid numeric value in Deta model weights.");
                destination[index] = value;
            }
        }
    }
}
