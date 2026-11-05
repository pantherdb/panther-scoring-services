import { screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { renderRoute } from '../../utils/render'

function main() {
  return within(screen.getByRole('main'))
}

// A service's card: the section its heading names.
function card(name: RegExp) {
  return within(main().getByRole('heading', { level: 2, name }).closest('section')!)
}

describe('the home page', () => {
  it('shows the four services in priority order', () => {
    renderRoute('/')

    expect(
      main()
        .getAllByRole('heading', { level: 2 })
        .map(heading => heading.textContent)
    ).toEqual(['Coding SNP impact scoring', 'Protein ID mapping', 'HMM scoring', 'Tree grafting'])
  })

  it('links to the cSNP form, with no coming-soon mark', () => {
    renderRoute('/')

    const csnp = card(/coding snp/i)
    expect(csnp.getByRole('link', { name: /score coding snps/i })).toHaveAttribute('href', '/csnp')
    expect(csnp.queryByText(/coming soon/i)).not.toBeInTheDocument()
  })

  it('links to the refmap form, and marks it coming soon', () => {
    renderRoute('/')

    const refmap = card(/protein id mapping/i)
    expect(refmap.getByRole('link', { name: /map protein ids/i })).toHaveAttribute(
      'href',
      '/refmap'
    )
    expect(refmap.getByText(/coming soon/i)).toBeInTheDocument()
  })

  it.each([
    [/hmm scoring/i, '/hmmscore'],
    [/tree grafting/i, '/treegrafter'],
  ])('marks %s coming soon, and links to its page', (name, path) => {
    renderRoute('/')

    const shown = card(name)
    expect(shown.getByText(/coming soon/i)).toBeInTheDocument()
    expect(shown.getByRole('link')).toHaveAttribute('href', path)
  })

  it('keeps the scoring tools check', () => {
    renderRoute('/')

    expect(main().getByRole('button', { name: /check the scoring tools/i })).toBeEnabled()
  })
})
