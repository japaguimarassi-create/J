export const FORGE_VERSION = "0.1";

function vector(raw, line, lengths = [3]) {
  const values = raw.split(",").map((part) => Number(part.trim()));
  if (!lengths.includes(values.length) || values.some((value) => !Number.isFinite(value))) {
    throw new Error("Linha " + line + ": vetor inválido; use números separados por vírgula.");
  }
  if (values.length === 2) values.push(1);
  return values;
}

export function parseForge(text) {
  const scene = { project: "Projeto", name: "Cena", mode: "2d", fps: 30, duration: 3, objects: [], animations: [] };
  const names = new Set();
  let hasScene = false;
  String(text).split(/\r?\n/).forEach((raw, index) => {
    const number = index + 1;
    const line = raw.trim();
    if (!line || line.startsWith("//")) return;
    let match;
    if ((match = line.match(/^project\s+"([^"]+)"$/))) {
      scene.project = match[1];
      return;
    }
    if ((match = line.match(/^scene\s+"([^"]+)"\s+mode\s+(2d|3d)\s+fps\s+(\d+)\s+duration\s+([0-9]+(?:\.[0-9]+)?)$/i))) {
      if (hasScene) throw new Error("Linha " + number + ": esta versão aceita apenas uma cena por projeto.");
      hasScene = true;
      scene.name = match[1];
      scene.mode = match[2].toLowerCase();
      scene.fps = Number(match[3]);
      scene.duration = Number(match[4]);
      if (scene.fps < 1 || scene.fps > 240) throw new Error("Linha " + number + ": FPS deve ficar entre 1 e 240.");
      if (scene.duration <= 0 || scene.duration > 600) throw new Error("Linha " + number + ": duração deve ficar entre 0 e 600 segundos.");
      return;
    }
    if ((match = line.match(/^object\s+"([^"]+)"\s+(circle|box|sphere|cone|torus)\s+color\s+"(#[0-9a-fA-F]{6})"\s+at\s+\(([^)]+)\)\s+(size|scale)\s+\(([^)]+)\)$/i))) {
      const [, name, type, color, position, dimensionKind, dimensions] = match;
      if (names.has(name)) throw new Error("Linha " + number + ": nome de objeto duplicado: " + name + ".");
      names.add(name);
      scene.objects.push({ name, type: type.toLowerCase(), color, position: vector(position, number), dimensions: vector(dimensions, number, [2, 3]), dimensionKind: dimensionKind.toLowerCase() });
      return;
    }
    if ((match = line.match(/^animate\s+"([^"]+)"\s+(move|rotate|scale)\s+from\s+\(([^)]+)\)\s+to\s+\(([^)]+)\)\s+from\s+([0-9]+(?:\.[0-9]+)?)s\s+to\s+([0-9]+(?:\.[0-9]+)?)s\s+ease\s+(linear|smooth)$/i))) {
      const [, target, property, from, to, startRaw, endRaw, easing] = match;
      const start = Number(startRaw), end = Number(endRaw);
      if (!Number.isFinite(start) || !Number.isFinite(end) || start < 0 || end <= start) throw new Error("Linha " + number + ": o tempo final deve ser maior que o inicial.");
      scene.animations.push({ target, property: property.toLowerCase(), from: vector(from, number), to: vector(to, number), start, end, easing: easing.toLowerCase(), lineNumber: number });
      return;
    }
    throw new Error("Linha " + number + ": sintaxe FORGE desconhecida. Confira a referência rápida.");
  });
  if (!hasScene) throw new Error('Adicione: scene "Nome" mode 2d fps 30 duration 3.');
  if (!scene.objects.length) throw new Error("Adicione pelo menos um objeto.");
  for (const animation of scene.animations) {
    if (!names.has(animation.target)) throw new Error("Linha " + animation.lineNumber + ': objeto "' + animation.target + '" não existe.');
    if (animation.end > scene.duration) throw new Error("Linha " + animation.lineNumber + ": a animação termina depois da duração da cena.");
  }
  return scene;
}

export function inspectForge(text) {
  try { return { ok: true, scene: parseForge(text), error: null }; }
  catch (error) { return { ok: false, scene: null, error: error.message || "FORGE inválido" }; }
}
