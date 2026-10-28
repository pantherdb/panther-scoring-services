import type { RouteObject } from 'react-router'

import { NotFoundPage } from '@/components/NotFoundPage'
import { HomePage } from '@/features/home'
import { AppLayout } from '@/layout/AppLayout'

// The route table, shared by the browser router in main.tsx and the memory
// router in tests.
export const routes: RouteObject[] = [
  {
    element: <AppLayout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]
