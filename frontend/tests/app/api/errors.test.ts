import { describe, expect, it } from 'vitest'

import { isUnreachable } from '@/app/api/errors'

const PROBLEM_500 = {
  type: 'about:blank',
  title: 'Internal Server Error',
  status: 500,
  detail: 'x',
}

describe('isUnreachable', () => {
  it.each([
    ['the network failed', { status: 'FETCH_ERROR', error: 'TypeError: Failed to fetch' }],
    ['the request timed out', { status: 'TIMEOUT_ERROR', error: 'AbortError' }],
    ['the dev proxy had no API behind it', { status: 500, data: null }],
    ['a server in between answered 502', { status: 502, data: 'Bad Gateway' }],
    [
      'a server in between answered 503 in HTML',
      { status: 'PARSING_ERROR', originalStatus: 503, data: '<html>', error: 'SyntaxError' },
    ],
  ])('is true when %s', (_, error) => {
    expect(isUnreachable(error)).toBe(true)
  })

  it.each([
    ["the API's own 500", { status: 500, data: PROBLEM_500 }],
    ["the API's 501", { status: 501, data: { ...PROBLEM_500, status: 501 } }],
    ['a 404', { status: 404, data: { ...PROBLEM_500, status: 404 } }],
    ['a 422', { status: 422, data: { ...PROBLEM_500, status: 422, errors: [] } }],
    [
      'a 200 that was not JSON',
      { status: 'PARSING_ERROR', originalStatus: 200, data: 'x', error: 'SyntaxError' },
    ],
    ['not an error object', 'Failed'],
    ['null', null],
  ])('is false for %s', (_, error) => {
    expect(isUnreachable(error)).toBe(false)
  })
})
