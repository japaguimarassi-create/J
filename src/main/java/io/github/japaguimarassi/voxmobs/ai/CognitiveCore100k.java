package io.github.japaguimarassi.voxmobs.ai;

import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.Random;

public final class CognitiveCore100k {
    public static final int PARAMETER_COUNT = 100_000;
    private static final int FEATURE_COUNT = 256;
    private static final int EMBEDDING_SIZE = 128;
    private static final int HIDDEN_SIZE = 256;
    private static final int CLASS_COUNT = 16;
    private static final int HEAD_COUNT = 5;
    private static final int SPECIES_COUNT = 64;
    private static final int SPECIES_STRIDE = 212;
    private static final int EMBEDDING_OFFSET = 0;
    private static final int SHARED_OFFSET = EMBEDDING_OFFSET + FEATURE_COUNT * EMBEDDING_SIZE;
    private static final int HIDDEN_BIAS_OFFSET = SHARED_OFFSET + EMBEDDING_SIZE * HIDDEN_SIZE;
    private static final int HEAD_OFFSET = HIDDEN_BIAS_OFFSET + HIDDEN_SIZE;
    private static final int SPECIES_OFFSET = HEAD_OFFSET + HEAD_COUNT * HIDDEN_SIZE * CLASS_COUNT;
    private static final int GLOBAL_OFFSET = SPECIES_OFFSET + SPECIES_COUNT * SPECIES_STRIDE;
    private static final int MAGIC = 0x564D3130;
    private static final int VERSION = 1;
    private static final float[] TEMPERATURE_SCHEDULE = {0.55F, 0.72F, 0.88F, 1.0F, 1.14F, 1.28F};
    private static final float[][] CLASS_WEIGHTS = buildClassWeights();

    private final float[] parameters = new float[PARAMETER_COUNT];
    private final Random random = new Random(0x4D4F424D494E4431L);
    private long trainingSteps;
    private long successfulActions;
    private long rejectedActions;

    private CognitiveCore100k() {
        initialize();
    }

    public static CognitiveCore100k loadOrTrain(Path file) throws IOException {
        CognitiveCore100k core = new CognitiveCore100k();
        if (Files.isRegularFile(file)) {
            try {
                core.load(file);
                return core;
            } catch (IOException | RuntimeException ignored) {
                Files.move(file, file.resolveSibling(file.getFileName() + ".corrupt"), StandardCopyOption.REPLACE_EXISTING);
            }
        }
        core.trainCorpus();
        core.save(file);
        return core;
    }

    public synchronized CognitivePrediction predict(String text, String mobType) {
        Forward forward = forward(text, mobType, 1.0F);
        int[] labels = new int[HEAD_COUNT];
        float[] confidence = new float[HEAD_COUNT];
        for (int head = 0; head < HEAD_COUNT; head++) {
            for (int label = 0; label < CLASS_COUNT; label++) {
                if (forward.probabilities[head][label] > confidence[head]) {
                    confidence[head] = forward.probabilities[head][label];
                    labels[head] = label;
                }
            }
        }
        return new CognitivePrediction(labels[0], confidence[0], labels[1], confidence[1],
                labels[2], confidence[2], labels[3], confidence[3], labels[4], confidence[4]);
    }

    public synchronized void learnFromOutcome(String text, String mobType, MobAction action, boolean succeeded) {
        int actionClass = actionClass(action);
        if (!succeeded) {
            actionClass = 0;
            rejectedActions++;
        } else {
            successfulActions++;
        }
        Forward current = forward(text, mobType, 1.0F);
        TrainingExample example = new TrainingExample(text, mobType,
                current.best[0], actionClass,
                succeeded ? 2 : 11,
                succeeded ? 2 : 0,
                succeeded ? 2 : 11);
        trainOne(example, succeeded ? 0.0025F : 0.004F, 0.85F);
    }

    public synchronized void learnFromTeaching(String phrase, String mobType, MobAction action) {
        if (phrase == null || phrase.isBlank() || phrase.length() > 240 || action == null || action == MobAction.NONE) {
            throw new IllegalArgumentException("A frase e uma ação válida são obrigatórias.");
        }
        int targetAction = actionClass(action);
        String normalizedMob = mobType == null || mobType.isBlank() ? "minecraft:generic" : mobType;
        TrainingExample base = new TrainingExample(phrase, normalizedMob, 9, targetAction, 1, 9, 1);
        float[] temperatures = {0.62F, 0.78F, 0.96F, 1.12F, 0.88F, 1.24F};
        for (int pass = 0; pass < 48; pass++) {
            float temperature = temperatures[pass % temperatures.length];
            float learningRate = 0.012F / (1.0F + pass * 0.035F);
            trainOne(base, learningRate, temperature);
        }
    }

    public synchronized long trainingSteps() {
        return trainingSteps;
    }

    public synchronized long successfulActions() {
        return successfulActions;
    }

    public synchronized long rejectedActions() {
        return rejectedActions;
    }

    public int parameterCount() {
        return parameters.length;
    }

    public synchronized void save(Path file) throws IOException {
        Path parent = file.toAbsolutePath().getParent();
        if (parent != null) {
            Files.createDirectories(parent);
        }
        Path temporary = file.resolveSibling(file.getFileName() + ".tmp");
        try (DataOutputStream output = new DataOutputStream(new BufferedOutputStream(Files.newOutputStream(temporary)))) {
            output.writeInt(MAGIC);
            output.writeInt(VERSION);
            output.writeInt(PARAMETER_COUNT);
            output.writeLong(trainingSteps);
            output.writeLong(successfulActions);
            output.writeLong(rejectedActions);
            for (float parameter : parameters) {
                output.writeFloat(parameter);
            }
        }
        try {
            Files.move(temporary, file, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
        } catch (IOException ignored) {
            Files.move(temporary, file, StandardCopyOption.REPLACE_EXISTING);
        }
    }

    private synchronized void load(Path file) throws IOException {
        try (DataInputStream input = new DataInputStream(new BufferedInputStream(Files.newInputStream(file)))) {
            if (input.readInt() != MAGIC || input.readInt() != VERSION || input.readInt() != PARAMETER_COUNT) {
                throw new IOException("Unsupported VoxMobs brain format");
            }
            trainingSteps = input.readLong();
            successfulActions = input.readLong();
            rejectedActions = input.readLong();
            for (int i = 0; i < parameters.length; i++) {
                parameters[i] = input.readFloat();
            }
            if (input.read() != -1) {
                throw new IOException("Unexpected data after brain weights");
            }
        }
    }

    private void initialize() {
        for (int i = 0; i < parameters.length; i++) {
            parameters[i] = 0.0F;
        }
        for (int i = EMBEDDING_OFFSET; i < SHARED_OFFSET; i++) {
            parameters[i] = gaussian() * 0.08F;
        }
        for (int i = SHARED_OFFSET; i < HIDDEN_BIAS_OFFSET; i++) {
            parameters[i] = gaussian() * 0.055F;
        }
        for (int i = HIDDEN_BIAS_OFFSET; i < HEAD_OFFSET; i++) {
            parameters[i] = gaussian() * 0.015F;
        }
        for (int i = HEAD_OFFSET; i < SPECIES_OFFSET; i++) {
            parameters[i] = gaussian() * 0.04F;
        }
    }

    private float gaussian() {
        return (float) random.nextGaussian();
    }

    private void trainCorpus() {
        List<TrainingExample> corpus = CoreTrainingCorpus.examples();
        List<TrainingExample> training = new ArrayList<>();
        List<TrainingExample> validation = new ArrayList<>();
        for (int i = 0; i < corpus.size(); i++) {
            if (i % 5 == 0) {
                validation.add(corpus.get(i));
            } else {
                training.add(corpus.get(i));
            }
        }
        float[] bestParameters = parameters.clone();
        float bestValidation = Double.isFinite(validationLoss(validation)) ? validationLoss(validation) : Float.MAX_VALUE;
        Random shuffle = new Random(917331L);
        for (int epoch = 0; epoch < 34; epoch++) {
            Collections.shuffle(training, shuffle);
            float temperature = TEMPERATURE_SCHEDULE[epoch % TEMPERATURE_SCHEDULE.length];
            float learningRate = 0.019F / (1.0F + epoch * 0.03F);
            for (TrainingExample example : training) {
                trainOne(example, learningRate, temperature);
            }
            if (epoch >= 6 && epoch % 3 == 0) {
                List<RankedExample> ranked = new ArrayList<>();
                for (TrainingExample example : training) {
                    ranked.add(new RankedExample(example, loss(example, temperature)));
                }
                ranked.sort(Comparator.comparingDouble(RankedExample::loss));
                int reviewCount = Math.max(1, ranked.size() / 6);
                for (int i = 0; i < reviewCount; i++) {
                    trainOne(ranked.get(i).example(), learningRate * 0.3F, 0.9F);
                }
                for (int i = ranked.size() - reviewCount; i < ranked.size(); i++) {
                    trainOne(ranked.get(i).example(), learningRate * 0.85F, 0.75F);
                }
            }
            if (epoch % 2 == 0 || epoch == 33) {
                float score = validationLoss(validation);
                if (score < bestValidation) {
                    bestValidation = score;
                    bestParameters = parameters.clone();
                }
            }
        }
        System.arraycopy(bestParameters, 0, parameters, 0, parameters.length);
    }

    private float validationLoss(List<TrainingExample> examples) {
        if (examples.isEmpty()) {
            return Float.MAX_VALUE;
        }
        double sum = 0.0D;
        for (TrainingExample example : examples) {
            sum += loss(example, 1.0F);
        }
        return (float) (sum / examples.size());
    }

    private float loss(TrainingExample example, float temperature) {
        Forward forward = forward(example.text(), example.mobType(), temperature);
        int[] labels = labels(example);
        double total = 0.0D;
        for (int head = 0; head < HEAD_COUNT; head++) {
            total -= Math.log(Math.max(1.0E-7F, forward.probabilities[head][labels[head]]));
        }
        return (float) total / HEAD_COUNT;
    }

    private void trainOne(TrainingExample example, float learningRate, float temperature) {
        trainingSteps++;
        Forward forward = forward(example.text(), example.mobType(), temperature);
        int[] expected = labels(example);
        float[] hiddenDelta = new float[HIDDEN_SIZE];
        int species = speciesIndex(example.mobType());
        int speciesBase = SPECIES_OFFSET + species * SPECIES_STRIDE;
        for (int head = 0; head < HEAD_COUNT; head++) {
            int headBase = HEAD_OFFSET + head * HIDDEN_SIZE * CLASS_COUNT;
            float[] error = new float[CLASS_COUNT];
            for (int label = 0; label < CLASS_COUNT; label++) {
                error[label] = forward.probabilities[head][label] - (label == expected[head] ? 1.0F : 0.0F);
                int speciesBias = speciesBase + 192 + head * 4 + label % 4;
                float sampleWeight = CLASS_WEIGHTS[head][expected[head]];
                float corrected = error[label] * sampleWeight / temperature;
                parameters[GLOBAL_OFFSET + head * CLASS_COUNT + label] -= learningRate * corrected;
                parameters[speciesBias] -= learningRate * corrected * 0.25F;
                int outputBase = headBase + label * HIDDEN_SIZE;
                for (int h = 0; h < HIDDEN_SIZE; h++) {
                    float weight = parameters[outputBase + h];
                    hiddenDelta[h] += weight * corrected;
                    parameters[outputBase + h] -= learningRate * corrected * forward.hidden[h];
                }
            }
        }
        float[] preActivationDelta = new float[HIDDEN_SIZE];
        float[] embeddingDelta = new float[EMBEDDING_SIZE];
        for (int h = 0; h < HIDDEN_SIZE; h++) {
            float hiddenDerivative = 1.0F - forward.hidden[h] * forward.hidden[h];
            float adapterScale = 1.0F + parameters[speciesBase + h % 128] * 0.15F;
            float adapterDelta = hiddenDelta[h] * hiddenDerivative;
            float preAdapterDerivative = 1.0F - forward.preAdapter[h] * forward.preAdapter[h];
            preActivationDelta[h] = adapterDelta * adapterScale * preAdapterDerivative;
            parameters[speciesBase + h % 128] -= learningRate * adapterDelta * forward.preAdapter[h] * 0.15F;
            parameters[speciesBase + 128 + h % 64] -= learningRate * adapterDelta * 0.08F;
            parameters[HIDDEN_BIAS_OFFSET + h] -= learningRate * preActivationDelta[h];
            parameters[GLOBAL_OFFSET + 80 + h % 80] -= learningRate * preActivationDelta[h] * 0.04F;
            int sharedBase = SHARED_OFFSET + h * EMBEDDING_SIZE;
            for (int e = 0; e < EMBEDDING_SIZE; e++) {
                float oldWeight = parameters[sharedBase + e];
                embeddingDelta[e] += oldWeight * preActivationDelta[h];
                parameters[sharedBase + e] -= learningRate * preActivationDelta[h] * forward.embedding[e];
            }
        }
        float featureScale = (float) (1.0D / Math.sqrt(Math.max(1, forward.activeFeatures.indices.length)));
        for (int i = 0; i < forward.activeFeatures.indices.length; i++) {
            int embeddingBase = EMBEDDING_OFFSET + forward.activeFeatures.indices[i] * EMBEDDING_SIZE;
            float featureValue = forward.activeFeatures.values[i] * featureScale;
            for (int e = 0; e < EMBEDDING_SIZE; e++) {
                parameters[embeddingBase + e] -= learningRate * embeddingDelta[e] * featureValue;
            }
        }
    }

    private Forward forward(String text, String mobType, float temperature) {
        SparseFeatures active = features(text, mobType);
        float[] embedding = new float[EMBEDDING_SIZE];
        float scale = (float) (1.0D / Math.sqrt(Math.max(1, active.indices.length)));
        for (int i = 0; i < active.indices.length; i++) {
            int base = EMBEDDING_OFFSET + active.indices[i] * EMBEDDING_SIZE;
            float value = active.values[i] * scale;
            for (int e = 0; e < EMBEDDING_SIZE; e++) {
                embedding[e] += parameters[base + e] * value;
            }
        }
        int speciesBase = SPECIES_OFFSET + speciesIndex(mobType) * SPECIES_STRIDE;
        float[] preAdapter = new float[HIDDEN_SIZE];
        float[] hidden = new float[HIDDEN_SIZE];
        for (int h = 0; h < HIDDEN_SIZE; h++) {
            float sum = parameters[HIDDEN_BIAS_OFFSET + h] + parameters[GLOBAL_OFFSET + 80 + h % 80] * 0.04F;
            int base = SHARED_OFFSET + h * EMBEDDING_SIZE;
            for (int e = 0; e < EMBEDDING_SIZE; e++) {
                sum += parameters[base + e] * embedding[e];
            }
            preAdapter[h] = (float) Math.tanh(sum);
            float speciesScale = 1.0F + parameters[speciesBase + h % 128] * 0.15F;
            float speciesShift = parameters[speciesBase + 128 + h % 64] * 0.08F;
            hidden[h] = (float) Math.tanh(preAdapter[h] * speciesScale + speciesShift);
        }
        float[][] probabilities = new float[HEAD_COUNT][CLASS_COUNT];
        int[] best = new int[HEAD_COUNT];
        for (int head = 0; head < HEAD_COUNT; head++) {
            int headBase = HEAD_OFFSET + head * HIDDEN_SIZE * CLASS_COUNT;
            float maximum = -Float.MAX_VALUE;
            for (int label = 0; label < CLASS_COUNT; label++) {
                float logit = parameters[GLOBAL_OFFSET + head * CLASS_COUNT + label]
                        + parameters[speciesBase + 192 + head * 4 + label % 4];
                int base = headBase + label * HIDDEN_SIZE;
                for (int h = 0; h < HIDDEN_SIZE; h++) {
                    logit += parameters[base + h] * hidden[h];
                }
                logit /= Math.max(0.35F, temperature);
                probabilities[head][label] = logit;
                maximum = Math.max(maximum, logit);
            }
            double total = 0.0D;
            for (int label = 0; label < CLASS_COUNT; label++) {
                double value = Math.exp(Math.max(-24.0F, probabilities[head][label] - maximum));
                probabilities[head][label] = (float) value;
                total += value;
            }
            float bestProbability = -1.0F;
            for (int label = 0; label < CLASS_COUNT; label++) {
                probabilities[head][label] /= (float) total;
                if (probabilities[head][label] > bestProbability) {
                    bestProbability = probabilities[head][label];
                    best[head] = label;
                }
            }
        }
        return new Forward(embedding, preAdapter, hidden, probabilities, active, best);
    }

    private static SparseFeatures features(String text, String mobType) {
        float[] vector = new float[FEATURE_COUNT];
        addFeatures(vector, normalize(text), 1.0F);
        addFeatures(vector, normalize(mobType), 0.55F);
        int count = 0;
        for (float value : vector) {
            if (value != 0.0F) {
                count++;
            }
        }
        int[] indices = new int[count];
        float[] values = new float[count];
        int index = 0;
        for (int i = 0; i < vector.length; i++) {
            if (vector[i] != 0.0F) {
                indices[index] = i;
                values[index] = vector[i];
                index++;
            }
        }
        return new SparseFeatures(indices, values);
    }

    private static void addFeatures(float[] vector, String text, float weight) {
        String[] tokens = text.split("\\s+");
        for (String token : tokens) {
            if (token.isBlank()) {
                continue;
            }
            addHashed(vector, "w:" + token, weight);
        }
        for (int i = 0; i + 1 < tokens.length; i++) {
            addHashed(vector, "b:" + tokens[i] + "_" + tokens[i + 1], weight * 0.72F);
        }
        String compact = text.replace(" ", "_");
        for (int i = 0; i + 2 < compact.length(); i++) {
            addHashed(vector, "c:" + compact.substring(i, i + 3), weight * 0.18F);
        }
    }

    private static void addHashed(float[] vector, String value, float weight) {
        int hash = value.toLowerCase(Locale.ROOT).hashCode();
        int index = Math.floorMod(hash, FEATURE_COUNT);
        float sign = (hash & 0x100) == 0 ? 1.0F : -1.0F;
        vector[index] += weight * sign;
    }

    private static String normalize(String value) {
        if (value == null) {
            return "";
        }
        return IntentInterpreter.normalize(value);
    }

    private static int speciesIndex(String mobType) {
        return Math.floorMod((mobType == null ? "unknown" : mobType).hashCode(), SPECIES_COUNT);
    }


    private static float[][] buildClassWeights() {
        List<TrainingExample> examples = CoreTrainingCorpus.examples();
        int[][] counts = new int[HEAD_COUNT][CLASS_COUNT];
        int[] totals = new int[HEAD_COUNT];
        for (TrainingExample example : examples) {
            int[] labels = labels(example);
            for (int head = 0; head < HEAD_COUNT; head++) {
                counts[head][labels[head]]++;
                totals[head]++;
            }
        }
        float[][] weights = new float[HEAD_COUNT][CLASS_COUNT];
        for (int head = 0; head < HEAD_COUNT; head++) {
            int present = 0;
            for (int count : counts[head]) {
                if (count > 0) {
                    present++;
                }
            }
            float average = (float) totals[head] / Math.max(1, present);
            for (int label = 0; label < CLASS_COUNT; label++) {
                weights[head][label] = counts[head][label] == 0 ? 1.0F
                        : Math.min(8.0F, average / counts[head][label]);
            }
        }
        return weights;
    }

    private static int[] labels(TrainingExample example) {
        return new int[]{example.speechAct(), example.action(), example.reaction(), example.memory(), example.voiceEmotion()};
    }

    private static int actionClass(MobAction action) {
        return switch (action) {
            case NONE -> 0;
            case FOLLOW -> 1;
            case APPROACH -> 2;
            case FLEE -> 3;
            case LOOK -> 4;
            case SIT -> 5;
            case JUMP -> 6;
            case STOP -> 7;
            case PROTECT -> 8;
            case PICKUP_ITEM -> 9;
            case DROP_ITEM -> 10;
            case SPAWN_MOB -> 11;
        };
    }

    private record SparseFeatures(int[] indices, float[] values) {
    }

    private record Forward(float[] embedding, float[] preAdapter, float[] hidden,
                           float[][] probabilities, SparseFeatures activeFeatures, int[] best) {
    }

    private record RankedExample(TrainingExample example, float loss) {
    }
}
