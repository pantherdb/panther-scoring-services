import { createTheme, type CSSVariablesResolver, type MantineColorsTuple } from '@mantine/core'

// Colours are defined once, in the @theme block of src/index.css. Mantine's ten
// shades (0-9) map to Tailwind's 50-900 steps.
function tailwindScale(name: string): MantineColorsTuple {
  return [
    `var(--color-${name}-50)`,
    `var(--color-${name}-100)`,
    `var(--color-${name}-200)`,
    `var(--color-${name}-300)`,
    `var(--color-${name}-400)`,
    `var(--color-${name}-500)`,
    `var(--color-${name}-600)`,
    `var(--color-${name}-700)`,
    `var(--color-${name}-800)`,
    `var(--color-${name}-900)`,
  ]
}

export const theme = createTheme({
  colors: { primary: tailwindScale('primary') },
  primaryColor: 'primary',
  primaryShade: 6,
  // Honour the user's reduced-motion setting. Tests report reduced motion, so
  // Mantine transitions take no time there.
  respectReducedMotion: true,
  fontFamily: 'var(--font-sans)',
  headings: { fontFamily: 'var(--font-sans)' },
})

// Mantine's own error and dimmed colours (red-6 and gray-6) are about 3.2:1 on the canvas,
// below WCAG AA's 4.5:1 for a field's error and description. Point them at our tokens:
// --color-danger is about 4.6:1, --color-ink-muted about 7.2:1. The app has no dark scheme,
// so only the light one is set. Every MantineProvider takes this, in the app and in tests.
export const cssVariablesResolver: CSSVariablesResolver = () => ({
  variables: {},
  light: {
    '--mantine-color-error': 'var(--color-danger)',
    '--mantine-color-dimmed': 'var(--color-ink-muted)',
  },
  dark: {},
})
