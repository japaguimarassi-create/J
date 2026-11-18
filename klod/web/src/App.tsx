import { useState } from "react";
import { ArrowUp, Menu, Plus, Search, Settings2, Sparkles, Paperclip, Code2 } from "lucide-react";

type Message = { role: "user" | "assistant"; content: string };

export default function App() {
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [sidebar, setSidebar] = useState(false);
  const [mode, setMode] = useState("Conversação");

  function send() {
    const value = draft.trim();
    if (!value) return;
    setMessages((old) => [...old, { role: "user", content: value }, { role: "assistant", content: "A interface está ativa. O motor de inferência ainda não foi habilitado: nenhum checkpoint treinado e aprovado está instalado." }]);
    setDraft("");
  }

  return <main className="shell">
    <aside className={sidebar ? "sidebar open" : "sidebar"}>
      <div className="brand"><b>K</b><span>Klod</span><button className="icon" onClick={() => setSidebar(false)} aria-label="Fechar menu">×</button></div>
      <button className="new" onClick={() => setMessages([])}><Plus size={17}/> Nova conversa</button>
      <p className="label">ESPAÇO DE TRABALHO</p>
      <button className={mode === "Conversação" ? "nav active" : "nav"} onClick={() => setMode("Conversação")}><Sparkles size={17}/> Conversação</button>
      <button className={mode === "Desenvolvimento" ? "nav active" : "nav"} onClick={() => setMode("Desenvolvimento")}><Code2 size={17}/> Desenvolvimento</button>
      <div className="status"><i/> Modelo experimental não treinado <Settings2 size={16}/></div>
    </aside>
    {sidebar && <button className="scrim" onClick={() => setSidebar(false)} aria-label="Fechar navegação"/>}
    <section className="main">
      <header><button className="icon menu" onClick={() => setSidebar(!sidebar)} aria-label="Abrir navegação"><Menu size={20}/></button><strong>Klod</strong><small>Experimental</small><button className="icon search" aria-label="Pesquisar"><Search size={18}/></button></header>
      <div className="conversation">
        {messages.length === 0 ? <div className="welcome"><div className="orb"><Sparkles size={25}/></div><p className="eyebrow">INTELIGÊNCIA EM CONSTRUÇÃO</p><h1>O que vamos<br/><em>construir</em> hoje?</h1><p className="sub">Um espaço para raciocinar, pesquisar e desenvolver projetos.</p><div className="suggestions"><button onClick={() => setMode("Desenvolvimento")}><Code2 size={17}/> Analisar um projeto <span>→</span></button><button onClick={() => setDraft("Explique um problema complexo passo a passo")}><Sparkles size={17}/> Explorar uma ideia <span>→</span></button></div></div> : <div className="messages">{messages.map((m, i) => <article className={"message " + m.role} key={i}><b>{m.role === "user" ? "Você" : "Klod"}</b><p>{m.content}</p></article>)}</div>}
      </div>
      <div className="composer-wrap"><div className="composer"><textarea value={draft} onChange={(e) => setDraft(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }} placeholder={mode === "Conversação" ? "Pergunte qualquer coisa..." : "Descreva o que deseja desenvolver..."} rows={2}/><div className="actions"><button className="icon" aria-label="Anexar arquivo"><Paperclip size={18}/></button><span>Shift + Enter para nova linha</span><button className="send" onClick={send} disabled={!draft.trim()} aria-label="Enviar mensagem"><ArrowUp size={19}/></button></div></div><p className="disclaimer">Klod está em desenvolvimento. As respostas não são geradas por um modelo treinado.</p></div>
    </section>
  </main>;
}
