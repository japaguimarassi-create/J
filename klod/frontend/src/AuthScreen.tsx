import { type FormEvent, useEffect, useState } from 'react'

type User = { id: string; email: string; display_name: string; picture: string; role: 'user' | 'admin' }
type AuthMode = 'login' | 'register' | 'forgot' | 'resend' | 'sent' | 'verify' | 'reset' | 'reset-done'

type Props = {
  apiBase: string
  onAuthenticated: (user: User) => Promise<void>
}

async function request<T>(apiBase: string, path: string, body: unknown): Promise<T> {
  const response = await fetch(apiBase + path, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(payload.detail || 'Não foi possível concluir a solicitação.')
  return payload as T
}

export default function AuthScreen({ apiBase, onAuthenticated }: Props) {
  const params = new URLSearchParams(window.location.search)
  const verificationToken = params.get('verify') || ''
  const resetToken = params.get('reset') || ''
  const [mode, setMode] = useState<AuthMode>(verificationToken ? 'verify' : resetToken ? 'reset' : 'login')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [visiblePassword, setVisiblePassword] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [sentAddress, setSentAddress] = useState('')
  const [showResend, setShowResend] = useState(false)

  useEffect(() => {
    if (!verificationToken) return
    let active = true
    setBusy(true)
    request<{ user: User }>(apiBase, '/v1/auth/verify-email', { token: verificationToken })
      .then(({ user }) => {
        if (!active) return
        window.history.replaceState({}, '', window.location.pathname)
        return onAuthenticated(user)
      })
      .catch((reason: unknown) => {
        if (!active) return
        setError(reason instanceof Error ? reason.message : 'Não foi possível confirmar o e-mail.')
        setMode('resend')
      })
      .finally(() => {
        if (active) setBusy(false)
      })
    return () => { active = false }
  }, [apiBase, verificationToken, onAuthenticated])

  useEffect(() => {
    if (!resetToken || mode !== 'reset') return
    setMessage('O link foi aberto. Defina uma nova senha para sua conta.')
  }, [resetToken, mode])

  function changeMode(next: AuthMode) {
    setMode(next)
    setError('')
    setMessage('')
    setPassword('')
    setConfirmation('')
    setVisiblePassword(false)
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (busy) return
    setBusy(true)
    setError('')
    setMessage('')
    try {
      if (mode === 'login') {
        const result = await request<{ user: User }>(apiBase, '/v1/auth/login', { email, password })
        await onAuthenticated(result.user)
        return
      }
      if (mode === 'register') {
        if (password !== confirmation) throw new Error('As senhas não coincidem.')
        await request(apiBase, '/v1/auth/register', { display_name: name, email, password })
        setSentAddress(email.trim().toLowerCase())
        setMode('sent')
        return
      }
      if (mode === 'forgot' || mode === 'resend') {
        const path = mode === 'forgot' ? '/v1/auth/forgot-password' : '/v1/auth/resend-verification'
        const result = await request<{ message: string }>(apiBase, path, { email })
        setMessage(result.message)
        if (mode === 'resend') setMode('sent')
        return
      }
      if (mode === 'reset') {
        if (password !== confirmation) throw new Error('As senhas não coincidem.')
        await request(apiBase, '/v1/auth/reset-password', { token: resetToken, password })
        window.history.replaceState({}, '', window.location.pathname)
        setMode('reset-done')
        setPassword('')
        setConfirmation('')
        return
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Não foi possível concluir a solicitação.')
    } finally {
      setBusy(false)
    }
  }

  async function resend() {
    if (!sentAddress || busy) return
    setBusy(true)
    setError('')
    setMessage('')
    try {
      const result = await request<{ message: string }>(apiBase, '/v1/auth/resend-verification', { email: sentAddress })
      setMessage(result.message)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Não foi possível reenviar o e-mail.')
    } finally {
      setBusy(false)
    }
  }

  const isPasswordMode = mode === 'login' || mode === 'register' || mode === 'reset'
  const isEmailMode = mode === 'forgot' || mode === 'resend'
  const isFormMode = isPasswordMode || isEmailMode
  const heading = mode === 'login' ? 'Bem-vindo de volta' :
    mode === 'register' ? 'Crie sua conta' :
    mode === 'forgot' ? 'Recuperar acesso' :
    mode === 'resend' ? 'Confirmar e-mail' :
    mode === 'sent' ? 'Confira sua caixa de entrada' :
    mode === 'verify' ? 'Confirmando seu endereço' :
    mode === 'reset' ? 'Nova senha' : 'Senha atualizada'
  const description = mode === 'login' ? 'Entre para continuar de onde parou.' :
    mode === 'register' ? 'Um espaço para pensar, criar e desenvolver.' :
    mode === 'forgot' ? 'Enviaremos um link seguro para redefinir sua senha.' :
    mode === 'resend' ? 'Envie novamente o link de confirmação da sua conta.' :
    mode === 'sent' ? 'Enviamos as próximas instruções para o endereço informado.' :
    mode === 'verify' ? 'Estamos validando o link de confirmação.' :
    mode === 'reset' ? 'Escolha uma senha nova e exclusiva para sua conta.' :
    'Você já pode entrar com sua nova senha.'

  return (
    <main className="auth-screen">
      <div className="auth-ambient auth-ambient-one" />
      <div className="auth-ambient auth-ambient-two" />
      <div className="auth-frame">
        <section className="auth-story" aria-label="Sobre o Klod">
          <a className="auth-brand" href="/" aria-label="Klod início">
            <span className="auth-brand-mark">K</span>
            <span>KLOD<span className="auth-brand-period">.</span></span>
          </a>
          <div className="auth-story-content">
            <div className="auth-orbit" aria-hidden="true">
              <div className="auth-orbit-core">K</div>
              <span className="orbit-node orbit-node-a" />
              <span className="orbit-node orbit-node-b" />
              <span className="orbit-node orbit-node-c" />
            </div>
            <p className="auth-kicker">UM ESPAÇO PARA IR ALÉM</p>
            <h1>Suas ideias.<br /><span>Mais possibilidades.</span></h1>
            <p className="auth-story-copy">Converse, planeje projetos e desenvolva no mesmo ambiente. Uma inteligência, um agente e um Coder integrado.</p>
            <div className="auth-capabilities">
              <span><i>✳</i> Conversas inteligentes</span>
              <span><i>⌘</i> Coder integrado</span>
              <span><i>◫</i> Projetos persistentes</span>
            </div>
          </div>
          <div className="auth-story-foot"><span className="auth-live-dot" /> Plataforma experimental <span className="auth-foot-divider" /> v0.4</div>
        </section>

        <section className="auth-panel">
          <div className="auth-panel-brand">
            <span className="auth-brand-mark">K</span>
            <span>KLOD<span className="auth-brand-period">.</span></span>
          </div>
          <div className="auth-card">
            <div className="auth-card-heading">
              <p className="auth-kicker">{mode === 'register' ? 'COMECE AGORA' : mode === 'login' ? 'SEU ESPAÇO DE TRABALHO' : 'ACESSO À CONTA'}</p>
              <h2>{heading}</h2>
              <p>{description}</p>
            </div>

            {(mode === 'login' || mode === 'register') && (
              <div className="auth-tabs" role="tablist" aria-label="Tipo de acesso">
                <button type="button" role="tab" aria-selected={mode === 'login'} className={mode === 'login' ? 'selected' : ''} onClick={() => changeMode('login')}>Entrar</button>
                <button type="button" role="tab" aria-selected={mode === 'register'} className={mode === 'register' ? 'selected' : ''} onClick={() => changeMode('register')}>Criar conta</button>
              </div>
            )}

            {isFormMode && (
              <form className="auth-form" onSubmit={submit}>
                {mode === 'register' && (
                  <label className="auth-field">
                    <span>Seu nome</span>
                    <input value={name} onChange={(event) => setName(event.target.value)} autoComplete="name" placeholder="Como podemos chamar você?" maxLength={160} required />
                  </label>
                )}
                {(mode === 'login' || mode === 'register' || isEmailMode) && (
                  <label className="auth-field">
                    <span>Endereço de e-mail</span>
                    <input type="email" inputMode="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" placeholder="voce@exemplo.com" maxLength={254} required />
                  </label>
                )}
                {isPasswordMode && (
                  <label className="auth-field">
                    <span>{mode === 'reset' ? 'Nova senha' : 'Senha'}</span>
                    <div className="auth-password-wrap">
                      <input type={visiblePassword ? 'text' : 'password'} value={password} onChange={(event) => setPassword(event.target.value)} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} placeholder={mode === 'login' ? 'Digite sua senha' : 'No mínimo 10 caracteres'} minLength={mode === 'login' ? undefined : 10} maxLength={128} required />
                      <button type="button" className="auth-password-toggle" onClick={() => setVisiblePassword((value) => !value)} aria-label={visiblePassword ? 'Ocultar senha' : 'Mostrar senha'}>{visiblePassword ? 'Ocultar' : 'Mostrar'}</button>
                    </div>
                  </label>
                )}
                {(mode === 'register' || mode === 'reset') && (
                  <label className="auth-field">
                    <span>Confirmar senha</span>
                    <input type={visiblePassword ? 'text' : 'password'} value={confirmation} onChange={(event) => setConfirmation(event.target.value)} autoComplete="new-password" placeholder="Digite a senha novamente" minLength={10} maxLength={128} required />
                  </label>
                )}
                {mode === 'login' && (
                  <div className="auth-inline-row">
                    <span>Protegido por sessão segura</span>
                    <button type="button" onClick={() => changeMode('forgot')}>Esqueceu a senha?</button>
                  </div>
                )}
                {error && <p className="auth-feedback auth-feedback-error" role="alert">{error}</p>}
                {message && <p className="auth-feedback auth-feedback-success" role="status">{message}</p>}
                <button className="auth-submit" type="submit" disabled={busy}>
                  {busy ? <><span className="auth-spinner" /> Aguarde…</> :
                    mode === 'login' ? 'Entrar no Klod' :
                    mode === 'register' ? 'Criar minha conta' :
                    mode === 'forgot' ? 'Enviar link de recuperação' :
                    mode === 'resend' ? 'Reenviar confirmação' : 'Salvar nova senha'}
                  {!busy && <span>↗</span>}
                </button>
                {mode === 'register' && <p className="auth-password-hint">Use pelo menos 10 caracteres. Você confirmará seu endereço antes do primeiro acesso.</p>}
              </form>
            )}

            {mode === 'sent' && (
              <div className="auth-state-card">
                <div className="auth-state-icon">✉</div>
                <p>Um e-mail com o link de confirmação foi solicitado para:</p>
                <strong>{sentAddress}</strong>
                <p className="auth-password-hint">Abra o link no mesmo dispositivo para ativar a conta. Verifique também spam e promoções.</p>
                {message && <p className="auth-feedback auth-feedback-success" role="status">{message}</p>}
                {error && <p className="auth-feedback auth-feedback-error" role="alert">{error}</p>}
                <button className="auth-submit" type="button" onClick={() => void resend()} disabled={busy}>{busy ? 'Enviando…' : 'Reenviar e-mail'} <span>↗</span></button>
              </div>
            )}

            {mode === 'verify' && (
              <div className="auth-state-card">
                <div className="auth-state-icon">{busy ? <span className="auth-spinner" /> : '✓'}</div>
                <p>{busy ? 'Validando seu link de confirmação…' : 'Não foi possível validar este link.'}</p>
                {error && <p className="auth-feedback auth-feedback-error" role="alert">{error}</p>}
                {!busy && <button className="auth-submit" type="button" onClick={() => changeMode('resend')}>Solicitar novo link <span>↗</span></button>}
              </div>
            )}

            {mode === 'reset-done' && (
              <div className="auth-state-card">
                <div className="auth-state-icon">✓</div>
                <p>Sua senha foi alterada. Entre para acessar suas conversas e projetos.</p>
                <button className="auth-submit" type="button" onClick={() => changeMode('login')}>Ir para login <span>↗</span></button>
              </div>
            )}

            {!['login', 'register'].includes(mode) && mode !== 'verify' && mode !== 'sent' && mode !== 'reset-done' && (
              <button className="auth-back" type="button" onClick={() => changeMode('login')}>← Voltar para entrar</button>
            )}

            {mode === 'login' && (
              <div className="auth-footnote">
                <span>Novo por aqui?</span>
                <button type="button" onClick={() => changeMode('register')}>Crie sua conta</button>
              </div>
            )}
            {mode === 'register' && (
              <div className="auth-footnote"><span>Já tem uma conta?</span><button type="button" onClick={() => changeMode('login')}>Entrar</button></div>
            )}
          </div>
          <div className="auth-security-note"><span>⌑</span> Seus dados e projetos ficam vinculados à sua conta.</div>
          <div className="auth-mobile-foot">KLOD · CONSTRUA COM INTENÇÃO</div>
        </section>
      </div>
    </main>
  )
}
