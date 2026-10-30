// What a failed RTK Query request says about where it failed.

function isProblem(data: unknown) {
  return typeof data === 'object' && data !== null && 'status' in data && 'title' in data
}

/**
 * Whether a failed request never got an answer from the API: the network failed, it timed
 * out, or what answered wasn't the API. The API answers every error with problem details,
 * so a 5xx without them came from something in between: the dev server's proxy with no API
 * behind it (a 500 with an empty body), or a server answering 502, 503 or 504.
 */
export function isUnreachable(error: unknown): boolean {
  if (typeof error !== 'object' || error === null || !('status' in error)) return false
  const { status } = error
  if (status === 'FETCH_ERROR' || status === 'TIMEOUT_ERROR') return true
  if (status === 'PARSING_ERROR') {
    return (
      'originalStatus' in error &&
      typeof error.originalStatus === 'number' &&
      error.originalStatus >= 500
    )
  }
  if (typeof status !== 'number' || status < 500) return false
  return !isProblem('data' in error ? error.data : null)
}
