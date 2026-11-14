import { useEffect, useMemo, useRef, useState } from "react";
import { LANGUAGE_PROFILES, detectLanguage, inspectLanguage, type LanguageCode } from "./core/LanguageRouter";
import { UnicodeTokenizer } from "./core/UnicodeTokenizer";
import { formatParameterCount, ProceduralNeuralNetwork } from "./core/ProceduralNetwork";
import { planScene } from "./core/ScenePlanner";
import type { SceneSnapshot } from "./engine/StudioViewport";
import { StudioViewport } from "./engine/StudioViewport";

type Panel = "studio" | "generate" | "language" | "neural";
const tokenizer = new UnicodeTokenizer();

function downloadBlob(blob: Blob, filename: string) {
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
  const networkRef = useRef(new ProceduralNeuralNetwork());
  const [panel, setPanel] = useState<Panel>("studio");
  const [ready, setReady] = useState(false);
  const [webglError, setWebglError] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [objectCount, setObjectCount] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [prompt, setPrompt] = useState("Crie uma pequena cena de luta com dois personagens e um anel de energia");
  const [language, setLanguage] = useState<LanguageCode>("pt");
  const [languageText, setLanguageText] = useState("Olá! Vamos criar uma cena 3D com inteligência artificial.");
  const [trainingText, setTrainingText] = useState("O personagem entra na arena, observa o adversário e prepara o próximo movimento.");
  const [trainingMessage, setTrainingMessage] = useState("O núcleo ainda não foi adaptado a nenhum texto.");
  const [trainingBusy, setTrainingBusy] = useState(false);
  const [notice, setNotice] = useState("Projeto local pronto para edição.");
  const [color, setColor] = useState("#6f8cff");
  const [projectName, setProjectName] = useState("Minha primeira cena");

  const stats = useMemo(() => networkRef.current.getStats(), [trainingMessage]);
  const languageInfo = useMemo(() => inspectLanguage(languageText, language), [languageText, language]);
  const tokenInfo = useMemo(() => tokenizer.describe(languageText, language), [languageText, language]);
  const detected = detectLanguage(languageText);

  useEffect(() => {
    if (!hostRef.current) return;
    try {
      const viewport = new StudioViewport(hostRef.current, (id) => setSelectedId(id));
      viewportRef.current = viewport;
      viewport.addPrimitive("box", "Objeto principal", "#6f8cff");
      viewport.addPrimitive("sphere", "Objeto secundário", "#3dd6c6");
      setObjectCount(viewport.objectCount);
      setReady(true);
    } catch (error) {
      setWebglError(error instanceof Error ? error.message : "Não foi possível iniciar o renderizador 3D.");
    }
    return () => {
      viewportRef.current?.dispose();
      viewportRef.current = null;
    };
  }, []);

  const updateCount = () => setObjectCount(viewportRef.current?.objectCount ?? 0);

  const addObject = (kind: "box" | "sphere" | "capsule" | "torus") => {
    viewportRef.current?.addPrimitive(kind);
    updateCount();
    setNotice("Objeto adicionado à cena.");
  };

  const generateScene = () => {
    const plan = planScene(prompt);
    viewportRef.current?.replaceScene(plan.objects);
    viewportRef.current?.setPlaying(false);
    setPlaying(false);
    setProjectName(plan.title || "Cena gerada");
    updateCount();
    setPanel("studio");
    setNotice(plan.explanation);
  };

  const togglePlayback = () => {
    const next = !playing;
    setPlaying(next);
    viewportRef.current?.setPlaying(next);
  };

  const move = (axis: "x" | "y" | "z", amount: number) => {
    viewportRef.current?.moveSelected(axis, amount);
    setNotice("Transformação aplicada.");
  };

  const saveProject = () => {
    const snapshot = viewportRef.current?.snapshot();
    if (!snapshot) return;
    const payload = {
      app: "3D AI Studio",
      version: 1,
      name: projectName,
      savedAt: new Date().toISOString(),
      scene: snapshot
    };
    const serialized = JSON.stringify(payload, null, 2);
    localStorage.setItem("three-d-ai-studio-project", serialized);
    downloadBlob(new Blob([serialized], { type: "application/json" }), "3d-ai-studio-project.json");
    setNotice("Projeto salvo no dispositivo e exportado como JSON.");
  };

  const loadProject = (file?: File) => {
    if (!file) return;
    file.text().then((content) => {
      const parsed = JSON.parse(content) as { name?: string; scene?: SceneSnapshot };
      if (parsed.scene?.version !== 1 || !Array.isArray(parsed.scene.objects)) throw new Error("Formato de projeto inválido.");
      viewportRef.current?.replaceScene(parsed.scene.objects);
      setProjectName(parsed.name ?? "Projeto importado");
      updateCount();
      setNotice("Projeto importado.");
    }).catch((error: unknown) => setNotice(error instanceof Error ? error.message : "Falha ao importar o projeto."));
  };

  const exportGLB = async () => {
    try {
      const result = await viewportRef.current?.exportGLB();
      if (result) {
        downloadBlob(new Blob([result], { type: "model/gltf-binary" }), "3d-ai-studio-scene.glb");
        setNotice("Arquivo GLB exportado.");
      }
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Falha ao exportar GLB.");
    }
  };

  const exportImage = () => {
    const canvas = hostRef.current?.querySelector("canvas");
    if (!canvas) return;
    canvas.toBlob((blob) => {
      if (blob) downloadBlob(blob, "3d-ai-studio-preview.png");
    }, "image/png");
    setNotice("Prévia PNG exportada.");
  };

  const trainNetwork = () => {
    setTrainingBusy(true);
    window.setTimeout(() => {
      try {
        const result = networkRef.current.trainText(trainingText, 2, 0.06);
        const prediction = networkRef.current.predictNextByte(trainingText);
        setTrainingMessage(
          result.steps + " etapas concluídas · perda " + result.loss.toFixed(3) +
          " · próximo byte estimado: " + JSON.stringify(prediction.character)
        );
      } catch (error) {
        setTrainingMessage(error instanceof Error ? error.message : "Falha no treinamento.");
      } finally {
        setTrainingBusy(false);
      }
    }, 20);
  };

  const rebuildNetwork = () => {
    networkRef.current = networkRef.current.reset(Math.floor(Math.random() * 2_000_000_000));
    setTrainingMessage("Núcleo reconstruído com nova semente. O estado de treinamento anterior foi descartado.");
  };

  const selectedLabel = selectedId ? "Objeto selecionado" : "Nenhum objeto selecionado";

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <div className="brand-mark">3D</div>
          <div><div className="brand-name">AI STUDIO</div><div className="brand-caption">CREATE · ANIMATE · DIRECT</div></div>
        </div>
        <div className="topbar-center"><span className="status-dot" /> LOCAL ENGINE <span className="topbar-separator">/</span> ALPHA 0.1</div>
        <div className="topbar-actions">
          <button className="button button-quiet button-small" onClick={saveProject}>Salvar</button>
          <button className="button button-primary button-small" onClick={exportGLB}>Exportar GLB</button>
        </div>
      </header>

      <div className="workspace">
        <nav className="sidebar" aria-label="Ferramentas do estúdio">
          <div className="sidebar-label">WORKSPACE</div>
          {([
            ["studio", "◈", "Estúdio"],
            ["generate", "✦", "Gerar cena"],
            ["language", "文", "Idiomas"],
            ["neural", "⌘", "Neural Core"]
          ] as const).map(([id, icon, label]) => (
            <button key={id} className={"nav-item " + (panel === id ? "active" : "")} onClick={() => setPanel(id)}>
              <span className="nav-icon">{icon}</span><span>{label}</span>
            </button>
          ))}
          <div className="sidebar-spacer" />
          <div className="sidebar-foot"><span className="live-pip" /><span>Offline ready</span></div>
        </nav>

        <section className="main-panel">
          <div className="page-heading">
            <div>
              <div className="eyebrow">3D WORKSPACE / PROJECT 001</div>
              <h1>{panel === "studio" ? "Studio workspace" : panel === "generate" ? "Scene generator" : panel === "language" ? "Multilingual tokenizer" : "Procedural neural core"}</h1>
              <p>{panel === "studio" ? "Construa e ajuste objetos em uma viewport 3D real." : panel === "generate" ? "Transforme uma descrição em uma cena procedural editável." : panel === "language" ? "Codificação Unicode e seleção de escrita por idioma." : "Rede expansível com pesos gerados por semente e adaptação local."}</p>
            </div>
            <div className="project-pill"><span className="project-pill-dot" /> {projectName}</div>
          </div>

          {panel === "studio" && (
            <div className="studio-layout">
              <div className="viewport-column">
                <div className="viewport-toolbar">
                  <div className="viewport-mode"><span className="mode-indicator" /> PERSPECTIVE <span className="toolbar-divider" /> REAL-TIME VIEWPORT</div>
                  <div className="toolbar-actions">
                    <button className="icon-button" title="Exportar imagem PNG" onClick={exportImage}>▧</button>
                    <button className={"icon-button " + (playing ? "selected" : "")} title="Reproduzir animação" onClick={togglePlayback}>{playing ? "Ⅱ" : "▶"}</button>
                  </div>
                </div>
                <div className="viewport-stage" ref={hostRef}>
                  {!ready && !webglError && <div className="viewport-overlay">Inicializando motor 3D…</div>}
                  {webglError && <div className="viewport-overlay error">{webglError}<br />Verifique o suporte WebGL do dispositivo.</div>}
                </div>
                <div className="viewport-footer"><span>{objectCount} OBJECTS</span><span>WEBGL RENDERER</span><span>{playing ? "PLAYING" : "PAUSED"}</span></div>
                <div className="object-toolbar">
                  <span className="toolbar-title">ADD OBJECT</span>
                  <button onClick={() => addObject("box")}>＋ Cube</button>
                  <button onClick={() => addObject("sphere")}>＋ Sphere</button>
                  <button onClick={() => addObject("capsule")}>＋ Character</button>
                  <button onClick={() => addObject("torus")}>＋ Ring</button>
                </div>
              </div>
              <aside className="inspector">
                <div className="inspector-header"><span>INSPECTOR</span><span className="inspector-dots">•••</span></div>
                <div className="inspector-section">
                  <div className="section-label">SELECTION</div>
                  <div className="selection-card"><span className="selection-glyph">◇</span><div><strong>{selectedLabel}</strong><small>{selectedId ? selectedId.slice(0, 18) : "Toque em um objeto na viewport"}</small></div></div>
                </div>
                <div className="inspector-section">
                  <div className="section-label">TRANSFORM</div>
                  {(["x", "y", "z"] as const).map((axis) => (
                    <div className="transform-row" key={axis}>
                      <span className={"axis axis-" + axis}>{axis.toUpperCase()}</span>
                      <button disabled={!selectedId} onClick={() => move(axis, -0.25)}>−</button>
                      <button disabled={!selectedId} onClick={() => move(axis, 0.25)}>＋</button>
                    </div>
                  ))}
                </div>
                <div className="inspector-section">
                  <div className="section-label">MATERIAL</div>
                  <div className="color-row"><span>Base color</span><input type="color" value={color} onChange={(event) => { setColor(event.target.value); viewportRef.current?.setSelectedColor(event.target.value); }} /></div>
                  <div className="swatches">
                    {["#6f8cff", "#3dd6c6", "#a98cff", "#ffb86b", "#f079a8"].map((value) => <button key={value} style={{ background: value }} aria-label={"Cor " + value} onClick={() => { setColor(value); viewportRef.current?.setSelectedColor(value); }} />)}
                  </div>
                </div>
                <div className="inspector-section">
                  <div className="section-label">PREVIEW LOOP</div>
                  <div className="timeline-track"><span className="timeline-fill" /><span className="timeline-marker" /></div>
                  <div className="timeline-meta"><span>LIVE</span><span>LOOP</span></div>
                  <button className="button button-outline full-width" onClick={togglePlayback}>{playing ? "Pausar" : "Reproduzir"} cena</button>
                </div>
                <div className="inspector-bottom"><span className="live-pip" /> {ready ? "Engine ready" : "Starting engine"}</div>
              </aside>
            </div>
          )}

          {panel === "generate" && (
            <div className="content-card generator-card">
              <div className="card-kicker">TEXT TO SCENE <span>LOCAL PROCEDURAL PLANNER</span></div>
              <h2>Descreva o mundo que deseja criar.</h2>
              <p>O planejador identifica categorias de cena e monta geometrias editáveis. Nesta versão, a geração é local e baseada em regras; não usa um modelo generativo pré-treinado.</p>
              <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} rows={5} placeholder="Ex.: uma cidade futurista com três edifícios..." />
              <div className="prompt-suggestions">
                {["Uma floresta com árvores", "Uma cidade futurista", "Uma luta com dois personagens"].map((value) => <button key={value} onClick={() => setPrompt(value)}>{value}</button>)}
              </div>
              <button className="button button-primary button-large" onClick={generateScene}>✦ Construir cena 3D</button>
              <div className="feature-grid">
                <div><strong>01</strong><span>Interpretar prompt</span></div>
                <div><strong>02</strong><span>Montar geometrias</span></div>
                <div><strong>03</strong><span>Editar na viewport</span></div>
              </div>
            </div>
          )}

          {panel === "language" && (
            <div className="content-card language-card">
              <div className="card-kicker">UNICODE PROCESSING <span>BYTE TOKENIZER V1</span></div>
              <h2>Seis idiomas. Uma camada Unicode.</h2>
              <p>Selecione o idioma manualmente ou compare com a detecção heurística. A codificação UTF-8 mantém caracteres e sinais combinantes intactos.</p>
              <div className="language-controls">
                <label>Idioma de processamento
                  <select value={language} onChange={(event) => setLanguage(event.target.value as LanguageCode)}>
                    {Object.values(LANGUAGE_PROFILES).map((item) => <option key={item.code} value={item.code}>{item.nativeLabel} · {item.label}</option>)}
                  </select>
                </label>
                <div className="detected-chip">Detectado: <strong>{LANGUAGE_PROFILES[detected].nativeLabel}</strong></div>
              </div>
              <textarea dir={languageInfo.direction} value={languageText} onChange={(event) => setLanguageText(event.target.value)} rows={4} placeholder="Digite texto para codificar..." />
              <div className="language-metrics">
                <div><strong>{tokenInfo.glyphs.length}</strong><span>graphemes</span></div>
                <div><strong>{tokenInfo.utf8Bytes}</strong><span>UTF-8 bytes</span></div>
                <div><strong>{tokenInfo.tokenCount}</strong><span>tokens</span></div>
                <div><strong>{languageInfo.direction.toUpperCase()}</strong><span>direction</span></div>
              </div>
              <div className="glyph-table">
                <div className="glyph-table-head"><span>GLYPH</span><span>UNICODE / GLYPH ID</span><span>SCRIPT</span><span>TOKENS</span></div>
                {tokenInfo.glyphs.slice(0, 16).map((glyph, index) => (
                  <div className="glyph-row" key={glyph.code + index}><strong>{glyph.text}</strong><code>{glyph.code}</code><span>{glyph.script}</span><span>{glyph.tokenIds.length}</span></div>
                ))}
              </div>
              <div className="notice-line">Round-trip check: <strong>{tokenInfo.roundTrip === languageText.normalize("NFC") ? "PASS" : "NORMALIZED"}</strong> · UTF-8 byte fallback ativo</div>
            </div>
          )}

          {panel === "neural" && (
            <div className="content-card neural-card">
              <div className="card-kicker">PROCEDURAL MODEL <span>SEEDED WEIGHT FIELD</span></div>
              <h2>Atlas procedural core</h2>
              <p>Uma arquitetura de grande capacidade estrutural gera pesos de forma determinística e calcula apenas uma faixa ativa reduzida no dispositivo.</p>
              <div className="neural-hero">
                <div className="neural-orb"><span>AI</span></div>
                <div><div className="eyebrow">VIRTUAL PARAMETER SPACE</div><div className="neural-number">{formatParameterCount(stats.virtualParameterCount)}</div><span className="muted">parâmetros definidos pela arquitetura</span></div>
              </div>
              <div className="neural-metrics">
                <div><strong>{stats.depth}</strong><span>layers</span></div>
                <div><strong>{stats.hiddenSize}</strong><span>hidden size</span></div>
                <div><strong>{stats.activeWidth}</strong><span>active width</span></div>
                <div><strong>{formatParameterCount(stats.trainableParameterCount)}</strong><span>trainable head</span></div>
              </div>
              <div className="training-block">
                <div className="section-label">LOCAL ADAPTATION DATA</div>
                <textarea value={trainingText} onChange={(event) => setTrainingText(event.target.value)} rows={4} placeholder="Insira texto de treinamento..." />
                <div className="training-actions">
                  <button className="button button-primary" disabled={trainingBusy} onClick={trainNetwork}>{trainingBusy ? "Treinando…" : "Treinar readout local"}</button>
                  <button className="button button-outline" onClick={rebuildNetwork}>Reconstruir semente</button>
                </div>
                <div className="training-result">{trainingMessage}</div>
              </div>
              <div className="warning-note">Transparência: os pesos procedurais começam sem conhecimento pré-treinado. O treino desta versão atualiza apenas a camada de saída com o texto fornecido. A contagem virtual não representa memória alocada nem um modelo de centenas de milhões de pesos materializados.</div>
            </div>
          )}

          <div className="statusbar"><span>{notice}</span><span>{objectCount} objects · autosave local disponível</span></div>
        </section>
      </div>

      <input className="hidden-input" type="file" accept="application/json,.json" id="project-import" onChange={(event) => loadProject(event.target.files?.[0])} />
      <label htmlFor="project-import" className="floating-import">Importar projeto</label>
    </main>
  );
}

export default App;