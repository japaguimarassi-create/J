import { type FormEvent, useEffect, useRef, useState } from 'react'

type Message = { id: string; role: 'user' | 'assistant'; content: string }
type User = { id: string; email: string; display_name: string; picture: string; role: 'user' | 'admin' }

const apiBase = (import.meta.env.VITE_KLOD_API_URL || '').replace(/\/$/, '')
const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || ''

function readCookie(name: string): string {
  const prefix = encodeURIComponent(name) + '='
  const entry = document.cookie.split('; ').find((item) => item.startsWith(prefix))
  return entry ? decodeURIComponent(entry.slice(prefix.length)) : ''
}

export default function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [draft, setDraft] = useState('')
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState<'checking' | 'online' | 'offline'>('checking')
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [user, setUser] = useState<User | null>(null)
  const [authError, setAuthError] = useState('')
  const [authBusy, setAuthBusy] = useState(false)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const googleButtonRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let active = true
    fetch(apiBase + '/health')
      .then((response) => { if (!response.ok) throw new Error(); return response.json() })
      .then(() => active && setStatus('online'))
      .catch(() => active && setStatus('offline'))
    fetch(apiBase + '/v1/auth/me', { credentials: 'include' })
      .then((response) => response.ok ? response.json() : null)
      .then((payload) => { if (active && payload?.user) setUser(payload.user as User) })
      .catch(() => undefined)
    return () => { active = false }
  }, [])

  useEffect(() => {
    if (!googleClientId || !googleButtonRef.current) return
    let active = true
    const renderButton = () => {
      if (!active || !googleButtonRef.current || !window.google?.accounts.id) return
      window.google.accounts.id.initialize({
        client_id: googleClientId,
        callback: (credentialResponse) => {
          void (async () => {
            setAuthBusy(true)
            setAuthError('')
            try {
              const response = await fetch(apiBase + '/v1/auth/google', {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ credential: credentialResponse.credential }),
              })
              const payload = await response.json().catch(() => ({}))
              if (!response.ok) throw new Error(payload.detail || 'Falha no login Google')
              if (active) setUser(payload.user as User)
            } catch (error) {
              if (active) setAuthError(error instanceof Error ? error.message : 'Falha na autenticação')
            } finally {
              if (active) setAuthBusy(false)
            }
          })()
        },
      })
      window.google.accounts.id.renderButton(googleButtonRef.current, {
        type: 'standard', theme: 'filled_black', size: 'large', shape: 'pill',
        text: 'signin_with', width: 220, logo_alignment: 'left',
      })
    }
    let script = document.querySelector<HTMLScriptElement>('script[data-klod-google]')
    if (window.google?.accounts.id) renderButton()
    else if (script) script.addEventListener('load', renderButton)
    else {
      script = document.createElement('script')
      script.src = 'https://accounts.google.com/gsi/client'
      script.async = true
      script.defer = true
      script.dataset.klodGoogle = 'true'
      script.addEventListener('load', renderButton)
      script.addEventListener('error', () => active && setAuthError('Não foi possível carregar o login Google.'))
      document.head.appendChild(script)
    }
    return () => {
      active = false
      script?.removeEventListener('load', renderButton)
    }
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, loading])

  async function sendMessage(event: FormEvent) {
    event.preventDefault()
    const content = draft.trim()
    if (!content || loading) return
    if (!user) {
      setAuthError('Entre com uma conta Google verificada para conversar.')
      return
    }
    setMessages((items) => [...items, { id: crypto.randomUUID(), role: 'user', content }])
    setDraft('')
    setLoading(true)
    try {
      const response = await fetch(apiBase + '/v1/chat', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json', 'X-Klod-CSRF': readCookie('klod_csrf') },
        body: JSON.stringify({ message: content }),
      })
      const payload = await response.json().catch(() => ({}))
      if (response.status === 401) setUser(null)
      if (!response.ok) throw new Error(payload.detail || 'Falha ao consultar o modelo')
      setMessages((items) => [...items, { id: crypto.randomUUID(), role: 'assistant', content: payload.response || '' }])
    } catch (error) {
      const detail = error instanceof Error ? error.message : 'Falha de conexão.'
      setMessages((items) => [...items, { id: crypto.randomUUID(), role: 'assistant', content: 'Não foi possível gerar uma resposta real do modelo. ' + detail }])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  async function logout() {
    setAuthBusy(true)
    try {
      const response = await fetch(apiBase + '/v1/auth/logout', {
        method: 'POST',
        credentials: 'include',
        headers: { 'X-Klod-CSRF': readCookie('klod_csrf') },
      })
      const payload = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(payload.detail || 'Não foi possível encerrar a sessão')
      setUser(null)
      setMessages([])
      setAuthError('')
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : 'Falha ao sair.')
    } finally {
      setAuthBusy(false)
    }
  }

  return (
    <div className="app-shell">
      <aside className={'sidebar ' + (sidebarOpen ? 'sidebar-open' : '')}>
        <div className="brand-row"><div className="brand-mark">K</div><span>KLOD</span><button className="icon-button close-sidebar" onClick={() => setSidebarOpen(false)} aria-label="Fechar menu">×</button></div>
        <button className="new-chat" onClick={() => { setMessages([]); setSidebarOpen(false) }}><span>＋</span> Nova conversa</button>
        <div className="sidebar-label">ESPAÇO DE TRABALHO</div>
        <button className="nav-item active"><span>◌</span> Conversas</button>
        <button className="nav-item" disabled><span>▧</span> Projetos <small>em breve</small></button>
        <button className="nav-item" disabled><span>⌘</span> Desenvolvimento <small>em breve</small></button>
        <div className="account-panel">
          {user ? <>
            <div className="account-identity">
              {user.picture ? <img src={user.picture} alt="" referrerPolicy="no-referrer" /> : <span className="account-initial">{(user.display_name || user.email).slice(0, 1).toUpperCase()}</span>}
              <div><strong>{user.display_name || user.email}</strong><small>{user.role === 'admin' ? 'Administrador' : 'Conta Google'}</small></div>
            </div>
            <button className="account-action" onClick={() => void logout()} disabled={authBusy}>Sair da conta</button>
          </> : <>
            <div className="account-prompt">Entre para acessar sua conta Klod.</div>
            {googleClientId ? <div ref={googleButtonRef} className="google-button" /> : <div className="oauth-missing">Login Google aguardando configuração OAuth.</div>}
            {authBusy && <small className="auth-note">Verificando identidade…</small>}
          </>}
          {authError && <div className="auth-error" role="alert">{authError}</div>}
        </div>
        <div className="sidebar-footer"><div className={'status-dot ' + status} />{status === 'online' ? 'API conectada' : status === 'checking' ? 'Verificando conexão' : 'API desconectada'}<span className="version">v0.2</span></div>
      </aside>
      {sidebarOpen && <button className="scrim" onClick={() => setSidebarOpen(false)} aria-label="Fechar menu" />}
      <main className="main-panel">
        <header className="topbar"><button className="icon-button menu-button" onClick={() => setSidebarOpen(true)} aria-label="Abrir menu">☰</button><div className="topbar-title">Klod <span>Experimental</span></div><button className="profile-button" aria-label="Conta">{user ? (user.display_name || user.email).slice(0, 1).toUpperCase() : 'K'}</button></header>
        <section className={'conversation ' + (messages.length ? 'has-messages' : '')}>
          {messages.length === 0 ? <div className="welcome"><div className="orb"><span>K</span></div><p className="eyebrow">INTELIGÊNCIA EM CONSTRUÇÃO</p><h1>O que vamos<br /><em>construir hoje?</em></h1><p className="welcome-copy">Um espaço para pensar, pesquisar e desenvolver ideias.<br />O modelo experimental será conectado quando estiver treinado.</p><div className="suggestions"><button onClick={() => setDraft('Como funciona a arquitetura neural do Klod?')}>Entender a arquitetura <span>↗</span></button><button onClick={() => setDraft('Planeje um projeto de software do zero.')}>Planejar um projeto <span>↗</span></button></div></div> : <div className="message-list">{messages.map((message) => <article className={'message ' + message.role} key={message.id}><div className="message-avatar">{message.role === 'user' ? 'V' : 'K'}</div><div className="message-body"><div className="message-role">{message.role === 'user' ? 'Você' : 'Klod'}</div><p>{message.content}</p></div></article>)}{loading && <div className="thinking"><span /><span /><span /> <small>Klod está processando</small></div>}<div ref={bottomRef} /></div>}
        </section>
        <footer className="composer-area"><form className="composer" onSubmit={sendMessage}><textarea ref={inputRef} value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); void sendMessage(event) } }} placeholder={user ? 'Pergunte ao Klod...' : 'Entre com Google para conversar…'} rows={1} maxLength={12000} disabled={!user || loading} /><div className="composer-actions"><span className="composer-hint">{user ? 'Enter para enviar · Shift + Enter para quebrar linha' : 'Login Google obrigatório'}</span><button className="send-button" type="submit" disabled={!user || !draft.trim() || loading} aria-label="Enviar mensagem">↑</button></div></form><p className="disclaimer">Klod ainda está em desenvolvimento. Respostas dependem de um checkpoint neural treinado.</p></footer>
      </main>
    </div>
  )
}
