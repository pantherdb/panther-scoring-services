import { screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { renderRoute } from '../utils/render'

afterEach(() => {
  vi.unstubAllEnvs()
})

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

  it('marks the not-found page as mock data on mocked API answers', () => {
    vi.stubEnv('VITE_API_MOCKING', 'on')
    renderRoute('/does-not-exist')

    expect(screen.getByRole('heading', { level: 2, name: /not found/i })).toBeInTheDocument()
    expect(screen.getByRole('region', { name: /mock data/i })).toBeInTheDocument()
  })

  it('shows no mock data banner on the not-found page with the real API', () => {
    vi.stubEnv('VITE_API_MOCKING', 'off')
    renderRoute('/does-not-exist')

    expect(screen.getByRole('heading', { level: 2, name: /not found/i })).toBeInTheDocument()
    expect(screen.queryByRole('region', { name: /mock data/i })).not.toBeInTheDocument()
  })

  it('shows no build details on the not-found page', () => {
    renderRoute('/does-not-exist')

    expect(screen.getByRole('main').textContent).not.toMatch(
      /localhost|:\d{4,5}\b|VITE_|API_PROXY|npm |npx /
    )
  })
})
