import { isApiMocked } from '@/app/mocking'
import { ErrorPage } from '@/components/ErrorPage'

import { AppHeader } from './AppHeader'
import { MockDataBanner } from './MockDataBanner'

// The root route's error element: the layout itself failed, so draw the frame again without
// the parts that may have caused it. No footer: the versions in it are fetched data.
export function RootError() {
  return (
    <div className="flex min-h-dvh flex-col">
      {isApiMocked() && <MockDataBanner />}
      <AppHeader />
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8">
        <ErrorPage />
      </main>
    </div>
  )
}
