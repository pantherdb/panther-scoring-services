import { expect, test, type Locator, type Page } from '@playwright/test'

// Untagged: the form's own checks need nothing from the API, so this runs in every mode.

// WCAG 2.1 AA, 1.4.3: normal-size text needs 4.5:1 against its background.
const AA = 4.5

// The contrast between a text's colour and the page's canvas, as WCAG computes it. Colours
// can be oklch(), so each is painted on a canvas and read back as sRGB.
async function contrastOnCanvas(page: Page, text: Locator) {
  const color = await text.evaluate(element => getComputedStyle(element).color)
  return page.evaluate(color => {
    const context = document.createElement('canvas').getContext('2d', {
      willReadFrequently: true,
    })!
    const rgb = (css: string) => {
      context.clearRect(0, 0, 1, 1)
      context.fillStyle = css
      context.fillRect(0, 0, 1, 1)
      return Array.from(context.getImageData(0, 0, 1, 1).data.slice(0, 3))
    }
    const luminance = (css: string) => {
      const [r, g, b] = rgb(css).map(value => {
        const c = value / 255
        return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
      })
      return 0.2126 * r! + 0.7152 * g! + 0.0722 * b!
    }
    const canvas = getComputedStyle(document.body).backgroundColor
    const [light, dark] = [luminance(color), luminance(canvas)].sort((a, b) => b - a)
    return (light! + 0.05) / (dark! + 0.05)
  }, color)
}

// A field's description and error, found through the ids its aria-describedby names.
async function describedBy(field: Locator) {
  const ids = (await field.getAttribute('aria-describedby'))?.split(/\s+/) ?? []
  return field.page().locator(ids.map(id => `[id="${id}"]`).join(', '))
}

test('field descriptions and errors meet WCAG AA contrast', async ({ page }) => {
  await page.goto('/csnp')
  const sequence = page.getByRole('main').getByLabel(/protein sequence/i)
  await expect(sequence).toBeVisible()

  // Before submitting: the description alone.
  const before = await describedBy(sequence)
  await expect(before).toHaveCount(1)
  expect(await contrastOnCanvas(page, before.first())).toBeGreaterThanOrEqual(AA)

  // Submitting the empty form puts an error on the field, beside its description.
  await page
    .getByRole('main')
    .getByRole('button', { name: /score substitutions/i })
    .click()
  await expect(sequence).toHaveAttribute('aria-invalid', 'true')
  const after = await describedBy(sequence)
  await expect(after).toHaveCount(2)
  for (const text of await after.all()) {
    expect(await contrastOnCanvas(page, text)).toBeGreaterThanOrEqual(AA)
  }
})
