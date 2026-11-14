import { describe, expect, it } from "vitest";
import { detectLanguage, segmentText } from "./LanguageRouter";
import { UnicodeTokenizer } from "./UnicodeTokenizer";
import { ProceduralNeuralNetwork } from "./ProceduralNetwork";
import { planScene } from "./ScenePlanner";

describe("multilingual text pipeline", () => {
  it("round-trips Portuguese accents through UTF-8 bytes", () => {
    const tokenizer = new UnicodeTokenizer();
    const source = "ação, coração e animação";
    expect(tokenizer.decode(tokenizer.encode(source, "pt").tokens)).toBe(source);
  });

  it("recognizes the six script families", () => {
    expect(detectLanguage("Olá, tudo bem?")).toBe("pt");
    expect(detectLanguage("hello, how are you?")).toBe("en");
    expect(detectLanguage("hola, ¿cómo estás?")).toBe("es");
    expect(detectLanguage("你好世界")).toBe("zh");
    expect(detectLanguage("नमस्ते दुनिया")).toBe("hi");
    expect(detectLanguage("مرحبا بالعالم")).toBe("ar");
  });

  it("segments Chinese text by characters and Hindi by graphemes", () => {
    expect(segmentText("你好世界", "zh")).toHaveLength(4);
    expect(segmentText("नमस्ते", "hi").join("")).toBe("नमस्ते");
  });
});

describe("procedural neural engine", () => {
  it("creates reproducible parameters and trains its output head", () => {
    const first = new ProceduralNeuralNetwork({ depth: 2, hiddenSize: 32, activeWidth: 8, seed: 77 });
    const second = new ProceduralNeuralNetwork({ depth: 2, hiddenSize: 32, activeWidth: 8, seed: 77 });
    expect(first.bank.weight(1, 2, 3)).toBe(second.bank.weight(1, 2, 3));
    expect(first.trainableParameterCount).toBe(256 * 8 + 256);
    const result = first.trainText("procedural neural tokenizer", 1, 0.03);
    expect(result.steps).toBeGreaterThan(0);
    expect(Number.isFinite(result.loss)).toBe(true);
    expect(first.getStats().status).toBe("adapted");
  });

  it("builds an editable scene plan", () => {
    const plan = planScene("uma cidade futurista");
    expect(plan.objects.length).toBeGreaterThan(1);
    expect(plan.objects.every((object) => object.id && object.position.length === 3)).toBe(true);
    const forest = planScene("make something", "forest");
    const vehicle = planScene("make something", "vehicle");
    expect(forest.category).toBe("forest");
    expect(forest.objects.some((object) => object.kind === "cone")).toBe(true);
    expect(vehicle.objects.some((object) => object.kind === "cylinder")).toBe(true);
  });
});