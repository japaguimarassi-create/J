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

  snapshot(): SceneSnapshot {
    const objects: PlannedObject[] = Array.from(this.meshes.entries()).map(([id, mesh]) => ({
      id,
      name: mesh.name,
      kind: mesh.geometry.type.includes("Sphere") ? "sphere" :
        mesh.geometry.type.includes("Capsule") ? "capsule" :
        mesh.geometry.type.includes("Torus") ? "torus" : "box",
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
      for (const mesh of this.meshes.values()) mesh.rotation.y += 0.004;
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