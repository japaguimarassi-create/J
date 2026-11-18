import { expect, test, type Page, type Route } from '@playwright/test'

async function stubAuthenticatedApi(page: Page) {
  const conversations = [
    { id: 'conversation-1', title: 'Arquitetura Klod', updated_at: '2026-11-18T10:00:00Z' },
  ]
  const messages = [
    { id: 'message-1', role: 'user', content: 'Como o Klod funciona?' },
    { id: 'message-2', role: 'assistant', content: 'O Klod usa um único agente e um runtime neural.' },
  ]
  const projects: Array<{ id: string; name: string; description: string; updated_at: string }> = []
  const files: Record<string, string> = {}

  await page.route('**/health', (route: Route) => route.fulfill({ json: { ok: true, model_available: true } }))
  await page.route('**/v1/**', async (route: Route) => {
    const request = route.request()
    const url = new URL(request.url())
    const method = request.method()

    if (url.pathname === '/v1/model') {
      await route.fulfill({ json: { available: true, training_steps: 30, parameter_count: 86000 } })
      return
    }
    if (url.pathname === '/v1/auth/me') {
      await route.fulfill({ json: { user: { id: 'user-admin', email: 'admin@klod.test', display_name: 'Admin Klod', picture: '', role: 'admin' } } })
      return
    }
    if (url.pathname === '/v1/conversations' && method === 'GET') {
      await route.fulfill({ json: { conversations } })
      return
    }
    if (url.pathname === '/v1/conversations' && method === 'POST') {
      const body = request.postDataJSON() as { title: string }
      const conversation = { id: 'conversation-created', title: body.title, updated_at: new Date().toISOString() }
      conversations.unshift(conversation)
      await route.fulfill({ json: { conversation } })
      return
    }
    if (url.pathname === '/v1/conversations/conversation-1' && method === 'GET') {
      await route.fulfill({ json: { conversation: { ...conversations[0], messages } } })
      return
    }
    if (url.pathname === '/v1/chat' && method === 'POST') {
      await route.fulfill({ json: { response: 'Resposta de teste do Klod.', conversation_id: 'conversation-created', training_steps: 30, parameter_count: 86000 } })
      return
    }
    if (url.pathname === '/v1/projects' && method === 'GET') {
      await route.fulfill({ json: { projects } })
      return
    }
    if (url.pathname === '/v1/projects' && method === 'POST') {
      const body = request.postDataJSON() as { name: string; description: string }
      const project = { id: 'project-1', name: body.name, description: body.description, updated_at: new Date().toISOString() }
      projects.unshift(project)
      await route.fulfill({ json: { project } })
      return
    }
    if (url.pathname === '/v1/projects/project-1/files' && method === 'GET') {
      const path = url.searchParams.get('path')
      if (path) {
        await route.fulfill({ json: { path, content: files[path] || '' } })
      } else {
        await route.fulfill({ json: { files: Object.entries(files).map(([filePath, content]) => ({ path: filePath, size: content.length })) } })
      }
      return
    }
    if (url.pathname === '/v1/projects/project-1/files' && method === 'PUT') {
      const body = request.postDataJSON() as { path: string; content: string }
      files[body.path] = body.content
      await route.fulfill({ json: { ok: true, path: body.path } })
      return
    }
    if (url.pathname === '/v1/admin/overview') {
      await route.fulfill({ json: { users: 4, conversations: 12, projects: 3 } })
      return
    }
    if (url.pathname === '/v1/admin/users') {
      await route.fulfill({ json: { users: [{ id: 'user-admin', email: 'admin@klod.test', display_name: 'Admin Klod', role: 'admin', created_at: '2026-11-18T10:00:00Z' }] } })
      return
    }
    await route.fulfill({ status: 404, json: { detail: 'Mock endpoint not found' } })
  })
}

test('restores a saved conversation from the authenticated account', async ({ page }) => {
  await stubAuthenticatedApi(page)
  await page.goto('/')
  await expect(page.getByText('Admin Klod')).toBeVisible()
  await expect(page.getByText('Como o Klod funciona?')).toBeVisible()
  await expect(page.getByText('O Klod usa um único agente e um runtime neural.')).toBeVisible()
})

test('creates a project, opens its coder workspace and saves a file', async ({ page }) => {
  await stubAuthenticatedApi(page)
  await page.goto('/')
  await page.getByRole('button', { name: 'Projetos' }).click()
  await expect(page.getByRole('heading', { name: 'Seus projetos' })).toBeVisible()
  await page.getByLabel('Novo projeto').fill('Projeto de teste')
  await page.locator('.project-create textarea').fill('Workspace de aceitação')
  await page.getByRole('button', { name: 'Criar projeto' }).click()
  await expect(page.getByRole('heading', { name: 'Projeto de teste' })).toBeVisible()
  await page.getByRole('button', { name: /abrir no coder/i }).click()
  await expect(page.getByRole('heading', { name: 'Projeto de teste' })).toBeVisible()
  await page.getByRole('textbox', { name: 'Caminho do arquivo' }).fill('src/main.py')
  await page.getByRole('textbox', { name: 'Conteúdo do arquivo' }).fill("print('hello from Klod')")
  await page.getByRole('button', { name: 'Salvar arquivo' }).click()
  await expect(page.getByText('Arquivo salvo no workspace do projeto.')).toBeVisible()
  await expect(page.getByRole('button', { name: 'src/main.py' })).toBeVisible()
})

test('renders admin metrics and user directory for an admin identity', async ({ page }) => {
  await stubAuthenticatedApi(page)
  await page.goto('/')
  await page.getByRole('button', { name: 'Administração' }).click()
  await expect(page.getByRole('heading', { name: 'Administração' })).toBeVisible()
  await expect(page.getByText('admin@klod.test')).toBeVisible()
  await expect(page.getByText('12', { exact: true })).toBeVisible()
})
