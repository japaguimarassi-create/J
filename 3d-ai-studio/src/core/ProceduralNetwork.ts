import { TOKEN, UnicodeTokenizer } from "./UnicodeTokenizer";

export interface NetworkConfig {
  seed: number;
  depth: number;
  hiddenSize: number;
  activeWidth: number;
  vocabSize: number;
}

export interface NetworkStats {
  virtualParameterCount: number;
  trainableParameterCount: number;
  depth: number;
  hiddenSize: number;
  activeWidth: number;
  trainingSteps: number;
  lastLoss: number | null;
  seed: number;
  status: "procedural-untrained" | "adapted";
}

const DEFAULT_CONFIG: NetworkConfig = {
  seed: 20261114,
  depth: 48,
  hiddenSize: 768,
  activeWidth: 48,
  vocabSize: 256
};

function hash32(value: number): number {
  let x = value | 0;
  x ^= x >>> 16;
  x = Math.imul(x, 0x7feb352d);
  x ^= x >>> 15;
  x = Math.imul(x, 0x846ca68b);
  x ^= x >>> 16;
  return x >>> 0;
}

function signedUnit(value: number): number {
  return (value / 4294967295) * 2 - 1;
}

export class ProceduralParameterBank {
  constructor(readonly seed: number) {}

  weight(block: number, row: number, column: number, matrix = 0): number {
    const key = this.seed ^
      Math.imul(block + 1, 0x9e3779b1) ^
      Math.imul(row + 1, 0x85ebca6b) ^
      Math.imul(column + 1, 0xc2b2ae35) ^
      Math.imul(matrix + 1, 0x27d4eb2f);
    return signedUnit(hash32(key)) * 0.12;
  }
}

export class ProceduralNeuralNetwork {
  readonly config: NetworkConfig;
  readonly bank: ProceduralParameterBank;
  private readonly tokenizer = new UnicodeTokenizer();
  private readonly outputWeights: Float32Array;
  private readonly outputBias: Float32Array;
  private trainingSteps = 0;
  private lastLoss: number | null = null;

  constructor(config: Partial<NetworkConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    if (this.config.depth < 1 || this.config.hiddenSize < 16 || this.config.activeWidth < 8 ||
        this.config.activeWidth > this.config.hiddenSize || this.config.vocabSize !== 256) {
      throw new Error("Invalid network dimensions.");
    }
    this.bank = new ProceduralParameterBank(this.config.seed);
    this.outputWeights = new Float32Array(this.config.vocabSize * this.config.activeWidth);
    this.outputBias = new Float32Array(this.config.vocabSize);
    for (let token = 0; token < this.config.vocabSize; token++) {
      for (let column = 0; column < this.config.activeWidth; column++) {
        this.outputWeights[token * this.config.activeWidth + column] =
          this.bank.weight(this.config.depth, token, column, 9);
      }
    }
  }

  get virtualParameterCount(): number {
    const width = this.config.hiddenSize;
    const expansion = width * 4;
    const perBlock = 4 * width * width + 2 * width * expansion + 4 * width;
    return width * (this.config.vocabSize + 16) + perBlock * this.config.depth;
  }

  get trainableParameterCount(): number {
    return this.outputWeights.length + this.outputBias.length;
  }

  private activate(token: number): Float32Array {
    const width = this.config.activeWidth;
    let state = new Float32Array(width);
    const tokenIndex = Math.max(0, token - TOKEN.BYTE_BASE);
    for (let i = 0; i < width; i++) state[i] = this.bank.weight(-1, tokenIndex, i, 0);
    for (let block = 0; block < this.config.depth; block++) {
      const next = new Float32Array(width);
      for (let row = 0; row < width; row++) {
        let attention = 0;
        let feedForward = 0;
        for (let column = 0; column < width; column++) {
          attention += state[column] * this.bank.weight(block, row, column, 0);
          feedForward += state[column] * this.bank.weight(block, row, column, 1);
        }
        const a = Math.tanh(attention / Math.sqrt(width));
        const f = Math.tanh(feedForward / Math.sqrt(width) + this.bank.weight(block, row, 0, 2));
        next[row] = Math.tanh(state[row] + 0.28 * a + 0.16 * f);
      }
      state = next;
    }
    return state;
  }

  private logits(hidden: Float32Array): Float32Array {
    const result = new Float32Array(this.config.vocabSize);
    for (let token = 0; token < result.length; token++) {
      let score = this.outputBias[token];
      const offset = token * this.config.activeWidth;
      for (let column = 0; column < hidden.length; column++) {
        score += this.outputWeights[offset + column] * hidden[column];
      }
      result[token] = score;
    }
    return result;
  }

  trainText(text: string, epochs = 1, learningRate = 0.08): { steps: number; loss: number; samples: number } {
    const raw = this.tokenizer.encode(text).tokens.filter((token) => token >= TOKEN.BYTE_BASE && token <= TOKEN.BYTE_LIMIT);
    if (raw.length < 2) throw new Error("Add at least two UTF-8 bytes to create a training pair.");
    const stride = Math.max(1, Math.ceil((raw.length - 1) / 48));
    const pairs: Array<[number, number]> = [];
    for (let i = 0; i < raw.length - 1; i += stride) pairs.push([raw[i], raw[i + 1]]);
    let lossTotal = 0;
    let steps = 0;
    const rate = Math.min(0.2, Math.max(0.001, learningRate));
    for (let epoch = 0; epoch < Math.max(1, Math.min(8, epochs)); epoch++) {
      for (const [source, target] of pairs) {
        const hidden = this.activate(source);
        const scores = this.logits(hidden);
        let maximum = -Infinity;
        for (const score of scores) maximum = Math.max(maximum, score);
        let sum = 0;
        const probabilities = new Float32Array(scores.length);
        for (let i = 0; i < scores.length; i++) {
          probabilities[i] = Math.exp(scores[i] - maximum);
          sum += probabilities[i];
        }
        for (let i = 0; i < probabilities.length; i++) probabilities[i] /= sum;
        const targetIndex = target - TOKEN.BYTE_BASE;
        lossTotal += -Math.log(Math.max(probabilities[targetIndex], 1e-8));
        for (let token = 0; token < probabilities.length; token++) {
          const gradient = probabilities[token] - (token === targetIndex ? 1 : 0);
          const offset = token * this.config.activeWidth;
          for (let column = 0; column < hidden.length; column++) {
            this.outputWeights[offset + column] -= rate * gradient * hidden[column];
          }
          this.outputBias[token] -= rate * gradient;
        }
        steps++;
      }
    }
    this.trainingSteps += steps;
    this.lastLoss = lossTotal / Math.max(1, steps);
    return { steps, loss: this.lastLoss, samples: pairs.length };
  }

  predictNextByte(input: string): { byte: number; character: string; confidence: number } {
    const encoded = this.tokenizer.encode(input).tokens.filter((token) => token >= TOKEN.BYTE_BASE && token <= TOKEN.BYTE_LIMIT);
    if (encoded.length === 0) throw new Error("Enter text before requesting a prediction.");
    const hidden = this.activate(encoded[encoded.length - 1]);
    const scores = this.logits(hidden);
    let maximum = -Infinity;
    let selected = 0;
    for (let index = 0; index < scores.length; index++) {
      if (scores[index] > maximum) {
        maximum = scores[index];
        selected = index;
      }
    }
    const normalizer = scores.reduce((total, score) => total + Math.exp(score - maximum), 0);
    return {
      byte: selected,
      character: new TextDecoder().decode(new Uint8Array([selected])),
      confidence: 1 / normalizer
    };
  }

  getStats(): NetworkStats {
    return {
      virtualParameterCount: this.virtualParameterCount,
      trainableParameterCount: this.trainableParameterCount,
      depth: this.config.depth,
      hiddenSize: this.config.hiddenSize,
      activeWidth: this.config.activeWidth,
      trainingSteps: this.trainingSteps,
      lastLoss: this.lastLoss,
      seed: this.config.seed,
      status: this.trainingSteps > 0 ? "adapted" : "procedural-untrained"
    };
  }

  reset(seed: number): ProceduralNeuralNetwork {
    return new ProceduralNeuralNetwork({ ...this.config, seed });
  }
}

export function formatParameterCount(value: number): string {
  if (value >= 1_000_000_000) return (value / 1_000_000_000).toFixed(2) + "B";
  if (value >= 1_000_000) return (value / 1_000_000).toFixed(1) + "M";
  if (value >= 1_000) return (value / 1_000).toFixed(1) + "K";
  return String(value);
}