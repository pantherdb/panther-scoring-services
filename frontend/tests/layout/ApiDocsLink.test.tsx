import { screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { AppLayout } from '@/layout/AppLayout'

import { renderRoute } from '../utils/render'

const routes = [{ element: <AppLayout />, children: [{ index: true, element: <p>Page body</p> }] }]

function footer() {
  return within(screen.getByRole('contentinfo'))
}

afterEach(() => {
  vi.unstubAllEnvs()
})

describe('the API docs link in the footer', () => {
  it('links to the relative /api/v1/docs when the API URL is empty', () => {
    vi.stubEnv('VITE_API_MOCKING', 'off')
    vi.stubEnv('VITE_API_BASE_URL', '')
    renderRoute('/', { routes })

    expect(footer().getByRole('link', { name: /api docs/i })).toHaveAttribute(
      'href',
      '/api/v1/docs'
    )
  })

  it("links to the API's own docs when the API URL is set", () => {
    vi.stubEnv('VITE_API_MOCKING', 'off')
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.org/')
    renderRoute('/', { routes })

    expect(footer().getByRole('link', { name: /api docs/i })).toHaveAttribute(
      'href',
      'https://api.example.org/api/v1/docs'
    )
  })

  it('is hidden on mocked API answers', () => {
    vi.stubEnv('VITE_API_MOCKING', 'on')
    renderRoute('/', { routes })

    expect(screen.getByRole('contentinfo')).toBeInTheDocument()
    expect(footer().queryByRole('link', { name: /api docs/i })).not.toBeInTheDocument()
  })
})
