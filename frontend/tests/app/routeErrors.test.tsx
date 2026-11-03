import { screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type * as Home from '@/features/home'
import type * as Versions from '@/features/versions'

import { renderRoute } from '../utils/render'

// Which part of the app throws while rendering. The real route table is used, with the home
// page or the footer's versions swapped for ones that can throw.
const fail = vi.hoisted(() => ({ page: false, footer: false }))

vi.mock('@/features/home', async importOriginal => {
  const original = await importOriginal<typeof Home>()
  return {
    ...original,
    HomePage: () => {
      if (fail.page) throw new Error('page broke at http://localhost:4173/assets/index.js:1:2')
      return <original.HomePage />
    },
  }
})

vi.mock('@/features/versions', async importOriginal => {
  const original = await importOriginal<typeof Versions>()
  return {
    ...original,
    AppVersions: () => {
      if (fail.footer) throw new Error('footer broke at http://localhost:4173/assets/index.js:3:4')
      return <original.AppVersions />
    },
  }
})

// What React Router's own error screen shows, and what an error's details look like.
const DEVELOPER_SCREEN = /hey developer|unexpected application error|errorElement/i
const ERROR_DETAILS = /broke|localhost|:\d{4,5}\b|index\.js|at /

beforeEach(() => {
  // React and React Router log a caught render error with console.error; keep the output clean.
  vi.spyOn(console, 'error').mockImplementation(() => {})
  vi.spyOn(console, 'warn').mockImplementation(() => {})
})

afterEach(() => {
  fail.page = false
  fail.footer = false
  vi.restoreAllMocks()
  vi.unstubAllEnvs()
})

describe('route errors', () => {
  it('shows the home page, header and footer when nothing throws', async () => {
    renderRoute('/')

    expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 2, name: /coding snp/i })).toBeInTheDocument()
    expect(await within(screen.getByRole('contentinfo')).findAllByRole('term')).not.toHaveLength(0)
    expect(screen.queryByRole('heading', { name: /went wrong/i })).not.toBeInTheDocument()
  })

  it('shows the error page inside the shell when a page throws, with no details', async () => {
    fail.page = true
    renderRoute('/')

    const main = screen.getByRole('main')
    expect(within(main).getByRole('heading', { level: 2, name: /went wrong/i })).toBeInTheDocument()
    expect(within(main).getByRole('link', { name: /home/i })).toHaveAttribute('href', '/')
    expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument()
    expect(await within(screen.getByRole('contentinfo')).findAllByRole('term')).not.toHaveLength(0)
    expect(document.body.textContent).not.toMatch(DEVELOPER_SCREEN)
    expect(main.textContent).not.toMatch(ERROR_DETAILS)
  })

  it('goes home from the error page, and the home page then shows', async () => {
    fail.page = true
    const { router, user } = renderRoute('/csnp')
    expect(screen.queryByRole('heading', { name: /went wrong/i })).not.toBeInTheDocument()

    await router.navigate('/')
    expect(await screen.findByRole('heading', { name: /went wrong/i })).toBeInTheDocument()

    fail.page = false
    await user.click(screen.getByRole('link', { name: /home/i }))
    expect(
      await screen.findByRole('heading', { level: 2, name: /coding snp/i })
    ).toBeInTheDocument()
  })

  it('keeps the header when the layout itself throws, with no details', () => {
    fail.footer = true
    renderRoute('/')

    expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument()
    const main = screen.getByRole('main')
    expect(within(main).getByRole('heading', { level: 2, name: /went wrong/i })).toBeInTheDocument()
    expect(within(main).getByRole('link', { name: /home/i })).toHaveAttribute('href', '/')
    expect(document.body.textContent).not.toMatch(DEVELOPER_SCREEN)
    expect(document.body.textContent).not.toMatch(ERROR_DETAILS)
  })

  it('logs the error with console.warn in development', () => {
    vi.stubEnv('DEV', true)
    fail.page = true
    renderRoute('/')

    expect(console.warn).toHaveBeenCalledWith(expect.any(String), expect.any(Error))
  })

  it('logs nothing with console.warn outside development', () => {
    vi.stubEnv('DEV', false)
    fail.page = true
    renderRoute('/')

    expect(screen.getByRole('heading', { name: /went wrong/i })).toBeInTheDocument()
    expect(console.warn).not.toHaveBeenCalled()
  })
})
