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
  it('shows the four services in priority order, then the tools check, each its own section', () => {
    renderRoute('/')

    // All at one level, so the tools check isn't heard as part of the last service.
    expect(
      main()
        .getAllByRole('heading', { level: 2 })
        .map(heading => heading.textContent)
    ).toEqual([
      'Coding SNP impact scoring',
      'Protein ID mapping',
      'HMM scoring',
      'Tree grafting',
      'Scoring tools',
    ])
  })

  it('links to the cSNP form, with no coming-soon mark', () => {
    renderRoute('/')

    const csnp = card(/coding snp/i)
    expect(csnp.getByRole('link', { name: /score coding snps/i })).toHaveAttribute('href', '/csnp')
    expect(csnp.queryByText(/coming soon/i)).not.toBeInTheDocument()
  })

  it('links to the refmap form, with no coming-soon mark', () => {
    renderRoute('/')

    const refmap = card(/protein id mapping/i)
    expect(refmap.getByRole('link', { name: /map protein ids/i })).toHaveAttribute(
      'href',
      '/refmap'
    )
    expect(refmap.queryByText(/coming soon/i)).not.toBeInTheDocument()
  })

  it('links to the HMM scoring form, with no coming-soon mark', () => {
    renderRoute('/')

    const hmmscore = card(/hmm scoring/i)
    expect(hmmscore.getByRole('link', { name: /score a protein sequence/i })).toHaveAttribute(
      'href',
      '/hmmscore'
    )
    expect(hmmscore.queryByText(/coming soon/i)).not.toBeInTheDocument()
  })

  it('marks only tree grafting coming soon', () => {
    renderRoute('/')

    const marked = main()
      .getAllByRole('heading', { level: 2 })
      .filter(heading => within(heading.closest('section')!).queryByText(/coming soon/i))
      .map(heading => heading.textContent)
    expect(marked).toEqual(['Tree grafting'])
  })

  it('marks tree grafting coming soon, and links to its page', () => {
    renderRoute('/')

    const shown = card(/tree grafting/i)
    expect(shown.getByText(/coming soon/i)).toBeInTheDocument()
    expect(shown.getByRole('link')).toHaveAttribute('href', '/treegrafter')
  })

  it('keeps the scoring tools check', () => {
    renderRoute('/')

    expect(main().getByRole('button', { name: /check the scoring tools/i })).toBeEnabled()
  })
})
