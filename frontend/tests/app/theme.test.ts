import { describe, expect, it } from 'vitest'

import { cssVariablesResolver, theme } from '@/app/theme'
import { mergeMantineTheme, DEFAULT_THEME } from '@mantine/core'

// jsdom computes no colours, so the contrast itself is checked in a browser
// (e2e/contrast.spec.ts). Here: the error and description colours come from our tokens.
describe('cssVariablesResolver', () => {
  const resolved = cssVariablesResolver(mergeMantineTheme(DEFAULT_THEME, theme))

  it("colours field errors with the project's danger token", () => {
    expect(resolved.light['--mantine-color-error']).toBe('var(--color-danger)')
  })

  it("colours field descriptions with the project's muted ink token", () => {
    expect(resolved.light['--mantine-color-dimmed']).toBe('var(--color-ink-muted)')
  })

  it('leaves the other variables to Mantine', () => {
    expect(Object.keys(resolved.light)).toEqual(['--mantine-color-error', '--mantine-color-dimmed'])
    expect(resolved.variables).toEqual({})
  })
})
