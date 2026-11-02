import type { RouteObject } from 'react-router'

import { ErrorPage } from '@/components/ErrorPage'
import { NotFoundPage } from '@/components/NotFoundPage'
import { CsnpPage } from '@/features/csnp'
import { HomePage } from '@/features/home'
import { JobPage } from '@/features/jobs'
import { RefmapPage } from '@/features/refmap'
import { AppLayout } from '@/layout/AppLayout'
import { RootError } from '@/layout/RootError'

// The route table, shared by the browser router in main.tsx and the memory
// router in tests.
//
// Every route has an error element, so a render error never reaches React Router's
// developer screen, which ships in the production bundle. A page that throws is replaced
// by ErrorPage inside the layout, so the header and footer stay. If the layout itself
// throws, RootError draws the header again around the same page.
export const routes: RouteObject[] = [
  {
    element: <AppLayout />,
    errorElement: <RootError />,
    children: [
      { index: true, element: <HomePage />, errorElement: <ErrorPage /> },
      { path: 'csnp', element: <CsnpPage />, errorElement: <ErrorPage /> },
      { path: 'refmap', element: <RefmapPage />, errorElement: <ErrorPage /> },
      { path: 'jobs/:id', element: <JobPage />, errorElement: <ErrorPage /> },
      { path: '*', element: <NotFoundPage />, errorElement: <ErrorPage /> },
    ],
  },
]
