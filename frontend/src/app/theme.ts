import { createTheme, type MantineColorsTuple } from '@mantine/core'

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
