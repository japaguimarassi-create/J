import { expect, test } from '@playwright/test'

test('desktop authentication layout stays centered and readable', async ({ page }) => {
  await page.setViewportSize({ width: 1365, height: 900 })
  await page.route('**/health', (route) => route.fulfill({ json: { ok: true, model_available: false } }))
  await page.route('**/v1/model', (route) => route.fulfill({ json: { available: false, training_steps: 0, parameter_count: 0 } }))
  await page.route('**/v1/auth/me', (route) => route.fulfill({ status: 401, json: { detail: 'Authentication required' } }))
  await page.goto('/')
  await expect(page.getByRole('heading', { name: /suas ideias/i })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Bem-vindo de volta' })).toBeVisible()
  const layout = await page.evaluate(() => {
    const frame = document.querySelector<HTMLElement>('.auth-frame')
    const card = document.querySelector<HTMLElement>('.auth-card')
    return {
      width: window.innerWidth,
      scrollWidth: document.documentElement.scrollWidth,
      frameWidth: frame?.getBoundingClientRect().width || 0,
      cardWidth: card?.getBoundingClientRect().width || 0,
      storyVisible: getComputedStyle(document.querySelector('.auth-story')!).display !== 'none',
    }
  })
  expect(layout.scrollWidth).toBeLessThanOrEqual(layout.width)
  expect(layout.frameWidth).toBeLessThanOrEqual(1120)
  expect(layout.cardWidth).toBeLessThanOrEqual(460)
  expect(layout.storyVisible).toBe(true)
})
