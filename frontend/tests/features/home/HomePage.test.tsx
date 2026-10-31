import { screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { renderRoute } from '../../utils/render'

describe('the home page', () => {
  it('links to the cSNP form from its coding SNP section', () => {
    renderRoute('/')

    const main = within(screen.getByRole('main'))
    expect(main.getByRole('heading', { level: 2, name: /coding snp/i })).toBeInTheDocument()
    expect(main.getByRole('link', { name: /score coding snps/i })).toHaveAttribute('href', '/csnp')
  })

  it('links to the refmap form from its protein ID mapping section', () => {
    renderRoute('/')

    const main = within(screen.getByRole('main'))
    expect(main.getByRole('heading', { level: 2, name: /protein id mapping/i })).toBeInTheDocument()
    expect(main.getByRole('link', { name: /map protein ids/i })).toHaveAttribute('href', '/refmap')
  })

  it('keeps the scoring tools check', () => {
    renderRoute('/')

    expect(
      within(screen.getByRole('main')).getByRole('button', { name: /check the scoring tools/i })
    ).toBeEnabled()
  })
})
