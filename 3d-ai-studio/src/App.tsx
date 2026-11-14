import { useEffect, useRef, useState } from "react";
import { planScene, type PrimitiveKind, type ScenePlan } from "./core/ScenePlanner";
import { SceneBrain, type ScenePrediction } from "./core/SceneBrain";
import type { SceneSnapshot } from "./engine/StudioViewport";
import { StudioViewport } from "./engine/StudioViewport";

type Page = "scene" | "ai" | "animation";
type AnimationPreset = "idle" | "orbit" | "walk" | "run" | "jump" | "combo";

function download(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function App() {
  const hostRef = useRef<HTMLDivElement>(null);
  const viewportRef = useRef<StudioViewport | null>(null);
  const brainRef = useRef<SceneBrain | null>(null);
  const [page, setPage] = useState<Page>("scene");
  const [ready, setReady] = useState(false);
  const [modelReady, setModelReady] = useState(false);
  const [modelError, setModelError] = useState("");
  const [modelMetrics, setModelMetrics] = useState({ samples: 0, epochs: 0, validationAccuracy: 0, categories: 0, vocabulary: 0 });
  const [prediction, setPrediction] = useState<ScenePrediction | null>(null);
  const [prompt, setPrompt] = useState("Crie uma floresta com árvores altas, pedras e um caminho");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [objectCount, setObjectCount] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [animation, setAnimation] = useState<AnimationPreset>("idle");
  const [color, setColor] = useState("#6f8cff");
  const [projectName, setProjectName] = useState("Minha cena");
  const [notice, setNotice] = useState("Motor 3D inicializando…");

  useEffect(() => {
    if (!hostRef.current) return;
    try {
      const viewport = new StudioViewport(hostRef.current, id => setSelectedId(id));
      viewportRef.current = viewport;
      viewport.addPrimitive("box", "Objeto inicial", "#6f8cff");
      setObjectCount(viewport.objectCount);
      setReady(true);
      setNotice("Motor 3D pronto.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Falha ao iniciar o motor 3D.");
    }
    return () => {
      viewportRef.current?.dispose();
      viewportRef.current = null;
    };
  }, []);

  useEffect(() => {
    let active = true;
    SceneBrain.load().then(brain => {
      if (!active) return;
      brainRef.current = brain;
      setModelMetrics(brain.metrics);
      setModelReady(true);
      setNotice("Modelo neural treinado carregado.");
    }).catch(error => {
      if (!active) return;
      setModelError(error instanceof Error ? error.message : "Modelo treinado indisponível.");
    });
    return () => { active = false; };
  }, []);

  const refreshCount = () => setObjectCount(viewportRef.current?.objectCount ?? 0);

  const addObject = (kind: PrimitiveKind) => {
    viewportRef.current?.addPrimitive(kind);
    refreshCount();
    setNotice("Objeto adicionado.");
  };

  const applyAnimation = (preset: AnimationPreset) => {
    setAnimation(preset);
    viewportRef.current?.setAnimationPreset(preset);
    viewportRef.current?.setPlaying(true);
    setPlaying(true);
  };

  const generate = () => {
    const learned = brainRef.current?.predict(prompt) ?? null;
    setPrediction(learned);
    const plan: ScenePlan = planScene(prompt, learned?.category);
    viewportRef.current?.replaceScene(plan.objects);
    const preset: AnimationPreset = plan.animation === "action" ? "combo" : plan.animation;
    viewportRef.current?.setAnimationPreset(preset);
    viewportRef.current?.setPlaying(false);
    setAnimation(preset);
    setPlaying(false);
    setProjectName(plan.title);
    refreshCount();
    setPage("scene");
    setNotice(learned
      ? "IA classificou a cena como " + learned.category + " (" + Math.round(learned.confidence * 100) + "%) e construiu " + plan.objects.length + " objetos."
      : "Modelo neural indisponível; cena criada pelo planejador de regras.");
  };

  const move = (axis: "x" | "y" | "z", amount: number) => {
    viewportRef.current?.moveSelected(axis, amount);
    setNotice("Transformação aplicada.");
  };

  const save = () => {
    const scene = viewportRef.current?.snapshot();
    if (!scene) return;
    const content = JSON.stringify({ app: "3D AI Studio", version: 2, name: projectName, savedAt: new Date().toISOString(), scene }, null, 2);
    localStorage.setItem("three-d-ai-studio-project", content);
    download(new Blob([content], { type: "application/json" }), "3d-ai-studio-project.json");
    setNotice("Projeto salvo e exportado.");
  };

  const load = (file?: File) => {
    if (!file) return;
    file.text().then(content => {
      const data = JSON.parse(content) as { name?: string; scene?: SceneSnapshot };
      if (data.scene?.version !== 1 || !Array.isArray(data.scene.objects)) throw new Error("Arquivo de projeto inválido.");
      viewportRef.current?.replaceScene(data.scene.objects);
      setProjectName(data.name ?? "Projeto importado");
      refreshCount();
      setNotice("Projeto importado.");
    }).catch(error => setNotice(error instanceof Error ? error.message : "Falha ao importar."));
  };

  const exportGlb = async () => {
    try {
      const result = await viewportRef.current?.exportGLB();
      if (result) download(new Blob([result], { type: "model/gltf-binary" }), "3d-ai-studio.glb");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Falha ao exportar GLB.");
    }
  };

  const togglePlayback = () => {
    const next = !playing;
    viewportRef.current?.setPlaying(next);
    setPlaying(next);
  };

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand"><span className="brand-mark">3D</span><span><b>AI STUDIO</b><small>CREATE · LEARN · ANIMATE</small></span></div>
        <div className="top-actions">
          <span className={"engine-state " + (ready ? "online" : "")}>{ready ? "ENGINE READY" : "STARTING"}</span>
          <button className="button ghost" onClick={save}>Salvar</button>
          <button className="button primary" onClick={exportGlb}>Exportar GLB</button>
        </div>
      </header>

      <nav className="main-nav" aria-label="Navegação principal">
        <button className={page === "scene" ? "active" : ""} onClick={() => setPage("scene")}><span>◈</span>Cena</button>
        <button className={page === "ai" ? "active" : ""} onClick={() => setPage("ai")}><span>✦</span>IA Criadora</button>
        <button className={page === "animation" ? "active" : ""} onClick={() => setPage("animation")}><span>▶</span>Animação</button>
      </nav>

      <section className="content">
        {page === "scene" && (
          <>
            <div className="section-heading"><div><p className="eyebrow">PROJETO ATUAL</p><h1>{projectName}</h1><p className="subheading">Monte sua cena e edite os objetos diretamente na viewport.</p></div><span className="count-pill">{objectCount} objetos</span></div>
            <div className="editor">
              <section className="viewport-card">
                <div className="viewport-head"><span><i className="live-dot" /> VISUALIZAÇÃO 3D</span><div><button className="icon-button" onClick={togglePlayback}>{playing ? "Ⅱ" : "▶"}</button><button className="icon-button" onClick={exportGlb}>⇩</button></div></div>
                <div className="viewport-stage" ref={hostRef}>{!ready && <div className="loading">Iniciando renderizador 3D…</div>}</div>
                <div className="object-actions">
                  <button onClick={() => addObject("box")}>＋ Cubo</button>
                  <button onClick={() => addObject("sphere")}>＋ Esfera</button>
                  <button onClick={() => addObject("capsule")}>＋ Personagem</button>
                  <button onClick={() => addObject("cylinder")}>＋ Cilindro</button>
                  <button onClick={() => addObject("cone")}>＋ Cone</button>
                  <button onClick={() => addObject("torus")}>＋ Anel</button>
                </div>
              </section>
              <aside className="inspector">
                <div className="panel-title">PROPRIEDADES</div>
                <div className="selected-object"><span className="object-icon">◇</span><span><b>{selectedId ? "Objeto selecionado" : "Nenhum objeto"}</b><small>{selectedId ?? "Toque em um objeto 3D"}</small></span></div>
                <div className="property-group"><label>POSIÇÃO</label>{(["x","y","z"] as const).map(axis => <div className="axis-row" key={axis}><b className={"axis-" + axis}>{axis.toUpperCase()}</b><button disabled={!selectedId} onClick={() => move(axis,-0.25)}>−</button><button disabled={!selectedId} onClick={() => move(axis,0.25)}>＋</button></div>)}</div>
                <div className="property-group"><label>MATERIAL</label><div className="color-picker"><span>Cor base</span><input type="color" value={color} onChange={event => { setColor(event.target.value); viewportRef.current?.setSelectedColor(event.target.value); }} /></div><div className="swatches">{["#6f8cff","#3dd6c6","#a98cff","#ffb86b","#f079a8"].map(value => <button key={value} style={{background:value}} onClick={() => {setColor(value);viewportRef.current?.setSelectedColor(value);}} />)}</div></div>
                <div className="property-group"><label>ANIMAÇÃO RÁPIDA</label><button className="wide-button" onClick={() => applyAnimation("idle")}>Reproduzir movimento suave</button></div>
                <div className="inspector-foot"><i className="live-dot" /> {ready ? "Renderizador ativo" : "Carregando motor"}</div>
              </aside>
            </div>
          </>
        )}

        {page === "ai" && (
          <div className="ai-page">
            <div className="section-heading"><div><p className="eyebrow">MODELO TREINADO NA SANDBOX</p><h1>O que vamos criar?</h1><p className="subheading">A rede neural classifica a intenção em seis categorias e o construtor gera uma cena 3D editável.</p></div><span className={"model-pill " + (modelReady ? "online" : "")}>{modelReady ? "MODELO CARREGADO" : "MODELO PENDENTE"}</span></div>
            <div className="ai-card">
              <textarea value={prompt} onChange={event => setPrompt(event.target.value)} placeholder="Descreva uma cena, personagem, veículo ou ambiente…" rows={5} />
              <div className="prompt-examples">{["Uma floresta com árvores e pedras","Um carro esportivo futurista","Dois personagens em uma arena","Uma sala moderna com mesa e cadeiras"].map(value => <button key={value} onClick={() => setPrompt(value)}>{value}</button>)}</div>
              <button className="button primary generate-button" disabled={!ready} onClick={generate}>✦ Gerar cena 3D</button>
              {modelError && <p className="model-error">{modelError} A cena ainda pode ser criada pelo modo de regras.</p>}
            </div>
            <div className="model-stats">
              <div><b>{modelMetrics.samples || "—"}</b><span>exemplos de treino</span></div>
              <div><b>{modelMetrics.epochs || "—"}</b><span>épocas</span></div>
              <div><b>{Math.round(modelMetrics.validationAccuracy * 100) || 0}%</b><span>validação sandbox</span></div>
              <div><b>{modelMetrics.categories || "—"}</b><span>categorias aprendidas</span></div>
            </div>
            {prediction && <div className="prediction-card"><span>ÚLTIMA PREDIÇÃO</span><b>{prediction.category}</b><strong>{Math.round(prediction.confidence * 100)}% confiança</strong><small>Classificação do modelo; a geometria é construída pelo gerador procedural.</small></div>}
            <p className="honesty-note">O modelo foi treinado do zero em exemplos sintéticos multilíngues. Ele aprende classificação de intenção; não é um LLM nem gera malhas complexas livremente.</p>
          </div>
        )}

        {page === "animation" && (
          <div className="animation-page">
            <div className="section-heading"><div><p className="eyebrow">MOTION LAB</p><h1>Animações</h1><p className="subheading">Escolha movimentos simples ou sequências avançadas para a cena atual.</p></div><span className="count-pill">{playing ? "Reproduzindo" : "Pausado"}</span></div>
            <div className="animation-grid">
              <button className={animation === "idle" ? "chosen" : ""} onClick={() => applyAnimation("idle")}><b>01</b><strong>Idle</strong><span>Respiração e movimento sutil</span></button>
              <button className={animation === "orbit" ? "chosen" : ""} onClick={() => applyAnimation("orbit")}><b>02</b><strong>Orbit</strong><span>Rotação contínua dos objetos</span></button>
              <button className={animation === "walk" ? "chosen" : ""} onClick={() => applyAnimation("walk")}><b>03</b><strong>Walk</strong><span>Oscilação de caminhada</span></button>
              <button className={animation === "run" ? "chosen" : ""} onClick={() => applyAnimation("run")}><b>04</b><strong>Run</strong><span>Passos rápidos e impacto</span></button>
              <button className={animation === "jump" ? "chosen" : ""} onClick={() => applyAnimation("jump")}><b>05</b><strong>Jump</strong><span>Salto com arco vertical</span></button>
              <button className={animation === "combo" ? "chosen" : ""} onClick={() => applyAnimation("combo")}><b>06</b><strong>Combo avançado</strong><span>Sequência combinada de rotação e deslocamento</span></button>
            </div>
            <div className="animation-controls"><button className="button primary" onClick={togglePlayback}>{playing ? "Ⅱ Pausar" : "▶ Reproduzir"}</button><span>Prévia procedural em tempo real · {objectCount} objetos</span></div>
            <p className="honesty-note">Esses são movimentos procedurais de prévia. Rigging humano, captura de movimento e curvas keyframe por osso serão etapas posteriores.</p>
          </div>
        )}
      </section>

      <footer className="statusbar"><span>{notice}</span><label className="import-button">Importar projeto<input type="file" accept="application/json,.json" onChange={event => load(event.target.files?.[0])} /></label></footer>
    </main>
  );
}

export default App;
