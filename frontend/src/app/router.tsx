import type { RouteObject } from 'react-router'

import { NotFoundPage } from '@/components/NotFoundPage'
import { CsnpPage } from '@/features/csnp'
import { HomePage } from '@/features/home'
import { JobPage } from '@/features/jobs'
import { RefmapPage } from '@/features/refmap'
import { AppLayout } from '@/layout/AppLayout'

// The route table, shared by the browser router in main.tsx and the memory
// router in tests.
export const routes: RouteObject[] = [
  {
    element: <AppLayout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'csnp', element: <CsnpPage /> },
      { path: 'refmap', element: <RefmapPage /> },
      { path: 'jobs/:id', element: <JobPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]
