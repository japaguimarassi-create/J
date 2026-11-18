import { expect, test } from '@playwright/test'

async function mockPublicAuth(page) {
  await page.route('**/health', (route) => route.fulfill({ json: { ok: true, model_available: false } }))
  await page.route('**/v1/model', (route) => route.fulfill({ json: { available: false, training_steps: 0, parameter_count: 0 } }))
  await page.route('**/v1/auth/me', (route) => route.fulfill({ status: 401, json: { detail: 'Authentication required' } }))
}

test('mobile email login is the initial screen and fits the viewport', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await mockPublicAuth(page)
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Bem-vindo de volta' })).toBeVisible()
  await expect(page.getByLabel('Endereço de e-mail')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Entrar no Klod' })).toBeVisible()

  const layout = await page.evaluate(() => {
    const email = document.querySelector<HTMLInputElement>('.auth-field input[type="email"]')
    const button = document.querySelector<HTMLElement>('.auth-submit')
    return {
      width: window.innerWidth,
      scrollWidth: document.documentElement.scrollWidth,
      emailHeight: email?.getBoundingClientRect().height || 0,
      buttonHeight: button?.getBoundingClientRect().height || 0,
      googleScript: [...document.scripts].some((script) => script.src.includes('accounts.google.com')),
    }
  })
  expect(layout.scrollWidth).toBeLessThanOrEqual(layout.width)
  expect(layout.emailHeight).toBeGreaterThanOrEqual(48)
  expect(layout.buttonHeight).toBeGreaterThanOrEqual(48)
  expect(layout.googleScript).toBe(false)
  await page.screenshot({ path: 'test-results/klod-mobile-auth.png', fullPage: true })
})

test('mobile registration shows email verification state', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await mockPublicAuth(page)
  await page.route('**/v1/auth/register', (route) => route.fulfill({
    json: { message: 'Se o endereço puder receber uma confirmação, enviaremos um link para ativar a conta.' },
  }))
  await page.goto('/')
  await page.getByRole('tab', { name: 'Criar conta' }).click()
  await expect(page.getByRole('heading', { name: 'Crie sua conta' })).toBeVisible()
  await page.getByLabel('Seu nome').fill('Klod Test')
  await page.getByLabel('Endereço de e-mail').fill('user@example.com')
  await page.getByLabel('Senha', { exact: true }).fill('correct-horse-battery')
  await page.getByLabel('Confirmar senha').fill('correct-horse-battery')
  await page.getByRole('button', { name: 'Criar minha conta' }).click()
  await expect(page.getByRole('heading', { name: 'Confira sua caixa de entrada' })).toBeVisible()
  await expect(page.getByText('user@example.com')).toBeVisible()
})

test('forgot password keeps the email field and gives a neutral confirmation', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await mockPublicAuth(page)
  await page.route('**/v1/auth/forgot-password', (route) => route.fulfill({
    json: { message: 'Se existir uma conta associada ao endereço, enviaremos instruções para redefinir a senha.' },
  }))
  await page.goto('/')
  await page.getByRole('button', { name: 'Esqueceu a senha?' }).click()
  await expect(page.getByRole('heading', { name: 'Recuperar acesso' })).toBeVisible()
  await page.getByLabel('Endereço de e-mail').fill('user@example.com')
  await page.getByRole('button', { name: 'Enviar link de recuperação' }).click()
  await expect(page.getByRole('status')).toContainText('Se existir uma conta associada')
})
