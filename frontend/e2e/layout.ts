import { expect, type Page } from '@playwright/test'

/** The page fits the window's width: nothing makes it scroll sideways, as on a phone. */
export async function expectNoSidewaysScroll(page: Page) {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth
  )
  expect(overflow).toBe(0)
}
