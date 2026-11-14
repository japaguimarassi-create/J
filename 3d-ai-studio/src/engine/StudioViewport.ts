import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFExporter } from "three/addons/exporters/GLTFExporter.js";
import type { PlannedObject, PrimitiveKind } from "../core/ScenePlanner";

export interface SceneSnapshot {
  version: 1;
  objects: PlannedObject[];
}

export class StudioViewport {
  private readonly scene = new THREE.Scene();
  private readonly camera = new THREE.PerspectiveCamera(45, 1, 0.1, 200);
  private readonly renderer: THREE.WebGLRenderer;
  private readonly controls: OrbitControls;
  private readonly assetRoot = new THREE.Group();
  private readonly raycaster = new THREE.Raycaster();
  private readonly pointer = new THREE.Vector2();
  private readonly meshes = new Map<string, THREE.Mesh>();
  private animationFrame = 0;
  private playing = false;
  private animationPreset: "idle" | "orbit" | "walk" | "run" | "jump" | "combo" = "idle";
  private animationTime = 0;
  private selectedId: string | null = null;
  private readonly resizeObserver: ResizeObserver;
  private readonly onPointerDown = (event: PointerEvent) => this.handlePointer(event);

  constructor(private readonly host: HTMLElement, private readonly selectionListener: (id: string | null) => void) {
    this.scene.background = new THREE.Color("#0b1220");
    this.camera.position.set(5.5, 4.3, 7.5);
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: "low-power" });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.setClearColor("#0b1220", 1);
    this.host.appendChild(this.renderer.domElement);
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.target.set(0, 0.5, 0);
    this.scene.add(
      new THREE.HemisphereLight("#dbe7ff", "#1b2842", 2.2),
      new THREE.DirectionalLight("#ffffff", 2.5),
      new THREE.DirectionalLight("#758fff", 1.2)
    );
    const key = this.scene.children[1] as THREE.DirectionalLight;
    key.position.set(5, 8, 6);
    const rim = this.scene.children[2] as THREE.DirectionalLight;
    rim.position.set(-6, 3, -4);
    const grid = new THREE.GridHelper(30, 30, "#31415d", "#1a2940");
    grid.position.y = -0.72;
    this.scene.add(grid, this.assetRoot);
    this.renderer.domElement.addEventListener("pointerdown", this.onPointerDown);
    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(this.host);
    this.resize();
    this.animate();
  }

  private resize() {
    const width = Math.max(1, this.host.clientWidth);
    const height = Math.max(1, this.host.clientHeight);
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height, false);
  }

  private geometry(kind: PrimitiveKind): THREE.BufferGeometry {
    if (kind === "sphere") return new THREE.SphereGeometry(0.78, 32, 24);
    if (kind === "capsule") return new THREE.CapsuleGeometry(0.48, 1.35, 5, 12);
    if (kind === "torus") return new THREE.TorusGeometry(0.72, 0.18, 12, 48);
    if (kind === "cylinder") return new THREE.CylinderGeometry(0.5, 0.5, 1.4, 20);
    if (kind === "cone") return new THREE.ConeGeometry(0.72, 1.5, 24);
    return new THREE.BoxGeometry(1.35, 1.35, 1.35);
  }

  addPrimitive(kind: PrimitiveKind, name?: string, color?: string): string {
    const uuid = typeof crypto.randomUUID === "function"
      ? crypto.randomUUID()
      : Math.random().toString(36).slice(2) + Date.now().toString(36);
    const id = "object-" + uuid;
    const mesh = new THREE.Mesh(this.geometry(kind), new THREE.MeshStandardMaterial({
      color: color ?? "#6f8cff",
      roughness: 0.42,
      metalness: 0.12
    }));
    mesh.name = name ?? kind.toUpperCase();
    mesh.userData.id = id;
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    mesh.position.x = this.meshes.size * 0.18;
    mesh.userData.basePosition = mesh.position.toArray();
    mesh.userData.baseRotation = mesh.rotation.toArray();
    this.assetRoot.add(mesh);
    this.meshes.set(id, mesh);
    this.select(id);
    return id;
  }

  replaceScene(objects: PlannedObject[]) {
    for (const mesh of this.meshes.values()) {
      mesh.geometry.dispose();
      const material = mesh.material;
      if (Array.isArray(material)) material.forEach((item) => item.dispose());
      else material.dispose();
    }
    this.meshes.clear();
    while (this.assetRoot.children.length) this.assetRoot.remove(this.assetRoot.children[0]);
    for (const item of objects) {
      const mesh = new THREE.Mesh(this.geometry(item.kind), new THREE.MeshStandardMaterial({
        color: item.color,
        roughness: 0.42,
        metalness: 0.12
      }));
      mesh.name = item.name;
      mesh.userData.id = item.id;
      mesh.position.set(...item.position);
      mesh.scale.set(...item.scale);
      mesh.userData.basePosition = mesh.position.toArray();
      mesh.userData.baseRotation = mesh.rotation.toArray();
      this.assetRoot.add(mesh);
      this.meshes.set(item.id, mesh);
    }
    this.select(objects[0]?.id ?? null);
  }

  private handlePointer(event: PointerEvent) {
    const rect = this.renderer.domElement.getBoundingClientRect();
    this.pointer.set(
      ((event.clientX - rect.left) / rect.width) * 2 - 1,
      -((event.clientY - rect.top) / rect.height) * 2 + 1
    );
    this.raycaster.setFromCamera(this.pointer, this.camera);
    const hits = this.raycaster.intersectObjects(this.assetRoot.children, false);
    this.select(hits[0]?.object.userData.id ?? null);
  }

  select(id: string | null) {
    this.selectedId = id && this.meshes.has(id) ? id : null;
    this.selectionListener(this.selectedId);
  }

  get selectedObject() {
    return this.selectedId ? this.meshes.get(this.selectedId) ?? null : null;
  }

  get objectCount() {
    return this.meshes.size;
  }

  moveSelected(axis: "x" | "y" | "z", amount: number) {
    const object = this.selectedObject;
    if (object) object.position[axis] = THREE.MathUtils.clamp(object.position[axis] + amount, -20, 20);
  }

  setSelectedColor(color: string) {
    const material = this.selectedObject?.material;
    if (material && !Array.isArray(material)) (material as THREE.MeshStandardMaterial).color.set(color);
  }

  setPlaying(value: boolean) {
    this.playing = value;
  }

  setAnimationPreset(preset: "idle" | "orbit" | "walk" | "run" | "jump" | "combo") {
    this.animationPreset = preset;
    this.animationTime = 0;
    for (const mesh of this.meshes.values()) {
      const position = mesh.userData.basePosition as [number, number, number] | undefined;
      const rotation = mesh.userData.baseRotation as [number, number, number, number] | undefined;
      if (position) mesh.position.set(...position);
      if (rotation) mesh.rotation.set(rotation[0], rotation[1], rotation[2]);
    }
  }

  snapshot(): SceneSnapshot {
    const objects: PlannedObject[] = Array.from(this.meshes.entries()).map(([id, mesh]) => ({
      id,
      name: mesh.name,
      kind: mesh.geometry.type.includes("Sphere") ? "sphere" :
        mesh.geometry.type.includes("Capsule") ? "capsule" :
        mesh.geometry.type.includes("Torus") ? "torus" :
        mesh.geometry.type.includes("Cylinder") ? "cylinder" :
        mesh.geometry.type.includes("Cone") ? "cone" : "box",
      color: "#" + (mesh.material as THREE.MeshStandardMaterial).color.getHexString(),
      position: [mesh.position.x, mesh.position.y, mesh.position.z],
      scale: [mesh.scale.x, mesh.scale.y, mesh.scale.z]
    }));
    return { version: 1, objects };
  }

  async exportGLB(): Promise<ArrayBuffer> {
    const exporter = new GLTFExporter();
    return new Promise((resolve, reject) => {
      exporter.parse(this.assetRoot, (result) => {
        if (result instanceof ArrayBuffer) resolve(result);
        else reject(new Error("The exporter did not return a binary GLB."));
      }, (error) => reject(error), { binary: true, onlyVisible: true });
    });
  }

  private animate = () => {
    this.animationFrame = requestAnimationFrame(this.animate);
    if (this.playing) {
      this.animationTime += 1 / 60;
      let index = 0;
      for (const mesh of this.meshes.values()) {
        const basePosition = mesh.userData.basePosition as [number, number, number] | undefined;
        const baseRotation = mesh.userData.baseRotation as [number, number, number, number] | undefined;
        if (!basePosition || !baseRotation) continue;
        const speed = this.animationPreset === "run" ? 13 : this.animationPreset === "walk" ? 6 : this.animationPreset === "combo" ? 9 : 2.2;
        const phase = this.animationTime * speed + index * 0.72;
        mesh.position.set(...basePosition);
        mesh.rotation.set(baseRotation[0], baseRotation[1], baseRotation[2]);
        if (this.animationPreset === "orbit") {
          mesh.rotation.y += this.animationTime * 0.35;
        } else if (this.animationPreset === "walk") {
          mesh.position.y += Math.abs(Math.sin(phase * 2)) * 0.08;
          mesh.rotation.x += Math.sin(phase) * 0.28;
        } else if (this.animationPreset === "run") {
          mesh.position.y += Math.abs(Math.sin(phase * 2)) * 0.16;
          mesh.rotation.x += Math.sin(phase) * 0.52;
        } else if (this.animationPreset === "jump") {
          mesh.position.y += Math.max(0, Math.sin((this.animationTime % 1.2) / 1.2 * Math.PI)) * 0.95;
          mesh.rotation.x += Math.sin(phase) * 0.08;
        } else if (this.animationPreset === "combo") {
          mesh.position.y += Math.abs(Math.sin(phase * 1.7)) * 0.22;
          mesh.rotation.y += Math.sin(phase) * 0.62;
          mesh.rotation.x += Math.cos(phase * 1.3) * 0.34;
          mesh.position.x += Math.sin(phase * 0.55) * 0.12;
        } else {
          mesh.position.y += Math.abs(Math.sin(phase)) * 0.035;
          mesh.rotation.y += Math.sin(phase) * 0.06;
        }
        index++;
      }
    }
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  };

  dispose() {
    cancelAnimationFrame(this.animationFrame);
    this.resizeObserver.disconnect();
    this.renderer.domElement.removeEventListener("pointerdown", this.onPointerDown);
    this.controls.dispose();
    for (const mesh of this.meshes.values()) {
      mesh.geometry.dispose();
      const material = mesh.material;
      if (Array.isArray(material)) material.forEach((item) => item.dispose());
      else material.dispose();
    }
    this.renderer.dispose();
    this.renderer.domElement.remove();
  }
}