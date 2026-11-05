import { screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { renderRoute } from '../utils/render'

function main() {
  return within(screen.getByRole('main'))
}

describe('a coming-soon page', () => {
  it.each([
    ['/hmmscore', /hmm scoring/i, /hmm library/i],
    ['/treegrafter', /tree grafting/i, /family tree/i],
  ])(
    'at %s says what the service will do, that it is coming soon, and links home',
    (path, title, summary) => {
      renderRoute(path)

      expect(main().getByRole('heading', { level: 2, name: title })).toBeInTheDocument()
      expect(main().getByText(summary)).toBeInTheDocument()
      expect(main().getAllByText(/coming soon/i).length).toBeGreaterThan(0)
      expect(main().getByRole('link', { name: /back to home/i })).toHaveAttribute('href', '/')
    }
  )

  it('goes home from its link', async () => {
    const { user } = renderRoute('/hmmscore')

    await user.click(main().getByRole('link', { name: /back to home/i }))

    expect(
      await main().findByRole('heading', { level: 2, name: /coding snp/i })
    ).toBeInTheDocument()
  })
})
