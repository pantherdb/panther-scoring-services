import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { renderRoute } from '../utils/render'

describe('routes', () => {
  it('shows the home page inside the shell at /', () => {
    renderRoute('/')

    expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 2, name: /coding snp/i })).toBeInTheDocument()
  })

  it('shows the not-found page, still inside the shell, for an unknown URL', () => {
    renderRoute('/does-not-exist')

    expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 2, name: /not found/i })).toBeInTheDocument()
    expect(screen.getByRole('link')).toHaveAttribute('href', '/')
  })

  it('goes back home from the not-found page', async () => {
    const { user, router } = renderRoute('/does-not-exist')

    await user.click(screen.getByRole('link'))

    expect(router.state.location.pathname).toBe('/')
    expect(screen.getByRole('heading', { level: 2, name: /coding snp/i })).toBeInTheDocument()
  })

  it('shows no build details on the not-found page', () => {
    renderRoute('/does-not-exist')

    expect(screen.getByRole('main').textContent).not.toMatch(
      /localhost|:\d{4,5}\b|VITE_|API_PROXY|npm |npx /
    )
  })
})
