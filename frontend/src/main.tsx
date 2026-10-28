import '@/index.css'

import { MantineProvider } from '@mantine/core'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { Provider } from 'react-redux'
import { createBrowserRouter } from 'react-router'
import { RouterProvider } from 'react-router/dom'

import { routes } from '@/app/router'
import { makeStore } from '@/app/store'
import { theme } from '@/app/theme'

async function startMocking() {
  // Replaced at build time, so builds without mocking drop MSW entirely.
  if (import.meta.env.VITE_API_MOCKING !== 'on') return
  const { worker } = await import('@/mocks/browser')
  await worker.start({ onUnhandledFrame: 'bypass' })
}

const store = makeStore()
const router = createBrowserRouter(routes)

await startMocking()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Provider store={store}>
      <MantineProvider theme={theme}>
        <RouterProvider router={router} />
      </MantineProvider>
    </Provider>
  </StrictMode>
)
