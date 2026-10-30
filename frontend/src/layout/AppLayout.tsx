import { Outlet } from 'react-router'

import { isApiMocked } from '@/app/mocking'
import { AppVersions } from '@/features/versions'

import { MockDataBanner } from './MockDataBanner'

export function AppLayout() {
  return (
    <div className="flex min-h-dvh flex-col">
      {isApiMocked() && <MockDataBanner />}
      <header className="bg-primary-700 text-white">
        <div className="mx-auto w-full max-w-5xl px-4 py-4">
          <h1 className="text-xl font-semibold">PANTHER Scoring</h1>
        </div>
      </header>
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8">
        <Outlet />
      </main>
      <footer className="border-t border-hairline bg-surface">
        <div className="mx-auto w-full max-w-5xl px-4 py-3 text-xs text-ink-muted">
          <AppVersions />
        </div>
      </footer>
    </div>
  )
}
