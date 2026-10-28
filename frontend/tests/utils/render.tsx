import { MantineProvider } from '@mantine/core'
import { render } from '@testing-library/react'
import { userEvent } from '@testing-library/user-event'
import { Provider } from 'react-redux'
// RouterProvider from 'react-router', not 'react-router/dom' as in main.tsx:
// under Vitest, 'react-router/dom' loads React Router's CommonJS build, whose
// contexts differ from the ESM build that <Outlet> and <Link> use, so nested
// routes render empty. The /dom version only adds flushSync, which tests don't use.
import { createMemoryRouter, RouterProvider, type RouteObject } from 'react-router'

import { routes as appRoutes } from '@/app/router'
import { makeStore } from '@/app/store'
import { theme } from '@/app/theme'

type Options = {
  /** Defaults to the app's own route table. */
  routes?: RouteObject[]
}

// Renders a URL with the same providers as main.tsx: a fresh store, the theme
// and a memory router.
export function renderRoute(path: string, { routes = appRoutes }: Options = {}) {
  const store = makeStore()
  const router = createMemoryRouter(routes, { initialEntries: [path] })
  const user = userEvent.setup()
  const result = render(
    <Provider store={store}>
      <MantineProvider theme={theme}>
        <RouterProvider router={router} />
      </MantineProvider>
    </Provider>
  )
  return { ...result, store, router, user }
}
