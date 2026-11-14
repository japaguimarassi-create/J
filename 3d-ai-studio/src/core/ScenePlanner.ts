export type PrimitiveKind = "box" | "sphere" | "capsule" | "torus";

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
  objects: PlannedObject[];
  animation: "idle" | "orbit" | "action";
  explanation: string;
}

const palette = ["#6f8cff", "#3dd6c6", "#a98cff", "#ffb86b", "#f079a8"];

function containsAny(text: string, words: string[]) {
  return words.some((word) => text.includes(word));
}

export function planScene(prompt: string): ScenePlan {
  const text = prompt.toLocaleLowerCase();
  const objects: PlannedObject[] = [];
  const add = (kind: PrimitiveKind, name: string, index: number, position: [number, number, number]) => {
    objects.push({
      id: "generated-" + index + "-" + Math.random().toString(36).slice(2, 8),
      name,
      kind,
      color: palette[index % palette.length],
      position,
      scale: kind === "capsule" ? [0.7, 1.35, 0.7] : [1, 1, 1]
    });
  };

  if (containsAny(text, ["floresta", "forest", "árvore", "tree", "bosque"])) {
    add("box", "Tronco", 0, [0, 0, 0]);
    add("sphere", "Copa", 1, [0, 1.4, 0]);
    add("sphere", "Copa auxiliar", 2, [1.2, 1.1, -0.5]);
  } else if (containsAny(text, ["cidade", "city", "prédio", "predio", "building", "urbano"])) {
    add("box", "Edifício central", 0, [0, 1.2, 0]);
    add("box", "Edifício lateral", 1, [-1.5, 0.6, -0.7]);
    add("box", "Edifício alto", 2, [1.5, 1.7, -0.8]);
  } else if (containsAny(text, ["luta", "fight", "batalha", "battle", "personagem", "character"])) {
    add("capsule", "Personagem A", 0, [-1.2, 0, 0]);
    add("capsule", "Personagem B", 1, [1.2, 0, 0]);
    add("torus", "Anel de energia", 2, [0, 0.4, 0]);
  } else {
    add("box", "Objeto principal", 0, [0, 0, 0]);
    add("sphere", "Objeto secundário", 1, [1.7, 0.2, 0]);
    add("torus", "Elemento de destaque", 2, [-1.5, 0.1, 0]);
  }

  return {
    title: prompt.trim().slice(0, 48) || "Nova cena",
    objects,
    animation: containsAny(text, ["luta", "fight", "batalha", "battle", "ação", "acao"]) ? "action" : "orbit",
    explanation: "Cena procedural criada a partir de palavras-chave. Os objetos são geometria 3D editável; nenhum modelo externo foi baixado."
  };
}