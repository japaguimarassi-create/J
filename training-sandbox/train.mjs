import fs from "node:fs";
import path from "node:path";

const root = path.resolve("training-sandbox");
const generated = path.join(root, "generated");
const modelDir = path.join(generated, "models");
const textureDir = path.join(generated, "textures");
const animationDir = path.join(generated, "animations");
const dataDir = path.join(generated, "dataset");
for (const dir of [modelDir, textureDir, animationDir, dataDir]) fs.mkdirSync(dir, { recursive: true });

let seed = 20261114;
function random() {
  seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
  return seed / 4294967296;
}
function write(file, value) {
  fs.writeFileSync(file, typeof value === "string" ? value : JSON.stringify(value, null, 2));
}
function tokenize(text) {
  const normalized = text.toLocaleLowerCase().normalize("NFC");
  const words = normalized.match(/[\p{L}\p{N}]+/gu) ?? [];
  const tokens = [];
  for (const word of words) {
    if (/[\u3400-\u9fff]/u.test(word)) {
      const chars = Array.from(word);
      tokens.push(...chars);
      for (let i = 0; i < chars.length - 1; i++) tokens.push(chars[i] + chars[i + 1]);
    } else tokens.push(word);
  }
  return tokens;
}

const classes = {
  forest: {
    pt: ["crie uma floresta densa com árvores e folhas", "faça um bosque com troncos e vegetação", "gere uma selva verde com árvores altas"],
    en: ["create a dense forest with trees and leaves", "make a woodland with trunks and vegetation", "generate a green jungle with tall trees"],
    es: ["crea un bosque denso con árboles y hojas", "haz una selva verde con troncos y vegetación", "genera árboles altos en un bosque"],
    zh: ["创建一片有树木和叶子的森林", "生成绿色丛林和高大的树", "制作一个茂密的树林"],
    hi: ["पेड़ों और पत्तों वाला घना जंगल बनाओ", "हरे जंगल में ऊँचे पेड़ बनाओ", "वन और वनस्पति का दृश्य बनाओ"],
    ar: ["أنشئ غابة كثيفة بها أشجار وأوراق", "اصنع غابة خضراء بأشجار طويلة", "أنشئ مشهد غابة ونباتات"]
  },
  city: {
    pt: ["crie uma cidade futurista com prédios altos", "gere ruas urbanas e edifícios", "faça uma metrópole com arranha céus"],
    en: ["create a futuristic city with tall buildings", "generate urban streets and buildings", "make a metropolis with skyscrapers"],
    es: ["crea una ciudad futurista con edificios altos", "genera calles urbanas y edificios", "haz una metrópolis con rascacielos"],
    zh: ["创建有高楼大厦的未来城市", "生成城市街道和建筑", "制作一个现代都市"],
    hi: ["ऊँची इमारतों वाला भविष्य का शहर बनाओ", "शहरी सड़कें और भवन बनाओ", "एक आधुनिक महानगर बनाओ"],
    ar: ["أنشئ مدينة مستقبلية بمبانٍ عالية", "أنشئ شوارع حضرية ومباني", "اصنع مدينة حديثة وناطحات سحاب"]
  },
  character: {
    pt: ["crie um personagem humano com cabeça braços e pernas", "faça dois lutadores em uma arena", "gere uma pessoa estilizada para animação"],
    en: ["create a human character with head arms and legs", "make two fighters in an arena", "generate a stylized person for animation"],
    es: ["crea un personaje humano con cabeza brazos y piernas", "haz dos luchadores en una arena", "genera una persona estilizada para animación"],
    zh: ["创建一个有头部手臂和腿的人物", "制作竞技场中的两个角色", "生成可动画的卡通人物"],
    hi: ["सिर हाथ और पैरों वाला मानव पात्र बनाओ", "मैदान में दो लड़ाके बनाओ", "एनीमेशन के लिए पात्र बनाओ"],
    ar: ["أنشئ شخصية بشرية لها رأس وذراعان وساقان", "اصنع مقاتلين في ساحة", "أنشئ شخصية كرتونية للتحريك"]
  },
  vehicle: {
    pt: ["crie um carro esportivo com quatro rodas", "gere um veículo futurista", "faça uma nave com asas e motores"],
    en: ["create a sports car with four wheels", "generate a futuristic vehicle", "make a spaceship with wings and engines"],
    es: ["crea un coche deportivo con cuatro ruedas", "genera un vehículo futurista", "haz una nave con alas y motores"],
    zh: ["创建一辆有四个轮子的跑车", "生成未来车辆", "制作有机翼和引擎的飞船"],
    hi: ["चार पहियों वाली स्पोर्ट्स कार बनाओ", "भविष्य का वाहन बनाओ", "पंख और इंजन वाला अंतरिक्ष यान बनाओ"],
    ar: ["أنشئ سيارة رياضية بأربع عجلات", "أنشئ مركبة مستقبلية", "اصنع سفينة فضائية بأجنحة ومحركات"]
  },
  interior: {
    pt: ["crie uma sala com mesa cadeiras e janelas", "gere um quarto moderno", "faça uma cozinha com armários"],
    en: ["create a room with a table chairs and windows", "generate a modern bedroom", "make a kitchen with cabinets"],
    es: ["crea una habitación con mesa sillas y ventanas", "genera un dormitorio moderno", "haz una cocina con armarios"],
    zh: ["创建一个有桌子椅子和窗户的房间", "生成现代卧室", "制作带橱柜的厨房"],
    hi: ["मेज कुर्सियों और खिड़कियों वाला कमरा बनाओ", "आधुनिक शयनकक्ष बनाओ", "अलमारियों वाला रसोईघर बनाओ"],
    ar: ["أنشئ غرفة بها طاولة وكراسي ونوافذ", "أنشئ غرفة نوم حديثة", "اصنع مطبخاً بخزائن"]
  },
  abstract: {
    pt: ["crie uma escultura abstrata com formas geométricas", "gere uma composição artística de cubos e anéis", "faça uma instalação de arte flutuante"],
    en: ["create an abstract sculpture with geometric shapes", "generate an artistic composition of cubes and rings", "make a floating art installation"],
    es: ["crea una escultura abstracta con formas geométricas", "genera una composición artística de cubos y anillos", "haz una instalación de arte flotante"],
    zh: ["创建由几何形状组成的抽象雕塑", "生成立方体和圆环艺术组合", "制作漂浮艺术装置"],
    hi: ["ज्यामितीय आकृतियों वाली अमूर्त मूर्ति बनाओ", "घनों और छल्लों की कलात्मक रचना बनाओ", "तैरती हुई कला स्थापना बनाओ"],
    ar: ["أنشئ منحوتة تجريدية بأشكال هندسية", "أنشئ تكويناً فنياً من المكعبات والحلقات", "اصنع عملاً فنياً عائماً"]
  }
};

const examples = [];
for (const [label, languages] of Object.entries(classes)) {
  for (const [language, prompts] of Object.entries(languages)) {
    for (const prompt of prompts) {
      examples.push({ text: prompt, label, language, tokens: tokenize(prompt) });
    }
  }
}
for (let i = examples.length - 1; i > 0; i--) {
  const j = Math.floor(random() * (i + 1));
  [examples[i], examples[j]] = [examples[j], examples[i]];
}
const vocabulary = [...new Set(examples.flatMap(item => item.tokens))].sort();
const wordIndex = new Map(vocabulary.map((word, index) => [word, index]));
const labels = Object.keys(classes);
const labelIndex = new Map(labels.map((label, index) => [label, index]));

function vectorize(text) {
  const vector = new Float64Array(vocabulary.length);
  for (const token of tokenize(text)) {
    const index = wordIndex.get(token);
    if (index !== undefined) vector[index] += 1;
  }
  const norm = Math.sqrt(vector.reduce((sum, value) => sum + value * value, 0)) || 1;
  for (let i = 0; i < vector.length; i++) vector[i] /= norm;
  return vector;
}
function matrix(rows, cols, scale) {
  return Array.from({ length: rows }, () => Array.from({ length: cols }, () => (random() * 2 - 1) * scale));
}
function softmax(values) {
  const max = Math.max(...values);
  const exps = values.map(value => Math.exp(value - max));
  const total = exps.reduce((a, b) => a + b, 0);
  return exps.map(value => value / total);
}

const inputSize = vocabulary.length;
const hiddenSize = 48;
const outputSize = labels.length;
const w1 = matrix(hiddenSize, inputSize, Math.sqrt(2 / inputSize));
const b1 = Array(hiddenSize).fill(0);
const w2 = matrix(outputSize, hiddenSize, Math.sqrt(2 / hiddenSize));
const b2 = Array(outputSize).fill(0);
const learningRate = 0.035;
const validation = examples.filter((_, index) => index % 4 === 0);
const trainingExamples = examples.filter((_, index) => index % 4 !== 0);
let finalLoss = 0;
const epochs = Number(process.env.TRAIN_EPOCHS || 180);
for (let epoch = 0; epoch < epochs; epoch++) {
  let epochLoss = 0;
  for (const sample of trainingExamples) {
    const x = vectorize(sample.text);
    const h = new Float64Array(hiddenSize);
    for (let row = 0; row < hiddenSize; row++) {
      let value = b1[row];
      for (let col = 0; col < inputSize; col++) value += w1[row][col] * x[col];
      h[row] = Math.max(0, value);
    }
    const logits = b2.map((bias, row) => {
      let value = bias;
      for (let col = 0; col < hiddenSize; col++) value += w2[row][col] * h[col];
      return value;
    });
    const probs = softmax(logits);
    const target = labelIndex.get(sample.label);
    epochLoss -= Math.log(Math.max(probs[target], 1e-12));
    const gradOut = probs.slice();
    gradOut[target] -= 1;
    const gradHidden = new Float64Array(hiddenSize);
    for (let row = 0; row < outputSize; row++) {
      for (let col = 0; col < hiddenSize; col++) {
        gradHidden[col] += gradOut[row] * w2[row][col];
        w2[row][col] -= learningRate * gradOut[row] * h[col];
      }
      b2[row] -= learningRate * gradOut[row];
    }
    for (let row = 0; row < hiddenSize; row++) {
      if (h[row] <= 0) continue;
      for (let col = 0; col < inputSize; col++) w1[row][col] -= learningRate * gradHidden[row] * x[col];
      b1[row] -= learningRate * gradHidden[row];
    }
  }
  finalLoss = epochLoss / trainingExamples.length;
}
function predict(text) {
  const x = vectorize(text);
  const h = new Float64Array(hiddenSize);
  for (let row = 0; row < hiddenSize; row++) {
    let value = b1[row];
    for (let col = 0; col < inputSize; col++) value += w1[row][col] * x[col];
    h[row] = Math.max(0, value);
  }
  const logits = b2.map((bias, row) => {
    let value = bias;
    for (let col = 0; col < hiddenSize; col++) value += w2[row][col] * h[col];
    return value;
  });
  const probs = softmax(logits);
  const best = probs.indexOf(Math.max(...probs));
  return { label: labels[best], confidence: probs[best], probabilities: Object.fromEntries(labels.map((label, index) => [label, probs[index]])) };
}
const correct = trainingExamples.filter(sample => predict(sample.text).label === sample.label).length;
const accuracy = correct / trainingExamples.length;
const validationAccuracy = validation.filter(sample => predict(sample.text).label === sample.label).length / validation.length;
const checkpoint = {
  format: "3d-ai-studio-scene-brain-v1",
  trainedFromScratch: true,
  architecture: { type: "bag-of-subword-features-mlp", inputSize, hiddenSize, outputSize, labels },
  vocabulary,
  weights: { inputHidden: w1, hiddenBias: b1, hiddenOutput: w2, outputBias: b2 },
  training: { epochs, samples: examples.length, finalLoss, trainingAccuracy: accuracy, validationAccuracy, seed: 20261114 }
};
write(path.join(generated, "scene-brain.json"), checkpoint);
write(path.join(dataDir, "scene-prompts.json"), examples);

const modelSpecs = [
  { name: "cube", title: "Cube", vertices: [[-1,-1,-1],[1,-1,-1],[1,1,-1],[-1,1,-1],[-1,-1,1],[1,-1,1],[1,1,1],[-1,1,1]], faces: [[1,2,3,4],[5,8,7,6],[1,5,6,2],[2,6,7,3],[3,7,8,4],[5,1,4,8]] },
  { name: "pyramid", title: "Pyramid", vertices: [[-1,0,-1],[1,0,-1],[1,0,1],[-1,0,1],[0,1.8,0]], faces: [[1,4,3,2],[1,2,5],[2,3,5],[3,4,5],[4,1,5]] },
  { name: "humanoid", title: "Humanoid blockout", vertices: [[0,2,0],[-.35,1.5,0],[.35,1.5,0],[-.25,.6,0],[.25,.6,0],[-.7,1.4,0],[-1,0.8,0],[.7,1.4,0],[1,.8,0],[-.2,.1,0],[.2,.1,0]], faces: [[1,2,3],[2,4,5],[2,5,3],[2,6,7],[3,8,9],[4,10,5],[5,11,10]] },
  { name: "tree", title: "Tree low-poly", vertices: [[-.2,0,-.2],[.2,0,-.2],[.2,1,-.2],[-.2,1,-.2],[-.2,0,.2],[.2,0,.2],[.2,1,.2],[-.2,1,.2],[0,2.5,0]], faces: [[1,2,3,4],[5,8,7,6],[1,5,6,2],[4,3,7,8],[4,8,5,1],[2,6,7,3],[4,8,9],[3,7,9],[1,5,9],[2,6,9]] },
  { name: "house", title: "House", vertices: [[-1,0,-1],[1,0,-1],[1,1.2,-1],[-1,1.2,-1],[-1,0,1],[1,0,1],[1,1.2,1],[-1,1.2,1],[0,2,-1],[0,2,1]], faces: [[1,2,3,4],[5,8,7,6],[1,5,6,2],[4,3,7,8],[4,8,10,9],[3,7,10,9],[1,4,9],[2,3,9]] },
  { name: "car", title: "Car blockout", vertices: [[-1,-.3,-2],[1,-.3,-2],[1,.3,-2],[-1,.3,-2],[-.7,-.3,1.5],[.7,-.3,1.5],[.7,.3,1.5],[-.7,.3,1.5],[-.5,.35,-.8],[.5,.35,-.8],[.4,.85,.7],[-.4,.85,.7]], faces: [[1,2,3,4],[5,8,7,6],[1,5,6,2],[4,3,7,8],[9,10,11,12]] },
  { name: "crystal", title: "Crystal", vertices: [[0,1.8,0],[-.8,0,-.5],[.8,0,-.5],[.8,0,.5],[-.8,0,.5],[0,-1,0]], faces: [[1,2,3],[1,3,4],[1,4,5],[1,5,2],[6,3,2],[6,4,3],[6,5,4],[6,2,5]] },
  { name: "ring", title: "Ring", vertices: Array.from({length:32},(_,i)=>{const a=Math.floor(i/2)*Math.PI/8;const r=i%2?0.82:1.18;return [Math.cos(a)*r,Math.sin(a)*r,0];}), faces: Array.from({length:16},(_,i)=>[i*2+1,i*2+2,((i*2+3)%32)+1,((i*2+2)%32)+1]) }
];
const modelManifest = [];
for (const spec of modelSpecs) {
  const lines = ["# " + spec.title, "o " + spec.name, "mtllib studio.mtl", "usemtl base"];
  for (const vertex of spec.vertices) lines.push("v " + vertex.join(" "));
  for (const vertex of spec.vertices) {
    const length = Math.hypot(vertex[0], vertex[1], vertex[2]) || 1;
    lines.push("vt " + ((vertex[0] / length + 1) / 2).toFixed(5) + " " + ((vertex[1] / length + 1) / 2).toFixed(5));
  }
  for (const face of spec.faces) {
    if (face.length < 3) {
      lines.push("l " + face.join(" "));
      continue;
    }
    const a = spec.vertices[face[0] - 1], b = spec.vertices[face[1] - 1], c = spec.vertices[face[2] - 1];
    const u = [b[0]-a[0], b[1]-a[1], b[2]-a[2]];
    const v = [c[0]-a[0], c[1]-a[1], c[2]-a[2]];
    const n = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]];
    const norm = Math.hypot(...n) || 1;
    lines.push("vn " + n.map(value => (value/norm).toFixed(5)).join(" "));
    const normalId = lines.filter(line => line.startsWith("vn ")).length;
    lines.push("f " + face.map(index => index + "/" + index + "/" + normalId).join(" "));
  }
  write(path.join(modelDir, spec.name + ".obj"), lines.join("\n") + "\n");
  modelManifest.push({
    id: spec.name, title: spec.title, vertices: spec.vertices.length,
    faces: spec.faces.length, topology: spec.faces.some(face=>face.length===2) ? "edges" : "polygon mesh",
    normals: "generated per-face cross product", uv: "planar UV coordinates written to OBJ",
    material: "studio.mtl", recipe: "mesh.vertices = " + JSON.stringify(spec.vertices) + "; mesh.faces = " + JSON.stringify(spec.faces)
  });
}
write(path.join(modelDir, "studio.mtl"), "newmtl base\nKa 0.12 0.14 0.2\nKd 0.42 0.55 0.9\nKs 0.4 0.4 0.4\nNs 48\nmap_Kd ../textures/checker.ppm\n");
function ppm(name, colorA, colorB) {
  const width = 16, height = 16, pixels = [];
  for (let y=0;y<height;y++) for(let x=0;x<width;x++) {
    const c = ((x>>2)+(y>>2))%2 ? colorA : colorB;
    pixels.push(...c);
  }
  write(path.join(textureDir,name), "P3\n"+width+" "+height+"\n255\n"+pixels.join(" ")+"\n");
}
ppm("checker.ppm",[70,110,190],[220,230,250]);
ppm("wood.ppm",[105,62,35],[160,105,60]);
ppm("metal.ppm",[90,105,125],[175,190,210]);
write(path.join(generated,"model-manifest.json"), modelManifest);
write(path.join(animationDir,"simple-clips.json"), {
  idle:{duration:2,loop:true,channels:[{target:"root.rotation.y",keys:[[0,0],[2,0.08]]},{target:"root.position.y",keys:[[0,0],[1,0.04],[2,0]]}]},
  walk:{duration:1,loop:true,channels:[{target:"leftLeg.rotation.x",keys:[[0,-0.45],[0.5,0.45],[1,-0.45]]},{target:"rightLeg.rotation.x",keys:[[0,0.45],[0.5,-0.45],[1,0.45]]},{target:"root.position.y",keys:[[0,0],[0.5,0.08],[1,0]]}]},
  run:{duration:0.55,loop:true,channels:[{target:"leftLeg.rotation.x",keys:[[0,-0.8],[0.275,0.8],[0.55,-0.8]]},{target:"rightLeg.rotation.x",keys:[[0,0.8],[0.275,-0.8],[0.55,0.8]]},{target:"root.position.y",keys:[[0,0],[0.275,0.16],[0.55,0]]}]},
  jump:{duration:1.2,loop:false,channels:[{target:"root.position.y",keys:[[0,0],[0.3,1.1],[0.75,1.1],[1.2,0]]},{target:"root.rotation.x",keys:[[0,0],[0.3,-0.2],[0.75,0.2],[1.2,0]]}]}
});
write(path.join(animationDir,"advanced-clips.json"), {
  combo:{duration:2.4,loop:false,channels:[
    {target:"root.rotation.y",keys:[[0,0],[0.3,-0.35],[0.8,0.5],[1.2,-0.7],[1.8,0.4],[2.4,0]]},
    {target:"rightArm.rotation.x",keys:[[0,0],[0.25,-1.2],[0.55,0.8],[0.9,-1.1],[1.3,0.2],[2.4,0]]},
    {target:"leftArm.rotation.x",keys:[[0,0],[0.5,-0.2],[1.1,0.7],[1.5,-0.8],[2.4,0]]},
    {target:"root.position.y",keys:[[0,0],[0.6,0.15],[1.1,0],[1.5,0.3],[1.9,0],[2.4,0]]}
  ]},
  turnAndReact:{duration:3,loop:false,channels:[
    {target:"root.rotation.y",keys:[[0,0],[0.9,1.57],[1.5,1.57],[2.3,0.2],[3,0]]},
    {target:"head.rotation.x",keys:[[0,0],[1.1,-0.2],[1.5,0.25],[2.1,-0.12],[3,0]]},
    {target:"root.position.x",keys:[[0,0],[1.2,0],[2,0.35],[3,0]]}
  ]}
});
write(path.join(generated,"training-report.json"), {
  status:"trained",
  training:"from-scratch supervised MLP",
  task:"multilingual prompt-to-scene-category",
  languages:["Portuguese","English","Spanish","Mandarin Chinese","Hindi","Arabic"],
  examples:examples.length,
  vocabularySize: vocabulary.length,
  epochs,
  finalLoss,
  trainingAccuracy:accuracy,
  validationAccuracy,
  geometryModels:modelManifest.length,
  textureMaps:3,
  simpleAnimationClips:4,
  advancedAnimationClips:2,
  note:"Small baseline classifier, not a general-purpose LLM or a full 3D generator."
});
for (const spec of modelSpecs) {
  const obj = fs.readFileSync(path.join(modelDir, spec.name + ".obj"), "utf8");
  const vertexLines = obj.split("\n").filter(line => line.startsWith("v ")).length;
  const uvLines = obj.split("\n").filter(line => line.startsWith("vt ")).length;
  if (vertexLines !== spec.vertices.length || uvLines !== spec.vertices.length) throw new Error("Mesh export validation failed: " + spec.name);
}
if (!Number.isFinite(validationAccuracy) || validationAccuracy < 0.7) {
  throw new Error("Sandbox validation failed: " + validationAccuracy);
}
console.log(JSON.stringify({samples:examples.length,vocabulary:inputSize,epochs,finalLoss,trainingAccuracy:accuracy,validationAccuracy,models:modelManifest.length,animations:6},null,2));
