import { screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { AppLayout } from '@/layout/AppLayout'

import { renderRoute } from '../utils/render'

const routes = [{ element: <AppLayout />, children: [{ index: true, element: <p>Page body</p> }] }]

const BUILD_DETAILS = /localhost|:\d{4,5}\b|VITE_|API_PROXY|MSW|npm |npx |\/usr\/|[A-Z]:\\/

afterEach(() => {
  vi.unstubAllEnvs()
})

describe('AppLayout', () => {
  it('shows the app title as the top-level heading', () => {
    renderRoute('/', { routes })

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/^PANTHER Scoring$/)
  })

  it('renders the page inside the main region', () => {
    renderRoute('/', { routes })

    expect(screen.getByRole('main')).toHaveTextContent('Page body')
  })

  describe('on mocked API answers', () => {
    it('marks the page as mock data, not from the scoring service', () => {
      vi.stubEnv('VITE_API_MOCKING', 'on')
      renderRoute('/', { routes })

      const banner = screen.getByRole('region', { name: /mock data/i })
      expect(banner).toHaveTextContent(/mock data/i)
      expect(banner).toHaveTextContent(/nothing on this page comes from the scoring service/i)
      expect(banner.textContent).not.toMatch(BUILD_DETAILS)
    })

    it('still shows the title and the page, with the banner outside the main region', () => {
      vi.stubEnv('VITE_API_MOCKING', 'on')
      renderRoute('/', { routes })

      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/^PANTHER Scoring$/)
      expect(screen.getByRole('main')).toHaveTextContent('Page body')
      expect(within(screen.getByRole('main')).queryByText(/mock data/i)).not.toBeInTheDocument()
    })
  })

  describe('with the real API', () => {
    it.each(['off', ''])('shows no mock data banner when API mocking is %j', value => {
      vi.stubEnv('VITE_API_MOCKING', value)
      renderRoute('/', { routes })

      expect(screen.getByRole('main')).toHaveTextContent('Page body')
      expect(screen.queryByRole('region', { name: /mock data/i })).not.toBeInTheDocument()
      expect(screen.queryByText(/mock data/i)).not.toBeInTheDocument()
    })
  })
})
