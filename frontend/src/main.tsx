import '@/index.css'

import { MantineProvider } from '@mantine/core'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { Provider } from 'react-redux'
import { createBrowserRouter } from 'react-router'
import { RouterProvider } from 'react-router/dom'

import { isApiMocked } from '@/app/mocking'
import { routes } from '@/app/router'
import { makeStore } from '@/app/store'
import { cssVariablesResolver, theme } from '@/app/theme'

async function startMocking() {
  // A constant in a build, so builds without mocking drop MSW entirely.
  if (!isApiMocked()) return
  const { worker } = await import('@/mocks/browser')
  await worker.start({
    onUnhandledFrame: 'bypass',
    // Under the base path, where Vite copied it from public/.
    serviceWorker: { url: `${import.meta.env.BASE_URL}mockServiceWorker.js` },
  })
}

const store = makeStore()
// The base path the site was built for (BASE_PATH in vite.config.ts), so routes and links work
// under a project page such as /panther-scoring-services/.
const router = createBrowserRouter(routes, { basename: import.meta.env.BASE_URL })

await startMocking()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Provider store={store}>
      <MantineProvider theme={theme} cssVariablesResolver={cssVariablesResolver}>
        <RouterProvider router={router} />
      </MantineProvider>
    </Provider>
  </StrictMode>
)
