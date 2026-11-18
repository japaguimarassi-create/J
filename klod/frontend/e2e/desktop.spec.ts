import { expect, test } from '@playwright/test'

test('desktop layout renders the sidebar and main workspace without overflow', async ({ page }) => {
  await page.setViewportSize({ width: 1365, height: 900 })
  await page.goto('/')
  await expect(page.getByRole('heading', { name: /o que vamos construir hoje/i })).toBeVisible()
  await expect(page.getByTestId('sidebar')).toBeVisible()
  const layout = await page.evaluate(() => ({
    width: window.innerWidth,
    scrollWidth: document.documentElement.scrollWidth,
    sidebarWidth: getComputedStyle(document.querySelector('.sidebar')!).width,
    headingColor: getComputedStyle(document.querySelector('.welcome h1')!).color,
  }))
  expect(layout.scrollWidth).toBeLessThanOrEqual(layout.width)
  expect(layout.sidebarWidth).toBe('272px')
  expect(layout.headingColor).not.toBe('rgba(0, 0, 0, 0)')
})
