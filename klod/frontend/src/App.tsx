import { type FormEvent, useEffect, useRef, useState } from 'react'

type Message = { id: string; role: 'user' | 'assistant'; content: string }
const apiBase = (import.meta.env.VITE_KLOD_API_URL || '').replace(/\/$/, '')

export default function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [draft, setDraft] = useState('')
  const [loading, setLoading] = useState(false)
  const [online, setOnline] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const input = useRef<HTMLTextAreaElement>(null)
  useEffect(() => {
    let active = true
    fetch(apiBase + '/health').then((response) => { if (!response.ok) throw new Error(); return response.json() }).then(() => active && setOnline(true)).catch(() => active && setOnline(false))
    return () => { active = false }
  }, [])
  async function send(event: FormEvent) {
    event.preventDefault()
    const content = draft.trim()
    if (!content || loading) return
    setMessages((items) => [...items, { id: crypto.randomUUID(), role: 'user', content }])
    setDraft('')
    setLoading(true)
    try {
      const response = await fetch(apiBase + '/v1/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: content }) })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(data.detail || ('HTTP ' + response.status))
      setMessages((items) => [...items, { id: crypto.randomUUID(), role: 'assistant', content: data.response || 'O modelo não retornou conteúdo.' }])
    } catch (error) {
      const reason = error instanceof Error ? error.message : 'Falha de conexão'
      setMessages((items) => [...items, { id: crypto.randomUUID(), role: 'assistant', content: 'Não foi possível gerar uma resposta real do modelo. ' + reason }])
    } finally { setLoading(false); input.current?.focus() }
  }
  return <div className="shell">
    <aside className={menuOpen ? 'sidebar open' : 'sidebar'}><div className="brand"><b>K</b><span>KLOD</span><button className="close" onClick={() => setMenuOpen(false)}>×</button></div><button className="new-chat" onClick={() => { setMessages([]); setMenuOpen(false) }}>＋ Nova conversa</button><label>ESPAÇO DE TRABALHO</label><button className="nav active">◌　Conversas</button><button className="nav" disabled>▧　Projetos <small>em breve</small></button><button className="nav" disabled>⌘　Desenvolvimento <small>em breve</small></button><div className="status"><i className={online ? 'on' : ''}/>{online ? 'API conectada' : 'API indisponível'}<small>v0.1</small></div></aside>
    {menuOpen && <button className="scrim" onClick={() => setMenuOpen(false)} aria-label="Fechar menu"/>}
    <main><header><button className="menu" onClick={() => setMenuOpen(true)}>☰</button><strong>Klod <em>Experimental</em></strong><span className="avatar">K</span></header>
      <section className={messages.length ? 'conversation populated' : 'conversation'}>{messages.length ? <div className="messages">{messages.map((message) => <article className={'message ' + message.role} key={message.id}><b>{message.role === 'user' ? 'Você' : 'Klod'}</b><p>{message.content}</p></article>)}{loading && <div className="loading">Klod está processando…</div>}</div> : <div className="welcome"><div className="orb">K</div><label>INTELIGÊNCIA EM CONSTRUÇÃO</label><h1>O que vamos<br/><i>construir hoje?</i></h1><p>Um espaço para pensar, pesquisar e desenvolver ideias.<br/>O modelo experimental será conectado quando estiver treinado.</p><div className="prompts"><button onClick={() => setDraft('Como funciona a arquitetura neural do Klod?')}>Entender a arquitetura ↗</button><button onClick={() => setDraft('Planeje um projeto de software do zero.')}>Planejar um projeto ↗</button></div></div>}</section>
      <footer><form onSubmit={send}><textarea ref={input} value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); void send(event) } }} rows={2} maxLength={12000} placeholder="Pergunte ao Klod…"/><div><small>Enter para enviar · Shift + Enter para nova linha</small><button type="submit" disabled={!draft.trim() || loading}>↑</button></div></form><p>Klod está em desenvolvimento. As respostas dependem de um checkpoint neural treinado.</p></footer>
    </main>
  </div>
}
