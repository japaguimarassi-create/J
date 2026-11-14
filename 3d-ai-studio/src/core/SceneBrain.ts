export type SceneCategory = "forest" | "city" | "character" | "vehicle" | "interior" | "abstract";

interface SceneCheckpoint {
  format: "3d-ai-studio-scene-brain-v1";
  architecture: { inputSize: number; hiddenSize: number; outputSize: number; labels: SceneCategory[] };
  vocabulary: string[];
  weights: {
    inputHidden: number[][];
    hiddenBias: number[];
    hiddenOutput: number[][];
    inputOutput: number[][];
    outputBias: number[];
  };
  training: { validationAccuracy: number; samples: number; epochs: number };
}

export interface ScenePrediction {
  category: SceneCategory;
  confidence: number;
  probabilities: Record<SceneCategory, number>;
}

function tokenize(text: string): string[] {
  const words = text.toLocaleLowerCase().normalize("NFC").match(/[\p{L}\p{N}]+/gu) ?? [];
  const tokens: string[] = [];
  for (const word of words) {
    if (/[\u3400-\u9fff]/u.test(word)) {
      const chars = Array.from(word);
      tokens.push(...chars);
      for (let i = 0; i < chars.length - 1; i++) tokens.push(chars[i] + chars[i + 1]);
    } else tokens.push(word);
  }
  return tokens;
}

export class SceneBrain {
  private readonly index: Map<string, number>;

  constructor(private readonly checkpoint: SceneCheckpoint) {
    if (checkpoint.format !== "3d-ai-studio-scene-brain-v1") throw new Error("Unsupported scene model format.");
    this.index = new Map(checkpoint.vocabulary.map((token, index) => [token, index]));
  }

  static async load(): Promise<SceneBrain> {
    const response = await fetch("models/scene-brain.json", { cache: "no-cache" });
    if (!response.ok) throw new Error("The trained scene model is not available in this build.");
    return new SceneBrain(await response.json() as SceneCheckpoint);
  }

  predict(text: string): ScenePrediction {
    const input = new Float64Array(this.checkpoint.architecture.inputSize);
    for (const token of tokenize(text)) {
      const index = this.index.get(token);
      if (index !== undefined) input[index] += 1;
    }
    const norm = Math.sqrt(input.reduce((sum, value) => sum + value * value, 0)) || 1;
    for (let i = 0; i < input.length; i++) input[i] /= norm;

    const { inputHidden, hiddenBias, hiddenOutput, inputOutput, outputBias } = this.checkpoint.weights;
    const hidden = new Float64Array(this.checkpoint.architecture.hiddenSize);
    for (let row = 0; row < hidden.length; row++) {
      let value = hiddenBias[row];
      for (let col = 0; col < input.length; col++) value += inputHidden[row][col] * input[col];
      hidden[row] = Math.max(0, value);
    }
    const logits = outputBias.map((bias, row) => {
      let value = bias;
      for (let col = 0; col < hidden.length; col++) value += hiddenOutput[row][col] * hidden[col];
      for (let col = 0; col < input.length; col++) value += inputOutput[row][col] * input[col];
      return value;
    });
    const max = Math.max(...logits);
    const exps = logits.map(value => Math.exp(value - max));
    const total = exps.reduce((sum, value) => sum + value, 0);
    const values = exps.map(value => value / total);
    const labels = this.checkpoint.architecture.labels;
    const probabilities = Object.fromEntries(labels.map((label, index) => [label, values[index]])) as Record<SceneCategory, number>;
    const selected = values.indexOf(Math.max(...values));
    return { category: labels[selected], confidence: values[selected], probabilities };
  }

  get metrics() {
    return {
      samples: this.checkpoint.training.samples,
      epochs: this.checkpoint.training.epochs,
      validationAccuracy: this.checkpoint.training.validationAccuracy,
      categories: this.checkpoint.architecture.labels.length,
      vocabulary: this.checkpoint.vocabulary.length
    };
  }
}
