import { afterEach, describe, expect, it, vi } from 'vitest'

import { isApiMocked } from '@/app/mocking'

afterEach(() => {
  vi.unstubAllEnvs()
})

describe('isApiMocked', () => {
  it('is true when the mode turns API mocking on', () => {
    vi.stubEnv('VITE_API_MOCKING', 'on')

    expect(isApiMocked()).toBe(true)
  })

  it.each(['off', ''])('is false when API mocking is %j', value => {
    vi.stubEnv('VITE_API_MOCKING', value)

    expect(isApiMocked()).toBe(false)
  })
})
