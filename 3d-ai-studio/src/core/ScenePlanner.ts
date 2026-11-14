import type { SceneCategory } from "./SceneBrain";

export type PrimitiveKind = "box" | "sphere" | "capsule" | "torus" | "cylinder" | "cone";

export interface PlannedObject {
  id: string;
  name: string;
  kind: PrimitiveKind;
  color: string;
  position: [number, number, number];
  scale: [number, number, number];
}

export interface ScenePlan {
  title: string;
  category: SceneCategory;
  objects: PlannedObject[];
  animation: "idle" | "orbit" | "action" | "walk" | "run" | "jump" | "combo";
  explanation: string;
}

const palette = ["#6f8cff", "#3dd6c6", "#a98cff", "#ffb86b", "#f079a8", "#b2d47a"];

function containsAny(text: string, words: string[]) {
  return words.some((word) => text.includes(word));
}

function inferFallback(text: string): SceneCategory {
  if (containsAny(text, ["floresta", "forest", "árvore", "arvore", "tree", "bosque", "selva"])) return "forest";
  if (containsAny(text, ["cidade", "city", "prédio", "predio", "building", "urbano"])) return "city";
  if (containsAny(text, ["carro", "car", "veículo", "veiculo", "vehicle", "nave", "ship"])) return "vehicle";
  if (containsAny(text, ["sala", "quarto", "cozinha", "room", "bedroom", "kitchen", "habitación"])) return "interior";
  if (containsAny(text, ["luta", "fight", "batalha", "battle", "personagem", "character", "humano"])) return "character";
  return "abstract";
}

export function planScene(prompt: string, learnedCategory?: SceneCategory): ScenePlan {
  const text = prompt.toLocaleLowerCase();
  const category = learnedCategory ?? inferFallback(text);
  const objects: PlannedObject[] = [];
  let nextId = 0;
  const add = (kind: PrimitiveKind, name: string, position: [number, number, number], scale: [number, number, number] = [1, 1, 1]) => {
    const index = nextId++;
    objects.push({
      id: "generated-" + index + "-" + Math.floor(Math.random() * 0xffffff).toString(16),
      name,
      kind,
      color: palette[index % palette.length],
      position,
      scale
    });
  };

  if (category === "forest") {
    for (let i = 0; i < 7; i++) {
      const x = (i % 4 - 1.5) * 1.35;
      const z = Math.floor(i / 4) * -1.8;
      add("cylinder", "Tronco " + (i + 1), [x, 0.35, z], [0.22, 0.85, 0.22]);
      add("cone", "Copa " + (i + 1), [x, 1.45, z], [0.85, 1.25, 0.85]);
    }
    add("box", "Solo da floresta", [0, -0.8, -0.5], [6, 0.12, 4]);
  } else if (category === "city") {
    for (let i = 0; i < 8; i++) {
      const x = (i % 4 - 1.5) * 1.65;
      const z = Math.floor(i / 4) * -1.9;
      const height = 0.8 + (i % 3) * 0.55;
      add("box", "Edifício " + (i + 1), [x, height / 2, z], [1.05, height, 1.1]);
    }
    add("box", "Praça", [0, -0.72, -0.8], [7, 0.12, 4]);
  } else if (category === "character") {
    for (let person = 0; person < 2; person++) {
      const x = person === 0 ? -1.35 : 1.35;
      const tint = person === 0 ? "#6f8cff" : "#f079a8";
      add("capsule", "Corpo " + (person + 1), [x, 0.1, 0], [0.55, 1.15, 0.55]);
      add("sphere", "Cabeça " + (person + 1), [x, 1.05, 0], [0.42, 0.42, 0.42]);
      add("cylinder", "Braço esquerdo " + (person + 1), [x - 0.55, 0.2, 0], [0.16, 0.62, 0.16]);
      add("cylinder", "Braço direito " + (person + 1), [x + 0.55, 0.2, 0], [0.16, 0.62, 0.16]);
      objects[objects.length - 4].color = tint;
    }
    add("torus", "Arena", [0, -0.7, 0], [2.8, 2.8, 2.8]);
  } else if (category === "vehicle") {
    add("box", "Chassi", [0, 0.1, 0], [2.6, 0.42, 1.2]);
    add("box", "Cabine", [0.15, 0.65, -0.05], [1.25, 0.72, 1.05]);
    for (const x of [-0.9, 0.9]) for (const z of [-0.62, 0.62]) add("cylinder", "Roda", [x, -0.32, z], [0.32, 0.22, 0.32]);
  } else if (category === "interior") {
    add("box", "Piso", [0, -0.72, 0], [5, 0.12, 4]);
    add("box", "Mesa", [0, 0, 0], [1.8, 0.16, 1.1]);
    for (const x of [-0.7, 0.7]) for (const z of [-0.35, 0.35]) add("cylinder", "Pé da mesa", [x, -0.35, z], [0.08, 0.38, 0.08]);
    for (const x of [-1.6, 1.6]) add("box", "Cadeira", [x, -0.15, 0], [0.65, 0.75, 0.65]);
    add("box", "Janela", [0, 1.15, -1.9], [1.2, 0.85, 0.08]);
  } else {
    add("box", "Forma central", [0, 0, 0], [1.2, 1.2, 1.2]);
    add("sphere", "Esfera flutuante", [1.65, 0.5, 0], [0.7, 0.7, 0.7]);
    add("torus", "Anel orbital", [-1.45, 0.25, 0], [1.15, 1.15, 1.15]);
    add("cone", "Pico geométrico", [0, 1.7, -0.8], [0.65, 0.9, 0.65]);
    add("cylinder", "Coluna", [0, -1.1, 0], [0.5, 0.7, 0.5]);
  }

  const animation: ScenePlan["animation"] =
    containsAny(text, ["correndo", "correr", "run", "running"]) ? "run" :
    containsAny(text, ["pular", "salto", "jump", "leap"]) ? "jump" :
    category === "character" ? "combo" : "orbit";

  return {
    title: prompt.trim().slice(0, 48) || "Nova cena",
    category,
    objects,
    animation,
    explanation: "O modelo neural classificou a intenção como " + category + ". A cena foi construída com geometrias 3D editáveis."
  };
}
