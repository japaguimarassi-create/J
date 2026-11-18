import { type FormEvent, useEffect, useRef, useState } from 'react'

type Message = { id: string; role: 'user' | 'assistant'; content: string }
type User = { id: string; email: string; display_name: string; picture: string; role: 'user' | 'admin' }
type Conversation = { id: string; title: string; updated_at: string }
type Project = { id: string; name: string; description: string; updated_at: string }
type WorkspaceFile = { path: string; size: number }
type AdminUser = { id: string; email: string; display_name: string; role: string; created_at: string }
type AdminOverview = { users: number; conversations: number; projects: number }
type ActiveView = 'chat' | 'projects' | 'coder' | 'admin'

const apiBase = (import.meta.env.VITE_KLOD_API_URL || '').replace(/\/$/, '')
const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || ''

function readCookie(name: string): string {
  const prefix = encodeURIComponent(name) + '='
  const entry = document.cookie.split('; ').find((item) => item.startsWith(prefix))
  return entry ? decodeURIComponent(entry.slice(prefix.length)) : ''
}

async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  const method = (init.method || 'GET').toUpperCase()
  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
    headers.set('X-Klod-CSRF', readCookie('klod_csrf'))
  }
  if (init.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  const response = await fetch(apiBase + path, { ...init, method, headers, credentials: 'include' })
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(payload.detail || 'A operação não foi concluída.')
  return payload as T
}

function makeMessage(role: Message['role'], content: string): Message {
  return { id: crypto.randomUUID(), role, content }
}

export default function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null)
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null)
  const [activeView, setActiveView] = useState<ActiveView>('chat')
  const [files, setFiles] = useState<WorkspaceFile[]>([])
  const [activeFilePath, setActiveFilePath] = useState('')
  const [fileContent, setFileContent] = useState('')
  const [newFilePath, setNewFilePath] = useState('')
  const [projectName, setProjectName] = useState('')
  const [projectDescription, setProjectDescription] = useState('')
  const [adminUsers, setAdminUsers] = useState<AdminUser[]>([])
  const [adminOverview, setAdminOverview] = useState<AdminOverview | null>(null)
  const [draft, setDraft] = useState('')
  const [loading, setLoading] = useState(false)
  const [savingFile, setSavingFile] = useState(false)
  const [status, setStatus] = useState<'checking' | 'online' | 'offline'>('checking')
  const [modelAvailable, setModelAvailable] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [user, setUser] = useState<User | null>(null)
  const [authError, setAuthError] = useState('')
  const [pageError, setPageError] = useState('')
  const [notice, setNotice] = useState('')
  const [authBusy, setAuthBusy] = useState(false)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const googleButtonRef = useRef<HTMLDivElement>(null)

  async function loadAccountData(account: User) {
    const [conversationPayload, projectPayload] = await Promise.all([
      apiRequest<{ conversations: Conversation[] }>('/v1/conversations'),
      apiRequest<{ projects: Project[] }>('/v1/projects'),
    ])
    setConversations(conversationPayload.conversations)
    setProjects(projectPayload.projects)
    if (conversationPayload.conversations.length) {
      const last = conversationPayload.conversations[0]
      const detail = await apiRequest<{ conversation: Conversation & { messages: Message[] } }>(
        '/v1/conversations/' + last.id,
      )
      setActiveConversationId(last.id)
      setMessages(detail.conversation.messages.map((item) => ({ ...item, id: String(item.id) })))
    }
    if (account.role === 'admin') await loadAdminData()
  }

  async function loadAdminData() {
    const [overview, users] = await Promise.all([
      apiRequest<AdminOverview>('/v1/admin/overview'),
      apiRequest<{ users: AdminUser[] }>('/v1/admin/users'),
    ])
    setAdminOverview(overview)
    setAdminUsers(users.users)
  }

  async function activateAccount(account: User) {
    setUser(account)
    setAuthError('')
    setPageError('')
    try {
      await loadAccountData(account)
    } catch (error) {
      setPageError(error instanceof Error ? error.message : 'Não foi possível carregar sua conta.')
    }
  }

  useEffect(() => {
    let active = true
    Promise.all([
      fetch(apiBase + '/health').then((response) => {
        if (!response.ok) throw new Error()
        return response.json()
      }),
      fetch(apiBase + '/v1/model').then((response) => response.ok ? response.json() : null).catch(() => null),
      apiRequest<{ user: User }>('/v1/auth/me').catch(() => null),
    ]).then(async ([health, model, identity]) => {
      if (!active) return
      setStatus(health.ok ? 'online' : 'offline')
      setModelAvailable(Boolean(model?.available))
      if (identity?.user) await activateAccount(identity.user)
    }).catch(() => {
      if (active) setStatus('offline')
    })
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
              const payload = await apiRequest<{ user: User }>('/v1/auth/google', {
                method: 'POST',
                body: JSON.stringify({ credential: credentialResponse.credential }),
              })
              if (active) await activateAccount(payload.user)
            } catch (error) {
              if (active) setAuthError(error instanceof Error ? error.message : 'Falha na autenticação.')
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

  async function refreshConversations() {
    const payload = await apiRequest<{ conversations: Conversation[] }>('/v1/conversations')
    setConversations(payload.conversations)
  }

  async function refreshProjects() {
    const payload = await apiRequest<{ projects: Project[] }>('/v1/projects')
    setProjects(payload.projects)
  }

  function startNewChat() {
    setActiveConversationId(null)
    setMessages([])
    setDraft('')
    setActiveView('chat')
    setSidebarOpen(false)
    setPageError('')
  }

  async function openConversation(conversationId: string) {
    setLoading(true)
    setPageError('')
    try {
      const payload = await apiRequest<{ conversation: Conversation & { messages: Message[] } }>(
        '/v1/conversations/' + conversationId,
      )
      setActiveConversationId(conversationId)
      setMessages(payload.conversation.messages.map((item) => ({ ...item, id: String(item.id) })))
      setActiveView('chat')
      setSidebarOpen(false)
    } catch (error) {
      setPageError(error instanceof Error ? error.message : 'Não foi possível abrir a conversa.')
    } finally {
      setLoading(false)
    }
  }

  async function sendMessage(event: FormEvent) {
    event.preventDefault()
    const content = draft.trim()
    if (!content || loading || !user) return
    setDraft('')
    setLoading(true)
    setPageError('')
    setNotice('')
    setMessages((items) => [...items, makeMessage('user', content)])
    try {
      let conversationId = activeConversationId
      if (!conversationId) {
        const created = await apiRequest<{ conversation: Conversation }>('/v1/conversations', {
          method: 'POST',
          body: JSON.stringify({ title: content.slice(0, 150) || 'Nova conversa' }),
        })
        conversationId = created.conversation.id
        setActiveConversationId(conversationId)
      }
      const payload = await apiRequest<{ response: string; conversation_id: string; training_steps: number; parameter_count: number }>(
        '/v1/chat',
        {
          method: 'POST',
          body: JSON.stringify({ message: content, conversation_id: conversationId }),
        },
      )
      setActiveConversationId(payload.conversation_id)
      setMessages((items) => [...items, makeMessage('assistant', payload.response)])
      setNotice('Checkpoint neural: ' + payload.training_steps.toLocaleString('pt-BR') + ' atualizações · ' + payload.parameter_count.toLocaleString('pt-BR') + ' parâmetros')
      await refreshConversations()
    } catch (error) {
      setMessages((items) => [...items, makeMessage('assistant', 'Não foi possível concluir a solicitação. ' + (error instanceof Error ? error.message : 'Falha de conexão.'))])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  async function logout() {
    setAuthBusy(true)
    try {
      await apiRequest<{ ok: boolean }>('/v1/auth/logout', { method: 'POST' })
      setUser(null)
      setMessages([])
      setConversations([])
      setProjects([])
      setActiveConversationId(null)
      setActiveProjectId(null)
      setFiles([])
      setActiveFilePath('')
      setFileContent('')
      setAdminUsers([])
      setAdminOverview(null)
      setActiveView('chat')
      setAuthError('')
      setNotice('')
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : 'Falha ao sair.')
    } finally {
      setAuthBusy(false)
    }
  }

  async function createProject(event: FormEvent) {
    event.preventDefault()
    const name = projectName.trim()
    if (!name) return
    setLoading(true)
    setPageError('')
    try {
      const payload = await apiRequest<{ project: Project }>('/v1/projects', {
        method: 'POST',
        body: JSON.stringify({ name, description: projectDescription }),
      })
      await refreshProjects()
      setActiveProjectId(payload.project.id)
      setProjectName('')
      setProjectDescription('')
      setNotice('Projeto criado.')
    } catch (error) {
      setPageError(error instanceof Error ? error.message : 'Não foi possível criar o projeto.')
    } finally {
      setLoading(false)
    }
  }

  async function openCoder(projectId: string) {
    setActiveProjectId(projectId)
    setActiveView('coder')
    setActiveFilePath('')
    setFileContent('')
    setNewFilePath('')
    setSidebarOpen(false)
    setPageError('')
    try {
      const payload = await apiRequest<{ files: WorkspaceFile[] }>('/v1/projects/' + projectId + '/files')
      setFiles(payload.files)
    } catch (error) {
      setPageError(error instanceof Error ? error.message : 'Não foi possível abrir o workspace.')
    }
  }

  async function openProjectFile(path: string) {
    if (!activeProjectId) return
    try {
      const payload = await apiRequest<{ path: string; content: string }>(
        '/v1/projects/' + activeProjectId + '/files?path=' + encodeURIComponent(path),
      )
      setActiveFilePath(path)
      setFileContent(payload.content)
      setNewFilePath('')
    } catch (error) {
      setPageError(error instanceof Error ? error.message : 'Não foi possível ler o arquivo.')
    }
  }

  async function saveProjectFile(event: FormEvent) {
    event.preventDefault()
    if (!activeProjectId) return
    const path = (activeFilePath || newFilePath).trim()
    if (!path) return
    setSavingFile(true)
    setPageError('')
    try {
      await apiRequest('/v1/projects/' + activeProjectId + '/files', {
        method: 'PUT',
        body: JSON.stringify({ path, content: fileContent }),
      })
      setActiveFilePath(path)
      setNewFilePath('')
      const payload = await apiRequest<{ files: WorkspaceFile[] }>('/v1/projects/' + activeProjectId + '/files')
      setFiles(payload.files)
      setNotice('Arquivo salvo no workspace do projeto.')
    } catch (error) {
      setPageError(error instanceof Error ? error.message : 'Não foi possível salvar o arquivo.')
    } finally {
      setSavingFile(false)
    }
  }

  async function enterView(view: ActiveView) {
    setActiveView(view)
    setSidebarOpen(false)
    setPageError('')
    if (view === 'projects') await refreshProjects().catch((error) => setPageError(String(error)))
    if (view === 'admin') await loadAdminData().catch((error) => setPageError(String(error)))
  }

  const activeProject = projects.find((project) => project.id === activeProjectId) || null

  return (
    <div className="app-shell">
      <aside className={'sidebar ' + (sidebarOpen ? 'sidebar-open' : '')} data-testid="sidebar">
        <div className="brand-row">
          <div className="brand-mark">K</div><span>KLOD</span>
          <button className="icon-button close-sidebar" onClick={() => setSidebarOpen(false)} aria-label="Fechar menu">×</button>
        </div>
        <button className="new-chat" onClick={startNewChat}><span>＋</span> Nova conversa</button>
        <div className="sidebar-label">ESPAÇO DE TRABALHO</div>
        <button className={'nav-item ' + (activeView === 'chat' ? 'active' : '')} onClick={() => void enterView('chat')}><span>◌</span> Conversas</button>
        <button className={'nav-item ' + (activeView === 'projects' ? 'active' : '')} onClick={() => void enterView('projects')} disabled={!user}><span>▧</span> Projetos</button>
        <button className={'nav-item ' + (activeView === 'coder' ? 'active' : '')} onClick={() => activeProjectId && void openCoder(activeProjectId)} disabled={!user || !activeProjectId}><span>⌘</span> Coder</button>
        {user?.role === 'admin' && <button className={'nav-item ' + (activeView === 'admin' ? 'active' : '')} onClick={() => void enterView('admin')}><span>◈</span> Administração</button>}
        {user && <div className="history-panel">
          <div className="sidebar-label">RECENTES</div>
          {conversations.slice(0, 7).map((conversation) => (
            <button key={conversation.id} className={'history-item ' + (conversation.id === activeConversationId ? 'selected' : '')} onClick={() => void openConversation(conversation.id)} title={conversation.title}>
              <span>◌</span><span>{conversation.title}</span>
            </button>
          ))}
          {!conversations.length && <div className="empty-history">Suas conversas salvas aparecerão aqui.</div>}
        </div>}
        <div className="account-panel">
          {user ? <>
            <div className="account-identity">
              {user.picture ? <img src={user.picture} alt="" referrerPolicy="no-referrer" /> : <span className="account-initial">{(user.display_name || user.email).slice(0, 1).toUpperCase()}</span>}
              <div><strong>{user.display_name || user.email}</strong><small>{user.role === 'admin' ? 'Administrador' : 'Conta Google'}</small></div>
            </div>
            <button className="account-action" onClick={() => void logout()} disabled={authBusy}>Sair da conta</button>
          </> : <>
            <div className="account-prompt">Entre para acessar suas conversas e projetos.</div>
            {googleClientId ? <div ref={googleButtonRef} className="google-button" /> : <div className="oauth-missing">Login Google aguardando configuração OAuth.</div>}
            {authBusy && <small className="auth-note">Verificando identidade…</small>}
          </>}
          {authError && <div className="auth-error" role="alert">{authError}</div>}
        </div>
        <div className="sidebar-footer"><div className={'status-dot ' + status} />{status === 'online' ? 'API conectada' : status === 'checking' ? 'Verificando conexão' : 'API desconectada'}<span className="version">v0.3</span></div>
      </aside>
      {sidebarOpen && <button className="scrim" onClick={() => setSidebarOpen(false)} aria-label="Fechar menu" />}
      <main className="main-panel">
        <header className="topbar">
          <button className="icon-button menu-button" onClick={() => setSidebarOpen(true)} aria-label="Abrir menu">☰</button>
          <div className="topbar-title">Klod <span>{modelAvailable ? 'Modelo conectado' : 'Experimental'}</span></div>
          <button className="profile-button" aria-label="Conta">{user ? (user.display_name || user.email).slice(0, 1).toUpperCase() : 'K'}</button>
        </header>

        {pageError && <div className="page-alert" role="alert">{pageError}<button onClick={() => setPageError('')} aria-label="Fechar aviso">×</button></div>}

        {activeView === 'chat' && <section className={'conversation ' + (messages.length ? 'has-messages' : '')} data-testid="chat-view">
          {messages.length === 0 ? <div className="welcome">
            <div className="orb"><span>K</span></div>
            <p className="eyebrow">INTELIGÊNCIA EM CONSTRUÇÃO</p>
            <h1>O que vamos<br /><em>construir hoje?</em></h1>
            <p className="welcome-copy">Uma IA, um agente e um Coder integrado.<br />Converse, planeje e desenvolva no mesmo espaço.</p>
            <div className="suggestions">
              <button onClick={() => setDraft('Como funciona a arquitetura neural do Klod?')}>Entender a arquitetura <span>↗</span></button>
              <button onClick={() => setDraft('Planeje um projeto de software do zero.')}>Planejar um projeto <span>↗</span></button>
            </div>
          </div> : <div className="message-list">
            {messages.map((message) => <article className={'message ' + message.role} key={message.id}>
              <div className="message-avatar">{message.role === 'user' ? 'V' : 'K'}</div>
              <div className="message-body"><div className="message-role">{message.role === 'user' ? 'Você' : 'Klod'}</div><p>{message.content}</p></div>
            </article>)}
            {loading && <div className="thinking"><span /><span /><span /> <small>Klod está processando</small></div>}
            <div ref={bottomRef} />
          </div>}
        </section>}

        {activeView === 'projects' && <section className="workspace-view" data-testid="projects-view">
          <div className="view-heading"><p className="eyebrow">ESPAÇO PERSISTENTE</p><h1>Seus projetos</h1><p>Organize código e arquivos em workspaces separados.</p></div>
          <form className="project-create" onSubmit={createProject}>
            <label htmlFor="project-name">Novo projeto</label>
            <input id="project-name" value={projectName} onChange={(event) => setProjectName(event.target.value)} placeholder="Nome do projeto" maxLength={100} required />
            <textarea value={projectDescription} onChange={(event) => setProjectDescription(event.target.value)} placeholder="Descrição (opcional)" maxLength={1000} rows={2} />
            <button type="submit" disabled={!projectName.trim() || loading}>Criar projeto</button>
          </form>
          <div className="project-grid">
            {projects.map((project) => <article className="project-card" key={project.id}>
              <div className="project-icon">▧</div><h2>{project.name}</h2><p>{project.description || 'Workspace pronto para seus arquivos.'}</p>
              <button onClick={() => void openCoder(project.id)}>Abrir no Coder <span>↗</span></button>
            </article>)}
            {!projects.length && <div className="empty-state">Nenhum projeto criado. Crie o primeiro acima.</div>}
          </div>
        </section>}

        {activeView === 'coder' && <section className="coder-view" data-testid="coder-view">
          <div className="view-heading coder-heading"><p className="eyebrow">CODER INTEGRADO · UM ÚNICO AGENTE</p><h1>{activeProject?.name || 'Workspace'}</h1><p>Arquivos isolados por conta e projeto. Gravações ocorrem apenas ao salvar.</p></div>
          <div className="coder-layout">
            <aside className="file-explorer">
              <div className="file-explorer-title">ARQUIVOS <button onClick={() => { setActiveFilePath(''); setNewFilePath(''); setFileContent('') }} aria-label="Novo arquivo">＋</button></div>
              {files.map((file) => <button key={file.path} className={'file-item ' + (file.path === activeFilePath ? 'selected' : '')} onClick={() => void openProjectFile(file.path)}><span>▤</span><span>{file.path}</span></button>)}
              {!files.length && <p className="empty-files">Este projeto ainda não tem arquivos.</p>}
            </aside>
            <form className="file-editor" onSubmit={saveProjectFile}>
              <div className="editor-toolbar">
                <input aria-label="Caminho do arquivo" value={activeFilePath || newFilePath} onChange={(event) => activeFilePath ? setActiveFilePath(event.target.value) : setNewFilePath(event.target.value)} placeholder="src/main.py" maxLength={240} required />
                <button type="submit" disabled={savingFile || !(activeFilePath || newFilePath).trim()}>{savingFile ? 'Salvando…' : 'Salvar arquivo'}</button>
              </div>
              <textarea aria-label="Conteúdo do arquivo" value={fileContent} onChange={(event) => setFileContent(event.target.value)} placeholder="Escreva ou cole o conteúdo do arquivo…" spellCheck={false} />
              <p className="editor-footnote" role="status">{notice || "O Klod não executa comandos no host. O workspace aceita arquivos de texto com limite de tamanho e proteção contra caminhos externos."}</p>
            </form>
          </div>
        </section>}

        {activeView === 'admin' && user?.role === 'admin' && <section className="workspace-view" data-testid="admin-view">
          <div className="view-heading"><p className="eyebrow">CONTROLE DA PLATAFORMA</p><h1>Administração</h1><p>Visão operacional da instalação Klod.</p></div>
          <div className="stats-grid">
            <article className="stat-card"><span>Usuários</span><strong>{adminOverview?.users ?? '—'}</strong></article>
            <article className="stat-card"><span>Conversas</span><strong>{adminOverview?.conversations ?? '—'}</strong></article>
            <article className="stat-card"><span>Projetos</span><strong>{adminOverview?.projects ?? '—'}</strong></article>
          </div>
          <div className="admin-table-wrap"><h2>Contas cadastradas</h2><table><thead><tr><th>Usuário</th><th>E-mail</th><th>Perfil</th></tr></thead><tbody>
            {adminUsers.map((item) => <tr key={item.id}><td>{item.display_name || '—'}</td><td>{item.email}</td><td><span className={'role-pill ' + item.role}>{item.role}</span></td></tr>)}
          </tbody></table>{!adminUsers.length && <p className="empty-state">Nenhuma conta encontrada.</p>}</div>
        </section>}

        {activeView === 'chat' && <footer className="composer-area">
          <form className="composer" onSubmit={sendMessage}>
            <textarea ref={inputRef} value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); void sendMessage(event) } }} placeholder={user ? 'Pergunte ao Klod...' : 'Entre com Google para conversar…'} rows={1} maxLength={12000} disabled={!user || loading} />
            <div className="composer-actions"><span className="composer-hint">{user ? (modelAvailable ? 'Enter para enviar · Shift + Enter para quebrar linha' : 'Modelo ainda não carregado') : 'Login Google obrigatório'}</span><button className="send-button" type="submit" disabled={!user || !draft.trim() || loading} aria-label="Enviar mensagem">↑</button></div>
          </form>
          <p className="disclaimer">{notice || (modelAvailable ? 'O modelo carregado é experimental; confira as respostas.' : 'Klod ainda não possui um checkpoint neural configurado. A interface e o backend não simulam respostas.')}</p>
        </footer>}
      </main>
    </div>
  )
}
