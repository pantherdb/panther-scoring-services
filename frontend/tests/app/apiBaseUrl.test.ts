import { afterEach, describe, expect, it, vi } from 'vitest'

import { apiBaseUrl } from '@/app/apiBaseUrl'

afterEach(() => {
  vi.unstubAllEnvs()
})

describe('apiBaseUrl', () => {
  it.each(['', '  '])('is the relative /api/v1 when the API URL is %j', value => {
    vi.stubEnv('VITE_API_BASE_URL', value)

    expect(apiBaseUrl()).toBe('/api/v1')
  })

  it('is the relative /api/v1 when the API URL is unset', () => {
    vi.stubEnv('VITE_API_BASE_URL', undefined)

    expect(apiBaseUrl()).toBe('/api/v1')
  })

  it('puts /api/v1 after the API URL when it is set', () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.org')

    expect(apiBaseUrl()).toBe('https://api.example.org/api/v1')
  })

  it.each(['https://api.example.org/', 'https://api.example.org//'])(
    'ignores a trailing slash in %j',
    value => {
      vi.stubEnv('VITE_API_BASE_URL', value)

      expect(apiBaseUrl()).toBe('https://api.example.org/api/v1')
    }
  )

  it('keeps a path before /api/v1', () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://example.org/panther')

    expect(apiBaseUrl()).toBe('https://example.org/panther/api/v1')
  })
})
