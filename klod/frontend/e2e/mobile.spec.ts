import { expect, test } from '@playwright/test'

test('mobile home renders without horizontal overflow and includes styled layout', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await expect(page.getByRole('heading', { name: /o que vamos construir hoje/i })).toBeVisible()
  await expect(page.getByText('Login Google aguardando configuração OAuth.')).toBeVisible()

  const layout = await page.evaluate(() => ({
    width: window.innerWidth,
    scrollWidth: document.documentElement.scrollWidth,
    orbWidth: getComputedStyle(document.querySelector('.orb')!).width,
    orbBackground: getComputedStyle(document.querySelector('.orb')!).backgroundImage,
    sidebarWidth: getComputedStyle(document.querySelector('.sidebar')!).width,
  }))
  expect(layout.scrollWidth).toBeLessThanOrEqual(layout.width)
  expect(layout.orbWidth).toBe('57px')
  expect(layout.orbBackground).not.toBe('none')
  expect(layout.sidebarWidth).toContain('292px')
  await page.screenshot({ path: 'test-results/klod-mobile-home.png', fullPage: true })
})

test('mobile navigation opens and closes', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await page.getByRole('button', { name: 'Abrir menu' }).click()
  await expect(page.getByTestId('sidebar')).toHaveClass(/sidebar-open/)
  await page.getByTestId('sidebar').getByRole('button', { name: 'Fechar menu' }).click()
  await expect(page.getByTestId('sidebar')).not.toHaveClass(/sidebar-open/)
})

test('suggested prompt populates the composer', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await page.getByRole('button', { name: /entender a arquitetura/i }).click()
  await expect(page.locator('.composer textarea')).toHaveValue('Como funciona a arquitetura neural do Klod?')
})
