import { parseForge } from "./forge.js";

const $ = (selector) => document.querySelector(selector);
const source = $("#sourceCode");
const canvas = $("#preview2d");
const context = canvas.getContext("2d");
const preview3d = $("#preview3d");
const timeline = $("#timeline");
const STORAGE_KEY = "motionforge.source.v1";
let sceneData = null;
let currentTime = 0;
let playing = false;
let frame = 0;
let lastStamp = 0;
let THREE = null;
let renderer = null;
let world = null;
let camera = null;
let meshes = new Map();
let generatedCode = "";
let corpusPromise = null;

const EXAMPLE_2D = 'project "MotionDemo"\nscene "Bola" mode 2d fps 30 duration 2\nobject "Bola" circle color "#58d6ff" at (40,120,0) size (36,36)\nanimate "Bola" move from (40,120,0) to (330,120,0) from 0s to 2s ease smooth';
const EXAMPLE_3D = 'project "MotionDemo3D"\nscene "Orbita" mode 3d fps 30 duration 4\nobject "Nucleo" sphere color "#77e6ff" at (0,0,0) scale (1,1,1)\nanimate "Nucleo" rotate from (0,0,0) to (0,360,0) from 0s to 4s ease linear';

function vectorAt(from, to, amount) {
  return from.map((value, index) => value + ((to[index] ?? value) - value) * amount);
}

function stateFor(object, time) {
  const state = { position: object.position.slice(), dimensions: object.dimensions.slice(), rotation: [0, 0, 0] };
  const animations = sceneData.animations.filter((item) => item.target === object.name);
  for (const animation of animations) {
    const raw = Math.max(0, Math.min(1, (time - animation.start) / (animation.end - animation.start)));
    const amount = animation.easing === "smooth" ? raw * raw * (3 - 2 * raw) : raw;
    if (animation.property === "move") state.position = vectorAt(animation.from, animation.to, amount);
    if (animation.property === "rotate") state.rotation = vectorAt(animation.from, animation.to, amount);
    if (animation.property === "scale") state.dimensions = vectorAt(animation.from, animation.to, amount);
  }
  return state;
}

function resizeCanvas() {
  const ratio = Math.min(window.devicePixelRatio || 1, 2);
  const box = canvas.getBoundingClientRect();
  canvas.width = Math.max(1, Math.floor(box.width * ratio));
  canvas.height = Math.max(1, Math.floor(box.height * ratio));
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
}

function draw2d(time) {
  if (!sceneData) return;
  resizeCanvas();
  const width = canvas.clientWidth, height = canvas.clientHeight;
  context.clearRect(0, 0, width, height);
  for (const object of sceneData.objects) {
    const state = stateFor(object, time);
    const x = state.position[0], y = state.position[1];
    const w = state.dimensions[0] || 30, h = state.dimensions[1] || w;
    context.save();
    context.translate(x, y);
    context.rotate((state.rotation[2] || 0) * Math.PI / 180);
    context.fillStyle = object.color;
    context.shadowColor = object.color;
    context.shadowBlur = 16;
    if (object.type === "circle" || object.type === "sphere") {
      context.beginPath();
      context.ellipse(0, 0, w / 2, h / 2, 0, 0, Math.PI * 2);
      context.fill();
    } else {
      context.fillRect(-w / 2, -h / 2, w, h);
    }
    context.restore();
  }
  updateTimeline(time);
}

async function ensureThree() {
  if (!THREE) THREE = await import("https://cdn.jsdelivr.net/npm/three@0.180.0/build/three.module.js");
  if (!renderer) {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    preview3d.replaceChildren(renderer.domElement);
    world = new THREE.Scene();
    world.background = new THREE.Color("#0b121b");
    camera = new THREE.PerspectiveCamera(45, 1, 0.1, 1000);
    camera.position.set(4, 3, 7);
    camera.lookAt(0, 0, 0);
    world.add(new THREE.HemisphereLight(0xc9e6ff, 0x182235, 2));
    const light = new THREE.DirectionalLight(0xffffff, 2.5);
    light.position.set(3, 5, 5);
    world.add(light);
  }
  const width = Math.max(1, preview3d.clientWidth), height = Math.max(1, preview3d.clientHeight);
  renderer.setSize(width, height);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
}

function geometryFor(object) {
  const dimension = object.dimensions;
  if (object.type === "sphere" || object.type === "circle") return new THREE.SphereGeometry(0.7, 24, 16);
  if (object.type === "cone") return new THREE.ConeGeometry(0.7, 1.5, 24);
  if (object.type === "torus") return new THREE.TorusGeometry(0.65, 0.22, 12, 32);
  return new THREE.BoxGeometry(1, 1, 1);
}

async function setup3d() {
  await ensureThree();
  world.children.slice().filter((child) => child.isMesh).forEach((mesh) => { world.remove(mesh); mesh.geometry.dispose(); mesh.material.dispose(); });
  meshes = new Map();
  sceneData.objects.forEach((object) => {
    const material = new THREE.MeshStandardMaterial({ color: object.color, roughness: 0.42, metalness: 0.12 });
    const mesh = new THREE.Mesh(geometryFor(object), material);
    mesh.name = object.name;
    world.add(mesh);
    meshes.set(object.name, mesh);
  });
  $("#preview3d").classList.remove("hidden");
  canvas.classList.add("hidden");
  $("#emptyState").classList.add("hidden");
  draw3d(currentTime);
}

function draw3d(time) {
  if (!renderer || !world || !sceneData) return;
  for (const object of sceneData.objects) {
    const mesh = meshes.get(object.name);
    if (!mesh) continue;
    const state = stateFor(object, time);
    mesh.position.set(state.position[0], state.position[1], state.position[2]);
    mesh.rotation.set(state.rotation[0] * Math.PI / 180, state.rotation[1] * Math.PI / 180, state.rotation[2] * Math.PI / 180);
    const factor = object.type === "box" ? 1 : 1;
    mesh.scale.set((state.dimensions[0] || 1) * factor, (state.dimensions[1] || state.dimensions[0] || 1) * factor, state.dimensions[2] || state.dimensions[0] || 1);
  }
  renderer.render(world, camera);
  updateTimeline(time);
}

function updateTimeline(time) {
  currentTime = Math.max(0, Math.min(sceneData.duration, time));
  timeline.value = String(currentTime);
  $("#timeReadout").textContent = "00:" + String(Math.floor(currentTime / 60)).padStart(2, "0") + ":" + (currentTime % 60).toFixed(2).padStart(5, "0") + " / " + sceneData.duration.toFixed(2) + " s";
}

async function render(time) {
  if (!sceneData) return;
  if (sceneData.mode === "3d") draw3d(time);
  else draw2d(time);
}

function setDiagnostic(message, status) {
  const node = $("#diagnostics");
  node.className = "diagnostics" + (status ? " " + status : "");
  node.textContent = message;
}

function stopPlayback() {
  playing = false;
  lastStamp = 0;
  $("#playPause").textContent = "▶";
  if (frame) cancelAnimationFrame(frame);
  frame = 0;
}

async function runCode() {
  stopPlayback();
  try {
    sceneData = parseForge(source.value);
    currentTime = 0;
    $("#sceneTitle").textContent = sceneData.name;
    $("#modeBadge").textContent = sceneData.mode.toUpperCase();
    $("#objectCount").textContent = String(sceneData.objects.length);
    $("#durationValue").textContent = sceneData.duration.toFixed(1) + " s";
    $("#fpsValue").textContent = String(sceneData.fps);
    timeline.max = String(sceneData.duration);
    $("#durationMark").textContent = sceneData.duration + "s";
    $("#halfMark").textContent = (sceneData.duration / 2).toFixed(1) + "s";
    $("#statusText").textContent = "Cena válida";
    if (sceneData.mode === "3d") {
      try { await setup3d(); }
      catch (error) {
        $("#preview3d").classList.add("hidden");
        canvas.classList.remove("hidden");
        throw new Error("A cena é válida, mas o motor 3D precisa de internet/WebGL: " + error.message);
      }
    } else {
      $("#preview3d").classList.add("hidden");
      canvas.classList.remove("hidden");
      $("#emptyState").classList.add("hidden");
      if (renderer) { renderer.dispose(); renderer = null; world = null; camera = null; meshes = new Map(); }
    }
    setDiagnostic("Cena válida: " + sceneData.objects.length + " objeto(s), " + sceneData.animations.length + " animação(ões).", "success");
    try { localStorage.setItem(STORAGE_KEY, source.value); } catch {}
    await render(0);
  } catch (error) {
    sceneData = null;
    $("#emptyState").classList.remove("hidden");
    setDiagnostic(error.message || "Falha ao analisar FORGE.", "error");
    $("#statusText").textContent = "Corrija o script";
  }
}

function tick(stamp) {
  if (!playing || !sceneData) return;
  if (!lastStamp) lastStamp = stamp;
  currentTime += Math.min((stamp - lastStamp) / 1000, 0.05);
  lastStamp = stamp;
  if (currentTime > sceneData.duration) currentTime = 0;
  render(currentTime);
  frame = requestAnimationFrame(tick);
}

async function togglePlay() {
  if (!sceneData) await runCode();
  if (!sceneData) return;
  playing = !playing;
  $("#playPause").textContent = playing ? "Ⅱ" : "▶";
  if (playing) frame = requestAnimationFrame(tick);
  else stopPlayback();
}

function normalizeWords(text) {
  return new Set(String(text).toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").match(/[a-z0-9_]+/g)?.filter((word) => word.length > 1) || []);
}

async function browserCorpusAnswer(query) {
  if (!corpusPromise) corpusPromise = fetch("./seed-examples.json").then((response) => { if (!response.ok) throw new Error("Corpus não carregou"); return response.json(); });
  const examples = await corpusPromise;
  const words = normalizeWords(query);
  let best = null, bestScore = 0;
  for (const example of examples) {
    const tokens = normalizeWords(example.prompt);
    const overlap = [...words].filter((word) => tokens.has(word)).length;
    const p = words.size ? overlap / words.size : 0;
    const r = tokens.size ? overlap / tokens.size : 0;
    let score = p + r ? 2 * p * r / (p + r) : 0;
    if (example.prompt.toLowerCase() === query.toLowerCase()) score = 1;
    if (score > bestScore) { best = example; bestScore = score; }
  }
  if (best && bestScore >= 0.18) return { answer: best.response, matched_prompt: best.prompt, confidence: bestScore, method: "corpus do navegador" };
  return { answer: "Ainda não há um exemplo confiável para esse pedido. Acrescente exemplos aprovados pelos três professores e treine novamente.", matched_prompt: best ? best.prompt : null, related_example: best ? best.response : null, confidence: bestScore, method: "abstenção" };
}

async function requestLocal(path, body) {
  const response = await fetch("http://127.0.0.1:8765" + path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), signal: AbortSignal.timeout(20000) });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Falha HTTP " + response.status);
  return data;
}

function codeFrom(text) {
  const lines = String(text).split(/\r?\n/);
  const start = lines.findIndex((line) => /^(project|scene|object|animate)\s/.test(line.trim()));
  if (start < 0) return "";
  const found = [];
  for (let i = start; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) { if (found.length) break; continue; }
    if (/^(project|scene|object|animate)\s/.test(line)) found.push(line);
    else if (found.length) break;
  }
  return found.join("\n");
}

function showAssistant(text, code) {
  $("#assistantOutput").textContent = text;
  generatedCode = code || "";
  $("#applyCode").classList.toggle("hidden", !generatedCode);
}

$("#runCode").addEventListener("click", runCode);
$("#resetTime").addEventListener("click", () => { stopPlayback(); render(0); });
$("#playPause").addEventListener("click", togglePlay);
$("#example2d").addEventListener("click", () => { source.value = EXAMPLE_2D; $("#lineInfo").textContent = source.value.split("\n").length + " linhas"; runCode(); });
$("#example3d").addEventListener("click", () => { source.value = EXAMPLE_3D; $("#lineInfo").textContent = source.value.split("\n").length + " linhas"; runCode(); });
timeline.addEventListener("input", () => { stopPlayback(); render(Number(timeline.value)); });
source.addEventListener("input", () => { $("#lineInfo").textContent = source.value.split("\n").length + " linhas"; });
$("#exportFile").addEventListener("click", () => {
  const url = URL.createObjectURL(new Blob([source.value], { type: "text/plain;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url; link.download = "scene.forge"; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
$("#askLocal").addEventListener("click", async () => {
  const prompt = $("#assistantPrompt").value.trim();
  if (!prompt) { showAssistant("Escreva uma tarefa antes de perguntar."); return; }
  showAssistant("Consultando o aluno local…");
  try {
    const result = await requestLocal("/chat", { prompt });
    const code = codeFrom(result.answer || "") || codeFrom(result.related_example || "");
    showAssistant(result.answer + "\n\nMétodo: " + result.method + " · confiança " + Math.round((result.confidence || 0) * 100) + "%\nModelo: " + result.model + " · " + Number(result.parameters || 247890).toLocaleString("pt-BR") + " parâmetros\n" + (result.warning || ""), code);
  } catch (error) {
    try {
      const result = await browserCorpusAnswer(prompt);
      showAssistant(result.answer + (result.related_example ? "\n\nExemplo relacionado:\n" + result.related_example : "") + "\n\nMétodo: " + result.method + " · correspondência " + Math.round(result.confidence * 100) + "%. Servidor neural offline: resposta vem do corpus semente.", codeFrom(result.answer) || codeFrom(result.related_example || ""));
    } catch (fallback) { showAssistant("Assistente indisponível: " + fallback.message); }
  }
});
$("#researchWeb").addEventListener("click", async () => {
  const query = $("#assistantPrompt").value.trim();
  if (!query) { showAssistant("Escreva o assunto da pesquisa."); return; }
  showAssistant("Pesquisando fontes externas…");
  try {
    const result = await requestLocal("/research", { query });
    const text = (result.results || []).map((row, index) => (index + 1) + ". " + row.title + "\n" + row.url + "\n" + row.snippet).join("\n\n");
    showAssistant(text || "Nenhum resultado encontrado.");
  } catch (error) {
    showAssistant("Servidor de pesquisa local indisponível (" + error.message + "). A pesquisa será aberta no navegador.");
    const link = document.createElement("a");
    link.href = "https://duckduckgo.com/?q=" + encodeURIComponent(query);
    link.target = "_blank"; link.rel = "noopener noreferrer"; link.textContent = "Abrir pesquisa ↗";
    $("#assistantOutput").append(document.createElement("br"), link);
  }
});
$("#applyCode").addEventListener("click", () => {
  if (!generatedCode) return;
  try { parseForge(generatedCode); source.value = generatedCode; $("#lineInfo").textContent = source.value.split("\n").length + " linhas"; runCode(); }
  catch (error) { showAssistant("O script sugerido não passou pelo parser: " + error.message); }
});
window.addEventListener("resize", () => { if (!sceneData) return; if (sceneData.mode === "2d") render(currentTime); else if (renderer) ensureThree().then(() => render(currentTime)); });
try { source.value = localStorage.getItem(STORAGE_KEY) || source.value; } catch {}
$("#lineInfo").textContent = source.value.split("\n").length + " linhas";
runCode();
