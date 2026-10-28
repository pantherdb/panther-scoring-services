import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { AppLayout } from '@/layout/AppLayout'

import { renderRoute } from '../utils/render'

const routes = [{ element: <AppLayout />, children: [{ index: true, element: <p>Page body</p> }] }]

describe('AppLayout', () => {
  it('shows the app title as the top-level heading', () => {
    renderRoute('/', { routes })

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('PANTHER cSNP Scoring')
  })

  it('renders the page inside the main region', () => {
    renderRoute('/', { routes })

    expect(screen.getByRole('main')).toHaveTextContent('Page body')
  })
})
