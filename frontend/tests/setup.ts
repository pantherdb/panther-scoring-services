import '@testing-library/jest-dom/vitest'

import { cleanup } from '@testing-library/react'
import { afterAll, afterEach, beforeAll } from 'vitest'

import { resetJobs } from '@/mocks/jobs'

import { server } from './mocks/server'

// jsdom has no matchMedia. Report reduced motion so Mantine transitions take no
// time and can't fire after a test has finished.
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string): MediaQueryList => ({
    matches: /prefers-reduced-motion:\s*reduce/.test(query),
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
})

// jsdom has no ResizeObserver and no scrollIntoView, and Mantine's Select needs both: it
// crashes on render without ResizeObserver, and scrolls the active option into view as the
// user moves through the options. jsdom has no layout to observe or scroll, so both do nothing.
globalThis.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
}
Element.prototype.scrollIntoView = () => {}

// The app calls a relative /api/v1, as it must in the browser. A browser's Request resolves a
// relative URL against the page; Node's, which jsdom leaves in place, throws "Invalid URL".
// Resolve it against jsdom's location, as the browser would.
const NodeRequest = globalThis.Request
globalThis.Request = class extends NodeRequest {
  constructor(input: RequestInfo | URL, init?: RequestInit) {
    super(typeof input === 'string' ? new URL(input, window.location.href) : input, init)
  }
}

// An API call without a handler fails the test instead of reaching the network.
beforeAll(() => server.listen({ onUnhandledFrame: 'error' }))
afterEach(() => {
  cleanup()
  server.resetHandlers()
  resetJobs()
})
afterAll(() => server.close())
