import { describe, expect, it } from 'vitest'

import { api } from '@/app/api/api'
import { makeStore } from '@/app/store'

describe('store', () => {
  it('starts with the API slice and nothing else', () => {
    const state = makeStore().getState()

    expect(Object.keys(state)).toEqual([api.reducerPath])
  })

  it('gives each call a fresh store', () => {
    expect(makeStore()).not.toBe(makeStore())
  })
})
