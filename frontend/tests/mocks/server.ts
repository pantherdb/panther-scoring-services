import { setupServer } from 'msw/node'

import { handlers } from '@/mocks/handlers'

// Tests override a handler with server.use(...); setup.ts resets after each test.
export const server = setupServer(...handlers)
