import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { TransformControls } from "three/addons/controls/TransformControls.js";
import { GLTFExporter } from "three/addons/exporters/GLTFExporter.js";
import { OBJExporter } from "three/addons/exporters/OBJExporter.js";
import { STLExporter } from "three/addons/exporters/STLExporter.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";

const $ = (id) => document.getElementById(id);
const viewport = $("viewport");
const sceneRoot = $("sceneTree");
const modelRoot = new THREE.Group();
modelRoot.name = "Modelo";
const clock = new THREE.Clock();

let renderer;
let scene;
let camera;
let orbit;
let transform;
let keyLight;
let fillLight;
let rimLight;
let grid;
let floor;
let environmentTarget;
let noiseTexture;
let selected = null;
let selectionBox = null;
let toastTimer = 0;
let objectCounter = 0;
let projectTitle = "Projeto sem título";

const presets = {
  chrome: { label: "Cromo polido", color: "#b9c5d8", metalness: 0.96, roughness: 0.12, clearcoat: 0.35, clearcoatRoughness: 0.12, bump: 0.006 },
  steel: { label: "Aço escovado", color: "#8999ad", metalness: 0.88, roughness: 0.32, clearcoat: 0.18, clearcoatRoughness: 0.3, bump: 0.018 },
  gold: { label: "Ouro", color: "#d9a83f", metalness: 0.94, roughness: 0.2, clearcoat: 0.32, clearcoatRoughness: 0.18, bump: 0.008 },
  ceramic: { label: "Cerâmica", color: "#e8edf5", metalness: 0.02, roughness: 0.2, clearcoat: 0.85, clearcoatRoughness: 0.12, bump: 0.004 },
  glass: { label: "Vidro", color: "#b9e2f5", metalness: 0, roughness: 0.055, clearcoat: 1, clearcoatRoughness: 0.05, transmission: 0.94, thickness: 0.8, ior: 1.46, bump: 0 },
  plastic: { label: "Plástico", color: "#d94e57", metalness: 0.04, roughness: 0.28, clearcoat: 0.65, clearcoatRoughness: 0.2, bump: 0.004 },
  rubber: { label: "Borracha", color: "#242a32", metalness: 0, roughness: 0.9, clearcoat: 0, clearcoatRoughness: 1, bump: 0.035 },
  stone: { label: "Pedra", color: "#777d85", metalness: 0, roughness: 0.94, clearcoat: 0, clearcoatRoughness: 1, bump: 0.075 },
  skin: { label: "Superfície orgânica", color: "#bd806a", metalness: 0, roughness: 0.62, clearcoat: 0.08, clearcoatRoughness: 0.5, bump: 0.012 }
};

function showToast(message) {
  const toast = $("toast");
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("show"), 2500);
}

function makeNoiseTexture() {
  const canvas = document.createElement("canvas");
  canvas.width = 256;
  canvas.height = 256;
  const context = canvas.getContext("2d");
  const image = context.createImageData(canvas.width, canvas.height);
  for (let i = 0; i < image.data.length; i += 4) {
    const value = 116 + Math.floor(Math.random() * 24);
    image.data[i] = value;
    image.data[i + 1] = value;
    image.data[i + 2] = value;
    image.data[i + 3] = 255;
  }
  context.putImageData(image, 0, 0);
  const texture = new THREE.CanvasTexture(canvas);
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.RepeatWrapping;
  texture.repeat.set(3, 3);
  texture.anisotropy = 4;
  texture.colorSpace = THREE.NoColorSpace;
  return texture;
}

function createMaterial(presetName = "chrome") {
  const preset = presets[presetName] || presets.chrome;
  const material = new THREE.MeshPhysicalMaterial({
    color: preset.color,
    metalness: preset.metalness,
    roughness: preset.roughness,
    clearcoat: preset.clearcoat,
    clearcoatRoughness: preset.clearcoatRoughness,
    transmission: preset.transmission || 0,
    thickness: preset.thickness || 0,
    ior: preset.ior || 1.5,
    envMapIntensity: 1,
    side: THREE.DoubleSide
  });
  if (noiseTexture && preset.bump > 0) {
    material.bumpMap = noiseTexture;
    material.bumpScale = preset.bump;
  }
  return material;
}

function getMeshes(object) {
  const result = [];
  if (!object) return result;
  object.traverse((child) => {
    if (child.isMesh) result.push(child);
  });
  return result;
}

function getPrimaryMaterial(object) {
  const mesh = getMeshes(object)[0];
  if (!mesh || !mesh.material) return null;
  return Array.isArray(mesh.material) ? mesh.material[0] : mesh.material;
}

function setMaterial(object, presetName) {
  const meshes = getMeshes(object);
  if (!meshes.length) return;
  for (const mesh of meshes) {
    const oldMaterial = mesh.material;
    const nextMaterial = createMaterial(presetName);
    if (Array.isArray(oldMaterial)) {
      oldMaterial.forEach((item) => item.dispose?.());
    } else {
      oldMaterial?.dispose?.();
    }
    mesh.material = nextMaterial;
  }
  updateProperties();
  renderSceneTree();
}

function makeRockGeometry(seed = 1) {
  const geometry = new THREE.IcosahedronGeometry(0.86, 4);
  const position = geometry.getAttribute("position");
  for (let i = 0; i < position.count; i++) {
    const x = position.getX(i);
    const y = position.getY(i);
    const z = position.getZ(i);
    const waveA = Math.sin(x * 8.7 + y * 4.1 + seed) * 0.045;
    const waveB = Math.cos(y * 10.3 - z * 5.4 + seed * 2) * 0.035;
    const waveC = Math.sin(z * 13.1 + x * 6.2) * 0.025;
    const factor = 1 + waveA + waveB + waveC;
    position.setXYZ(i, x * factor * 1.08, y * factor * 0.82, z * factor);
  }
  geometry.computeVertexNormals();
  return geometry;
}

function geometryFor(type) {
  switch (type) {
    case "box": return new THREE.BoxGeometry(1.35, 1.35, 1.35, 2, 2, 2);
    case "sphere": return new THREE.SphereGeometry(0.82, 72, 56);
    case "cylinder": return new THREE.CylinderGeometry(0.66, 0.66, 1.35, 72, 2);
    case "torus": return new THREE.TorusGeometry(0.68, 0.22, 28, 112);
    case "cone": return new THREE.ConeGeometry(0.75, 1.5, 72, 3);
    case "knot": return new THREE.TorusKnotGeometry(0.62, 0.19, 160, 24, 2, 3);
    case "plane": return new THREE.PlaneGeometry(1.8, 1.8, 1, 1);
    case "rock": return makeRockGeometry(++objectCounter);
    default: return new THREE.BoxGeometry(1.2, 1.2, 1.2);
  }
}

function primitiveLabel(type) {
  const names = {
    box: "Cubo", sphere: "Esfera", cylinder: "Cilindro", torus: "Rosca",
    cone: "Cone", knot: "Nó toroidal", plane: "Plano", rock: "Rocha procedural"
  };
  return names[type] || "Objeto";
}

function addPrimitive(type) {
  if (!scene) return;
  objectCounter += 1;
  const materialName = type === "rock" ? "stone" : "chrome";
  const mesh = new THREE.Mesh(geometryFor(type), createMaterial(materialName));
  mesh.name = primitiveLabel(type) + " " + String(objectCounter).padStart(2, "0");
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  if (type === "plane") {
    mesh.rotation.x = -Math.PI / 2;
    mesh.position.y = -0.72;
  } else if (modelRoot.children.length) {
    mesh.position.x = Math.min(2.2, (modelRoot.children.length % 4) * 0.28);
    mesh.position.y = 0.05;
  }
  modelRoot.add(mesh);
  setSelected(mesh);
  renderSceneTree();
  updateStats();
  showToast(primitiveLabel(type) + " adicionado");
}

function disposeSelectionBox() {
  if (!selectionBox || !scene) return;
  scene.remove(selectionBox);
  selectionBox.geometry?.dispose();
  selectionBox.material?.dispose();
  selectionBox = null;
}

function setSelected(object) {
  selected = object || null;
  if (transform) {
    if (selected) transform.attach(selected);
    else transform.detach();
  }
  disposeSelectionBox();
  if (selected) {
    selectionBox = new THREE.BoxHelper(selected, 0x87b5ff);
    scene.add(selectionBox);
  }
  updateProperties();
  renderSceneTree();
}

function renderSceneTree() {
  if (!sceneRoot) return;
  sceneRoot.replaceChildren();
  const objects = [...modelRoot.children].reverse();
  if (!objects.length) {
    const empty = document.createElement("div");
    empty.className = "tree-item";
    empty.textContent = "Nenhum objeto na cena";
    empty.style.color = "#687891";
    sceneRoot.append(empty);
    return;
  }
  for (const object of objects) {
    const row = document.createElement("button");
    row.type = "button";
    row.className = "tree-item" + (selected === object ? " selected" : "");
    const glyph = document.createElement("span");
    glyph.className = "tree-glyph";
    glyph.textContent = object.isGroup ? "◇" : "◈";
    const name = document.createElement("span");
    name.className = "tree-name";
    name.textContent = object.name || "Objeto sem nome";
    row.append(glyph, name);
    row.addEventListener("click", () => setSelected(object));
    sceneRoot.append(row);
  }
}

function updateStats() {
  const meshes = getMeshes(modelRoot);
  let triangles = 0;
  for (const mesh of meshes) {
    const geometry = mesh.geometry;
    const position = geometry?.getAttribute("position");
    if (!position) continue;
    triangles += geometry.index ? geometry.index.count / 3 : position.count / 3;
  }
  $("meshStats").textContent = meshes.length + " malha(s) · " + Math.round(triangles).toLocaleString("pt-BR") + " triângulos";
}

function updateProperties() {
  const hasObject = Boolean(selected);
  $("objectName").disabled = !hasObject;
  $("materialPreset").disabled = !hasObject;
  $("baseColor").disabled = !hasObject;
  $("roughness").disabled = !hasObject;
  $("metalness").disabled = !hasObject;
  $("clearcoat").disabled = !hasObject;
  if (!selected) {
    $("objectName").value = "";
    return;
  }
  $("objectName").value = selected.name || "Objeto";
  const material = getPrimaryMaterial(selected);
  if (!material) return;
  $("baseColor").value = "#" + material.color.getHexString();
  $("roughness").value = String(material.roughness ?? 0.5);
  $("metalness").value = String(material.metalness ?? 0);
  $("clearcoat").value = String(material.clearcoat ?? 0);
  updateRangeLabels();
}

function updateRangeLabels() {
  for (const id of ["roughness", "metalness", "clearcoat", "environmentStrength", "lightStrength"]) {
    const output = $(id + "Value");
    if (output) output.value = Number($(id).value).toFixed(2).replace(/0$/, "");
  }
}

function applyMaterialControls() {
  if (!selected) return;
  const meshes = getMeshes(selected);
  const color = $("baseColor").value;
  const roughness = Number($("roughness").value);
  const metalness = Number($("metalness").value);
  const clearcoat = Number($("clearcoat").value);
  for (const mesh of meshes) {
    const material = Array.isArray(mesh.material) ? mesh.material[0] : mesh.material;
    if (!material) continue;
    material.color.set(color);
    material.roughness = roughness;
    material.metalness = metalness;
    material.clearcoat = clearcoat;
    material.needsUpdate = true;
  }
  updateRangeLabels();
}

function setLightingPreset(name) {
  if (!keyLight || !fillLight || !rimLight) return;
  const options = {
    softbox: { key: 3, fill: 1.25, rim: 1.6, color: 0xffffff },
    cinematic: { key: 4.2, fill: 0.48, rim: 2.8, color: 0xffe0c2 },
    product: { key: 2.6, fill: 1.8, rim: 1.1, color: 0xffffff }
  }[name] || { key: 3, fill: 1.25, rim: 1.6, color: 0xffffff };
  keyLight.intensity = options.key;
  keyLight.color.setHex(options.color);
  fillLight.intensity = options.fill;
  rimLight.intensity = options.rim;
  $("lightStrength").value = String(options.key);
  updateRangeLabels();
}

function initScene() {
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: "high-performance" });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
  renderer.setSize(viewport.clientWidth, viewport.clientHeight);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.12;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.domElement.setAttribute("aria-label", "Viewport para edição 3D");
  renderer.domElement.style.touchAction = "none";
  viewport.prepend(renderer.domElement);

  scene = new THREE.Scene();
  scene.background = new THREE.Color("#0b111d");

  camera = new THREE.PerspectiveCamera(42, viewport.clientWidth / viewport.clientHeight, 0.1, 300);
  camera.position.set(4.2, 3.1, 5.5);

  orbit = new OrbitControls(camera, renderer.domElement);
  orbit.enableDamping = true;
  orbit.dampingFactor = 0.065;
  orbit.minDistance = 1.3;
  orbit.maxDistance = 45;
  orbit.target.set(0, 0, 0);
  orbit.update();

  transform = new TransformControls(camera, renderer.domElement);
  transform.setMode("translate");
  transform.setSize(0.78);
  scene.add(transform.getHelper());
  transform.addEventListener("dragging-changed", (event) => {
    orbit.enabled = !event.value;
  });
  transform.addEventListener("objectChange", () => {
    if (selectionBox) selectionBox.update();
    renderSceneTree();
  });

  const hemisphere = new THREE.HemisphereLight(0xc5d9ff, 0x201a20, 1.15);
  scene.add(hemisphere);

  keyLight = new THREE.DirectionalLight(0xffffff, 3);
  keyLight.position.set(4.5, 7.5, 5);
  keyLight.castShadow = true;
  keyLight.shadow.mapSize.set(2048, 2048);
  keyLight.shadow.camera.near = 0.1;
  keyLight.shadow.camera.far = 30;
  keyLight.shadow.camera.left = -8;
  keyLight.shadow.camera.right = 8;
  keyLight.shadow.camera.top = 8;
  keyLight.shadow.camera.bottom = -8;
  keyLight.shadow.bias = -0.00025;
  keyLight.shadow.normalBias = 0.02;
  scene.add(keyLight);

  fillLight = new THREE.DirectionalLight(0x9bbdff, 1.25);
  fillLight.position.set(-5, 2.5, -3);
  scene.add(fillLight);

  rimLight = new THREE.DirectionalLight(0xffd6b2, 1.6);
  rimLight.position.set(1, 4, -6);
  scene.add(rimLight);

  floor = new THREE.Mesh(
    new THREE.PlaneGeometry(200, 200),
    new THREE.MeshStandardMaterial({ color: "#111827", roughness: 0.92, metalness: 0.05 })
  );
  floor.rotation.x = -Math.PI / 2;
  floor.position.y = -0.9;
  floor.receiveShadow = true;
  scene.add(floor);

  grid = new THREE.GridHelper(24, 48, 0x314766, 0x1e2b3d);
  grid.position.y = -0.895;
  scene.add(grid);

  noiseTexture = makeNoiseTexture();
  const pmrem = new THREE.PMREMGenerator(renderer);
  const room = new RoomEnvironment();
  environmentTarget = pmrem.fromScene(room, 0.04);
  scene.environment = environmentTarget.texture;
  scene.environmentIntensity = 1;
  pmrem.dispose();

  scene.add(modelRoot);
  addPrimitive("sphere");
  $("loadingState").classList.add("hidden");

  const resizeObserver = new ResizeObserver(() => resizeRenderer());
  resizeObserver.observe(viewport);
  window.addEventListener("orientationchange", () => setTimeout(resizeRenderer, 150));
  animate();
}

function resizeRenderer() {
  if (!renderer || !camera) return;
  const width = Math.max(1, viewport.clientWidth);
  const height = Math.max(1, viewport.clientHeight);
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
}

function animate() {
  requestAnimationFrame(animate);
  orbit?.update();
  if (selectionBox) selectionBox.update();
  renderer.render(scene, camera);
}

function setTransformMode(mode) {
  if (!transform) return;
  transform.setMode(mode);
  document.querySelectorAll("[data-mode]").forEach((button) => {
    button.classList.toggle("active", button.dataset.mode === mode);
  });
}

function focusSelected() {
  if (!selected) {
    orbit.target.set(0, 0, 0);
    camera.position.set(4.2, 3.1, 5.5);
    orbit.update();
    return;
  }
  const bounds = new THREE.Box3().setFromObject(selected);
  const center = bounds.getCenter(new THREE.Vector3());
  const sphere = bounds.getBoundingSphere(new THREE.Sphere());
  const distance = Math.max(2.2, sphere.radius * 3.6);
  orbit.target.copy(center);
  camera.position.copy(center).add(new THREE.Vector3(distance * 0.72, distance * 0.48, distance));
  orbit.update();
}

function duplicateSelected() {
  if (!selected) return showToast("Selecione um objeto primeiro");
  const copy = selected.clone(true);
  copy.name = (selected.name || "Objeto") + " cópia";
  copy.position.x += 0.75;
  modelRoot.add(copy);
  setSelected(copy);
  updateStats();
  showToast("Objeto duplicado");
}

function deleteSelected() {
  if (!selected) return showToast("Nenhum objeto selecionado");
  const target = selected;
  transform.detach();
  modelRoot.remove(target);
  selected = null;
  disposeSelectionBox();
  updateProperties();
  renderSceneTree();
  updateStats();
  showToast("Objeto removido");
}

function downloadBlob(blob, fileName) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = fileName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1500);
}

function exportGLB() {
  if (!modelRoot.children.length) return showToast("A cena não possui objetos para exportar");
  showToast("Preparando arquivo GLB…");
  const exporter = new GLTFExporter();
  exporter.parse(
    modelRoot,
    (result) => {
      const blob = new Blob([result], { type: "model/gltf-binary" });
      downloadBlob(blob, "aether-model.glb");
      showToast("Modelo GLB exportado");
    },
    (error) => {
      console.error(error);
      showToast("Falha ao exportar GLB");
    },
    { binary: true, onlyVisible: true, trs: false, maxTextureSize: 2048 }
  );
}

function exportOBJ() {
  if (!modelRoot.children.length) return showToast("A cena não possui objetos para exportar");
  const data = new OBJExporter().parse(modelRoot);
  downloadBlob(new Blob([data], { type: "text/plain" }), "aether-model.obj");
  showToast("Modelo OBJ exportado");
}

function exportSTL() {
  if (!modelRoot.children.length) return showToast("A cena não possui objetos para exportar");
  const data = new STLExporter().parse(modelRoot, { binary: true });
  downloadBlob(new Blob([data], { type: "model/stl" }), "aether-model.stl");
  showToast("Malha STL exportada");
}

function projectJSON() {
  return JSON.stringify({
    app: "Aether 3D Studio",
    version: 1,
    title: projectTitle,
    createdWith: "Three.js",
    model: modelRoot.toJSON()
  });
}

function saveProject() {
  try {
    localStorage.setItem("aether3d-project-v1", projectJSON());
    $("projectStatus").textContent = projectTitle;
    showToast("Projeto salvo neste dispositivo");
  } catch (error) {
    console.error(error);
    showToast("Não foi possível salvar: armazenamento cheio");
  }
}

function downloadProject() {
  const blob = new Blob([projectJSON()], { type: "application/json" });
  downloadBlob(blob, "aether-project.json");
  showToast("Projeto JSON baixado");
}

function loadProjectData(data) {
  const objectData = data.model || data;
  const loadedRoot = new THREE.ObjectLoader().parse(objectData);
  for (const child of [...modelRoot.children]) modelRoot.remove(child);
  for (const child of [...loadedRoot.children]) modelRoot.add(child);
  projectTitle = data.title || "Projeto importado";
  $("projectStatus").textContent = projectTitle;
  setSelected(modelRoot.children[0] || null);
  renderSceneTree();
  updateStats();
  showToast("Projeto carregado");
}

function openFile(file) {
  if (!file) return;
  const extension = file.name.split(".").pop().toLowerCase();
  if (extension === "json") {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        loadProjectData(JSON.parse(String(reader.result)));
      } catch (error) {
        console.error(error);
        showToast("Arquivo JSON de projeto inválido");
      }
    };
    reader.readAsText(file);
    return;
  }
  if (extension === "glb") {
    const reader = new FileReader();
    reader.onload = () => {
      const loader = new GLTFLoader();
      loader.parse(reader.result, "", (gltf) => {
        const imported = gltf.scene;
        imported.name = file.name.replace(/\.glb$/i, "");
        modelRoot.add(imported);
        setSelected(imported);
        updateStats();
        showToast("Modelo GLB importado");
      }, (error) => {
        console.error(error);
        showToast("Não foi possível abrir este GLB");
      });
    };
    reader.readAsArrayBuffer(file);
    return;
  }
  showToast("Formato não suportado. Use GLB ou JSON.");
}

function screenshot() {
  renderer.domElement.toBlob((blob) => {
    if (blob) downloadBlob(blob, "aether-render.png");
    else showToast("Não foi possível capturar a imagem");
  }, "image/png");
}

function bindEvents() {
  document.querySelectorAll("[data-primitive]").forEach((button) => {
    button.addEventListener("click", () => addPrimitive(button.dataset.primitive));
  });
  document.querySelectorAll("[data-mode]").forEach((button) => {
    button.addEventListener("click", () => setTransformMode(button.dataset.mode));
  });

  $("duplicateBtn").addEventListener("click", duplicateSelected);
  $("deleteBtn").addEventListener("click", deleteSelected);
  $("frameBtn").addEventListener("click", focusSelected);
  $("cameraResetBtn").addEventListener("click", () => {
    orbit.reset();
    showToast("Câmera redefinida");
  });
  $("screenshotBtn").addEventListener("click", screenshot);
  $("exportBtn").addEventListener("click", exportGLB);
  $("exportObjBtn").addEventListener("click", exportOBJ);
  $("exportStlBtn").addEventListener("click", exportSTL);
  $("exportProjectBtn").addEventListener("click", downloadProject);
  $("saveBtn").addEventListener("click", saveProject);
  $("openProjectBtn").addEventListener("click", () => $("fileInput").click());
  $("fileInput").addEventListener("change", (event) => {
    openFile(event.target.files?.[0]);
    event.target.value = "";
  });

  $("objectName").addEventListener("input", () => {
    if (!selected) return;
    selected.name = $("objectName").value.slice(0, 48);
    renderSceneTree();
  });
  $("materialPreset").addEventListener("change", () => {
    if (!selected) return;
    setMaterial(selected, $("materialPreset").value);
    const preset = presets[$("materialPreset").value];
    if (preset) {
      $("baseColor").value = preset.color;
      $("roughness").value = String(preset.roughness);
      $("metalness").value = String(preset.metalness);
      $("clearcoat").value = String(preset.clearcoat);
      updateRangeLabels();
    }
  });
  ["baseColor", "roughness", "metalness", "clearcoat"].forEach((id) => {
    $(id).addEventListener("input", applyMaterialControls);
  });

  $("lightingPreset").addEventListener("change", () => setLightingPreset($("lightingPreset").value));
  $("environmentStrength").addEventListener("input", () => {
    scene.environmentIntensity = Number($("environmentStrength").value);
    updateRangeLabels();
  });
  $("lightStrength").addEventListener("input", () => {
    keyLight.intensity = Number($("lightStrength").value);
    updateRangeLabels();
  });
  $("gridToggle").addEventListener("change", () => { grid.visible = $("gridToggle").checked; });
  $("shadowToggle").addEventListener("change", () => {
    renderer.shadowMap.enabled = $("shadowToggle").checked;
    keyLight.castShadow = $("shadowToggle").checked;
    getMeshes(modelRoot).forEach((mesh) => { mesh.castShadow = $("shadowToggle").checked; });
  });
  $("qualityToggle").addEventListener("change", () => {
    const high = $("qualityToggle").checked;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, high ? 2 : 1.15));
    keyLight.shadow.mapSize.set(high ? 3072 : 1024, high ? 3072 : 1024);
    keyLight.shadow.map?.dispose();
    keyLight.shadow.needsUpdate = true;
    renderer.shadowMap.needsUpdate = true;
    showToast(high ? "Qualidade alta ativada" : "Modo leve ativado");
  });

  $("togglePropsBtn").addEventListener("click", () => $("propertiesPanel").classList.toggle("open"));
  $("closePropsBtn").addEventListener("click", () => $("propertiesPanel").classList.remove("open"));
  $("dockMoreBtn").addEventListener("click", () => document.querySelector(".left-panel").classList.toggle("mobile-open"));

  viewport.addEventListener("pointerdown", (event) => {
    if (event.target !== renderer.domElement || transform.dragging) return;
    const bounds = renderer.domElement.getBoundingClientRect();
    const pointer = new THREE.Vector2(
      ((event.clientX - bounds.left) / bounds.width) * 2 - 1,
      -((event.clientY - bounds.top) / bounds.height) * 2 + 1
    );
    const raycaster = new THREE.Raycaster();
    raycaster.setFromCamera(pointer, camera);
    const hits = raycaster.intersectObjects(modelRoot.children, true);
    if (hits.length) {
      let target = hits[0].object;
      while (target.parent && target.parent !== modelRoot) target = target.parent;
      setSelected(target);
    } else if (!transform.dragging) {
      setSelected(null);
    }
  });

  window.addEventListener("keydown", (event) => {
    const tag = document.activeElement?.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
    if (event.key === "Delete" || event.key === "Backspace") deleteSelected();
    if (event.key.toLowerCase() === "g") setTransformMode("translate");
    if (event.key.toLowerCase() === "r") setTransformMode("rotate");
    if (event.key.toLowerCase() === "s" && !event.ctrlKey) setTransformMode("scale");
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "d") {
      event.preventDefault();
      duplicateSelected();
    }
    if (event.key.toLowerCase() === "f") focusSelected();
  });
}

function restoreSavedProject() {
  try {
    const saved = localStorage.getItem("aether3d-project-v1");
    if (!saved) return;
    loadProjectData(JSON.parse(saved));
    showToast("Último projeto recuperado");
  } catch (error) {
    console.warn("Falha ao recuperar projeto salvo", error);
  }
}

try {
  initScene();
  bindEvents();
  restoreSavedProject();
} catch (error) {
  console.error(error);
  $("loadingState").classList.remove("hidden");
  $("loadingState").innerHTML = "<strong>Não foi possível iniciar o motor 3D.</strong><span>Verifique se o navegador permite WebGL e carregamento de módulos.</span>";
  showToast("Falha ao iniciar o renderizador 3D");
}