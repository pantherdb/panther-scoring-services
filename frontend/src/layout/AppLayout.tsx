import { Outlet } from 'react-router'

import { isApiMocked } from '@/app/mocking'
import { AppVersions } from '@/features/versions'

import { ApiDocsLink } from './ApiDocsLink'
import { AppHeader } from './AppHeader'
import { MockDataBanner } from './MockDataBanner'

export function AppLayout() {
  return (
    <div className="flex min-h-dvh flex-col">
      {isApiMocked() && <MockDataBanner />}
      <AppHeader />
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8">
        <Outlet />
      </main>
      <footer className="border-t border-hairline bg-surface">
        <div className="mx-auto flex w-full max-w-5xl flex-wrap items-baseline justify-between gap-x-4 gap-y-1 px-4 py-3 text-xs text-ink-muted">
          <AppVersions />
          <ApiDocsLink />
        </div>
      </footer>
    </div>
  )
}
